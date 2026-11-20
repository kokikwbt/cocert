"""Recompute the reported comparisons from saved VLDB decisions and timings."""

import argparse
from collections import Counter, defaultdict
import csv
from fractions import Fraction
import gzip
from itertools import combinations
import json
import math
from pathlib import Path
from statistics import mean, median
import sys


HERE = Path(__file__).resolve().parent
TABLES = HERE.parent / "tables"
RESOLVED = {"positive", "negative"}


def json_file(name):
    return json.loads((TABLES / name).read_text())


def group(rows, *keys):
    result = defaultdict(list)
    for row in rows:
        result[tuple(row[key] for key in keys)].append(row)
    return result


def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-12), (a, b)


def p95(values):
    ordered = sorted(values)
    i, part = divmod(95 * (len(ordered) - 1), 100)
    return ordered[i] + part / 100 * (ordered[min(i + 1, len(ordered) - 1)] - ordered[i])


def coverage(saved, reference, policy, bootstrap):
    expected = {(r["scenario"], r["epsilon"], r["condition"]): r for r in reference}
    output = []
    rng = None
    if bootstrap:
        import numpy as np
        rng = np.random.default_rng(policy["bootstrap_seed"])
    for cohort in saved:
        key = tuple(cohort[k] for k in ("scenario", "epsilon", "condition"))
        counts = Counter()
        units = defaultdict(lambda: [0, 0])
        for cluster, fine, separate, cocert, smt, n in cohort["records"]:
            yes = cocert == "positive"
            assert cocert in RESOLVED and (smt == cocert or smt == "undecided")
            assert not separate or yes
            assert fine is not False or not yes
            counts.update(queries=n, separate=n * separate, cocert=n * yes,
                          smt_positive=n * (smt == "positive"), smt_undecided=n * (smt == "undecided"),
                          smt_unresolved_positive=n * (smt == "undecided" and yes))
            if fine is not None:
                counts.update(fine_positive=n * fine, fine_negative=n * (not fine),
                              remaining_compatible=n * (fine and not yes))
                units[cluster][0] += n * fine
                units[cluster][1] += n * (yes - separate)
        expected_row = expected.pop(key)
        assert all(expected_row[k] == v for k, v in counts.items()), key
        result = dict(scenario=key[0], epsilon=key[1], condition=key[2], **counts)
        if counts["fine_positive"]:
            result["recall_gain_pp"] = 100 * (counts["cocert"] - counts["separate"]) / counts["fine_positive"]
        if rng is not None and "gain_pp_interval" in expected_row:
            values = np.asarray([units[k] for k in sorted(units)], dtype=np.int64)
            n_units = len(values)
            assert n_units == expected_row["units"]
            gains = []
            for _ in range(policy["bootstrap_draws"]):
                fine, added = values[rng.integers(n_units, size=n_units)].sum(axis=0)
                gains.append(100 * added / fine)
            interval = np.quantile(gains, [0.025, 0.975]).tolist()
            for a, b in zip(interval, expected_row["gain_pp_interval"]):
                close(a, b)
            result["gain_pp_interval"] = interval
        output.append(result)
    assert not expected
    return output


def split_total_control(saved, certification):
    """Project the paired outcomes onto the main coverage data and classify gaps."""
    assert saved["schema"] == 1
    epsilon = saved["epsilon"]
    assert epsilon == "1/10"
    expected = {(row["scenario"], row["condition"]): row for row in certification
                if row["epsilon"] == epsilon}
    categories = {
        (False, True, True): "total_only",
        (True, False, True): "sharing_only",
        (True, True, True): "either",
        (False, False, True): "both_required",
        (False, False, False): "compatible",
    }
    output = []
    seen = set()
    for cohort in saved["scenarios"]:
        scenario = cohort["scenario"]
        assert scenario not in seen
        seen.add(scenario)
        unknown, known, gaps = Counter(), Counter(), Counter()
        for row in cohort["patterns"]:
            size = row["queries"]
            fine = row["fine_positive"]
            su, cu, sk, ck = [row[key] for key in (
                "separate_unknown", "shared_unknown", "separate_known", "shared_known")]
            assert size > 0 and all(isinstance(v, bool) for v in (fine, su, cu, sk, ck))
            if su:
                assert cu and sk
            if cu or sk:
                assert ck
            if ck:
                assert fine
            for margins, separate, shared in ((unknown, su, cu), (known, sk, ck)):
                margins.update(queries=size, fine_positive=size * fine, fine_negative=size * (not fine),
                               separate=size * separate, cocert=size * shared,
                               remaining_compatible=size * (fine and not shared))
            if fine and not su:
                gaps[categories[cu, sk, ck]] += size
        for condition, margins in (("unknown", unknown), ("derived", known)):
            reference = expected[scenario, condition]
            assert all(reference[key] == value for key, value in margins.items()), (scenario, condition)
        uncertified = unknown["fine_positive"] - unknown["separate"]
        assert sum(gaps.values()) == uncertified
        assert 0 <= cohort["both_required_distinct_inputs"] <= gaps["both_required"]
        output.append({
            "scenario": scenario, "uncertified": uncertified,
            **{name: gaps[name] for name in categories.values()},
            "both_required_distinct_inputs": cohort["both_required_distinct_inputs"],
            "both_required_units": cohort["both_required_units"],
        })
    assert seen == {name for name, condition in expected if condition == "derived"}
    assert 0 < saved["replayed_distinct_inputs"] <= sum(row["both_required"] for row in output)
    assert 0 < saved["compatible_distinct_inputs"] <= sum(row["compatible"] for row in output)
    return output


def fleet_coverage(saved):
    cohort, = (
        row for row in saved
        if (row["scenario"], row["epsilon"], row["condition"]) == ("Scania", "1/10", "unknown")
    )
    eligible, fine_positive, separate, cocert = set(), set(), set(), set()
    for truck, fine, separate_answer, shared_answer, _, count in cohort["records"]:
        assert count > 0
        eligible.add(truck)
        if fine:
            fine_positive.add(truck)
        if separate_answer:
            separate.add(truck)
        if shared_answer == "positive":
            cocert.add(truck)
    assert separate <= cocert <= fine_positive <= eligible
    assert (len(eligible), len(fine_positive), len(separate), len(cocert)) == (1244, 968, 281, 359)
    return dict(eligible_trucks=len(eligible), fine_positive_trucks=len(fine_positive),
                separate_trucks=len(separate), cocert_trucks=len(cocert), added_trucks=len(cocert - separate))


def matched_timing(rows, reference):
    output = []
    paired_ratios = defaultdict(list)
    for scenario in reference["scenarios"]:
        series = [r for r in rows if r["scenario"] == scenario["scenario"]]
        methods = tuple(scenario["timings"])
        complete = Counter()
        common = defaultdict(list)
        queries = group(series, "key")
        assert len(queries) == reference["timing_requests_per_scenario"]
        for trials in queries.values():
            finished = {}
            for (method,), values in group(trials, "method").items():
                repetitions = reference["repetitions"]
                assert {v["repeat"] for v in values} == set(range(repetitions)) and len(values) == repetitions
                assert all(v["status"] in (v["expected"], "undecided") for v in values)
                if all(v["status"] in RESOLVED for v in values):
                    finished[method] = 1000 * median(v["seconds"] for v in values)
            complete.update(finished.keys())
            if set(finished) == set(methods):
                for method, elapsed in finished.items():
                    common[method].append(elapsed)
                baseline_times = {
                    "Adaptive LP": min(elapsed for method, elapsed in finished.items()
                                       if method.startswith("Adaptive LP")),
                    "Symb-SMT": finished["Symb-SMT"],
                }
                for baseline, elapsed in baseline_times.items():
                    paired_ratios[baseline].append(elapsed / finished["CoCert"])
        for method, ref in scenario["timings"].items():
            values = common[method]
            assert len(values) == scenario["jointly_resolved"]
            assert complete[method] == len(queries) - ref["undecided"]
            close(mean(values), ref["mean_ms"])
            close(median(values), ref["median_ms"])
            close(p95(values), ref["p95_ms"])
            output.append(dict(scenario=scenario["scenario"], method=method, n=len(queries),
                               complete=complete[method], joint=len(values), median_ms=median(values), p95_ms=p95(values)))
    paired = {
        baseline: dict(inputs=len(ratios), faster=sum(ratio > 1 for ratio in ratios),
                       median_speedup=median(ratios))
        for baseline, ratios in paired_ratios.items()
    }
    return output, paired


def timing_contrasts(timing):
    output = []
    for (name,), rows in sorted(group(timing, "scenario").items()):
        indexed = {r["method"]: r for r in rows}
        current = indexed["CoCert"]
        lp = [r for method, r in indexed.items() if method.startswith("Adaptive LP")]
        output.append(dict(
            scenario=name,
            smt_median=indexed["Symb-SMT"]["median_ms"] / current["median_ms"],
            lp_median=min(r["median_ms"] for r in lp) / current["median_ms"],
            lp_p95=min(r["p95_ms"] for r in lp) / current["p95_ms"],
        ))
    return output


def replay(rows, expected, binding):
    groups = group(rows, "stratum")
    for r in expected["strata"]:
        cases = groups[r["stratum"],]
        assert len(cases) == r["n"]
        for field in ("generation_ms", "replay_ms", "certificate_bytes"):
            head, unit = field.rsplit("_", 1)
            close(median(c[field] for c in cases), r[f"{head}_median_{unit}"])
    assert len(rows) == binding["valid"]["queries"] == sum(r["n"] for r in expected["strata"])
    assert all(n == len(rows) for n in binding["rejected"].values())
    assert Counter(r["status"] for r in rows) == Counter(positive=binding["valid"]["positive"],
                                                       negative=binding["valid"]["negative"])
    return dict(queries=len(rows), rejected=sum(binding["rejected"].values()), groups=expected["strata"])


def ablation(rows, weights):
    weights = {(r["dataset"], r["group"]): Fraction(int(r["population"]), int(r["sample"]))
               for r in weights}
    with (TABLES / "screening-comparison.csv").open(newline="") as stream:
        expected = {(r["group"], r["method"]): r for r in csv.DictReader(stream)}
    output = []
    for key, cases in sorted(group(rows, "group", "method").items()):
        values = []
        solved = 0
        for (dataset, _), trials in group(cases, "dataset", "query_id").items():
            weight = weights[dataset, key[0]]
            assert len(trials) == 3 and {r["repeat"] for r in trials} == {0, 1, 2}
            assert all(r["status"] == ("negative" if key[0] == "common_negative" else "positive") for r in trials)
            values.append((median(r["milliseconds"] for r in trials), weight))
            solved += weight * Fraction(sum(r["route"] == "solver" for r in trials), 3)
        total = sum(w for _, w in values)
        mean_ms = math.fsum(value * w for value, w in values) / total
        cumulative = 0
        for tail, weight in sorted(values):
            cumulative += weight
            if cumulative >= Fraction(95, 100) * total:
                break
        ref = expected[key]
        assert len(values) == int(ref["sample"]) and total == int(ref["population"])
        close(mean_ms, float(ref["mean_ms"]))
        close(tail, float(ref["p95_ms"]))
        output.append(dict(group=key[0], method=key[1], mean_ms=mean_ms, p95_ms=tail,
                           solver_fraction=float(solved / total), n=len(values)))
    return output


def near_threshold(rows):
    """Check ALPI runtimes on each side of the numerical optimum estimate."""
    output = []
    cohorts = group(rows, "level", "status")
    assert set(cohorts) == {(level, status) for level in (10**3, 10**6, 10**9) for status in RESOLVED}
    for (denominator, status), trials in sorted(cohorts.items()):
        cases = group(trials, "query_id")
        assert len(cases) == 12
        assert all(len(case) == 3 and {r["repeat"] for r in case} == {0, 1, 2} for case in cases.values())
        runtime = p95([median(r["seconds"] for r in case) for case in cases.values()])
        output.append(dict(offset_denominator=denominator, status=status, inputs=len(cases),
                           p95_seconds=runtime, mean_check_seconds=mean(r["check"] for r in trials)))
    closest_positive, = [r for r in output if r["offset_denominator"] == 10**9 and r["status"] == "positive"]
    assert round(closest_positive["p95_seconds"], 2) == 1.55
    assert round(closest_positive["mean_check_seconds"], 2) == 1.27
    return output


def precision_control(rows):
    """Compare exact checking on each set of accepted rounded supports."""
    output = []
    for (level,), inputs in sorted(group(rows, "level").items()):
        cases = group(inputs, "query")
        assert len(cases) == 12
        full = {}
        for (query,), trials in cases.items():
            assert {r["precision"] for r in trials} == {"full", "16", "24", "32", "44"}
            assert len(trials) == 5 and all(len(r["verification_seconds"]) == 3 for r in trials)
            original, = [r for r in trials if r["precision"] == "full"]
            assert original["accepted"]
            full[query] = median(original["verification_seconds"])
        for (precision,), trials in group(inputs, "precision").items():
            accepted = [r for r in trials if r["accepted"]]
            output.append(dict(level=level, precision=precision, tested=len(trials),
                               accepted=len(accepted),
                               median_accepted_ms=1000 * median(median(r["verification_seconds"])
                                                                for r in accepted) if accepted else None,
                               paired_full_ms=1000 * median(full[r["query"]]
                                                           for r in accepted) if accepted else None,
                               median_payload_bytes=median(r["payload_bytes"] for r in trials)))
    assert len(output) == 15
    closest = {r["precision"]: r["accepted"] for r in output if r["level"] == 10**9}
    assert closest == {"full": 12, "16": 0, "24": 2, "32": 12, "44": 12}
    return output


def dimensions(expanded, distinct, archive):
    equivalent = []
    for (stage, axis, factor), rows in sorted(group(expanded, "stage", "axis", "factor").items()):
        traces = group(rows, "origin")
        assert all(len(cases) == 3 for cases in traces.values())
        assert all(r["status"] == r["expected"] and r["stage"] == r["returned_stage"] for r in rows)
        elapsed = 1000 * math.exp(mean(math.log(median(r["seconds"] for r in cases)) for cases in traces.values()))
        key = stage, axis, factor
        ref, = [r for r in archive["dimension_scaling"] if (r["stage"], r["axis"], r["factor"]) == key]
        assert ref["n"] == len(traces)
        close(elapsed, ref["milliseconds"])
        equivalent.append(dict(stage=stage, axis=axis, factor=factor, milliseconds=elapsed, n=len(traces)))
    slopes = []
    for (stage, axis), rows in group(equivalent, "stage", "axis").items():
        x = [math.log(r["factor"]) for r in rows]
        y = [math.log(r["milliseconds"]) for r in rows]
        beta = sum((a - mean(x)) * (b - mean(y)) for a, b in zip(x, y)) / sum((a - mean(x)) ** 2 for a in x)
        slopes.append(dict(stage=stage, axis=axis, exponent=beta, time_ratio=math.exp(max(y) - min(y))))

    real = []
    expected = {(r["scenario"], r["axis"], r["level"]): r
                for r in archive["input_scaling"] if r["method"] == "CoCert"}
    for key, rows in sorted(group(distinct, "scenario", "axis", "level").items()):
        cases = group(rows, "channel", "query")
        assert all(len(runs) == 3 and {r["repeat"] for r in runs} == {0, 1, 2} for runs in cases.values())
        complete = sum(all(r["status"] in RESOLVED for r in runs) for runs in cases.values())
        solved = sum(any(r["solved"] for r in runs) for runs in cases.values())
        tail = 1000 * p95([median(r["seconds"] for r in runs) for runs in cases.values()])
        ref = expected.pop(key)
        assert (ref["n"], ref["complete"], ref["solver_requests"]) == (len(cases), complete, solved)
        close(tail, ref["p95_ms"])
        real.append(dict(scenario=key[0], axis=key[1], level=key[2], n=len(cases), complete=complete,
                         solver=solved, p95_ms=tail))
    assert not expected
    return dict(equivalent=equivalent, fits=slopes, distinct=real)


def secondary(data, archive):
    windows = [r for r in data["windows"] if r["epsilon"] == "1/10"]
    assert all(int(r["queries"]) == 66952 and int(r["undecided"]) == 0 for r in windows)
    for r in windows:
        assert int(r["cocert"]) - int(r["separate"]) == int(r["added"])
    assert {r["design"]: int(r["added"]) for r in windows} == {
        "symmetric": 988, "symmetric_plus_first": 1378, "full": 1682
    }
    native = []
    for period in data["native"]:
        records = period["counts"]
        added = [row for row in records if not row[2] and row[3] == "positive"]
        counts = dict(queries=sum(r[-1] for r in records), separate=sum(r[-1] for r in records if r[2]),
                      cocert=sum(r[-1] for r in records if r[3] == "positive"),
                      additional=sum(r[-1] for r in added), largest=max(r[0] for r in added),
                      etcd_added=sum(r[-1] for r in added if r[1]), distinct_added=period["distinct_added"])
        ref = archive["native_sizes"][period["run"]]
        assert counts["additional"] == sum(r["added"] for r in ref.values())
        continuity = period["continuity"]
        stable = [r for r in continuity if r[0] == "stable_process"]
        assert sum(r[-1] for r in continuity) == counts["queries"]
        assert sum(r[-1] for r in continuity if r[1]) == counts["separate"]
        assert sum(r[-1] for r in continuity if r[2] == "positive") == counts["cocert"]
        assert sum(r[-1] for r in stable if r[1]) == counts["separate"]
        assert sum(r[-1] for r in stable if r[2] == "positive") == counts["cocert"]
        excluded = counts["queries"] - sum(r[-1] for r in stable)
        native.append(dict(run=period["run"], continuity_excluded=excluded, **counts))
    assert [r["additional"] for r in native] == [430, 198]
    assert [r["continuity_excluded"] for r in native] == [26, 0]
    assert native[0]["distinct_added"] == 232 and native[0]["largest"] == 52

    reloads = data["reload_controls"]
    assert len(reloads) == 4 and all(row["selected_before_latency"] for row in reloads)
    compatible = sum(not (row["separate"] or row["cocert"] or row["undecided"]) for row in reloads)
    assert compatible == len(reloads)

    cache = []
    for (mode,), trials in sorted(group(data["cache"], "mode").items()):
        assert len(trials) == 3 and all(r["requests"] == r["resolved"] == 128 for r in trials)
        result = dict(mode=mode, distinct=median(r["distinct"] for r in trials),
                      hits=median(r["hits"] for r in trials), seconds=median(r["wall"] for r in trials))
        ref, = [r for r in archive["cache"] if r["dataset"] == "wmcs" and r["method"] == "CoCert" and r["mode"] == mode]
        close(result["seconds"], float(ref["wall"]))
        cache.append(result)

    pairs = Counter()
    for row in data["pairs"]:
        tested = {tuple(sorted(pair)): status for pair, status in row["outcomes"]}
        possible = set(combinations(range(row["windows"]), 2))
        assert tested and set(tested) <= possible and len(tested) == len(row["outcomes"])
        assert all(status in RESOLVED for status in tested.values())
        sufficient = "positive" in tested.values()
        assert sufficient or set(tested) == possible
        pairs["sufficient" if sufficient else "all_compatible"] += 1
    assert pairs == {"sufficient": 232, "all_compatible": 3}

    known = {}
    for (method,), rows in group(data["known_alpi"], "method").items():
        queries = group(rows, "key")
        assert len(queries) == 16 and all(len(trials) == 3 for trials in queries.values())
        assert all(r["status"] in RESOLVED for r in rows)
        known[method] = 1000 * mean(median(r["seconds"] for r in trials) for trials in queries.values())
    assert round(known["CoCert"] / known["Conditional LP/nested (HiGHS)"], 1) == 2.4

    return dict(window_ablation=data["windows"], native=native, cache=cache, exact_pairs=pairs,
                reload_controls=dict(queries=len(reloads), compatible=compatible),
                known_alpi_mean_ms=known)


def check_native_example(checkout):
    """Replay the saved native certificate with the public standard-library checker."""
    sys.path[:0] = [str(checkout / "src"), str(checkout / "scripts")]
    from cocert.verification import verify
    from cocert._verify_known import tv
    from verify_archive_example import reconstruct

    record = json.loads((HERE / "wmcs-audit.json").read_text())
    query = reconstruct(record)
    assert verify(record["proof"], query, epsilon=record["epsilon"]) is True
    boundary = list(map(Fraction, query["B"]))
    allocation = list(map(Fraction, record["attaining_allocation"]))
    assert len(boundary) == len(allocation) and all(0 <= x <= b for x, b in zip(allocation, boundary))
    largest_tv = max(tv(list(map(Fraction, a)), boundary, list(map(Fraction, c)), allocation)
                     for a, c in zip(query["A"], query["C"]))
    assert largest_tv == Fraction(record["optimum"])
    low, high = record["left"], record["right"]
    assert record["checkpoints"][low]["time"] < record["comparison_time"] < record["checkpoints"][high]["time"]
    return dict(checkpoints=len(record["checkpoints"]), windows=len(query["A"]), epsilon=record["epsilon"],
                certified_change=True, maximum_tv_at_displayed_allocation=str(largest_tv))


def main():
    if not __debug__:
        raise RuntimeError("Run without -O so that the result checks are enabled.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap", action="store_true", help="Also regenerate paired intervals using NumPy.")
    parser.add_argument("--checker", type=Path, help="Public CoCert checkout for exact replay of the WMCS example.")
    parser.add_argument("--output", type=Path, help="Write the recomputed values to this JSON file.")
    args = parser.parse_args()
    with gzip.open(HERE / "records.json.gz", "rt") as stream:
        data = json.load(stream)
    assert data["schema"] == 1
    archive, timing = json_file("archive-results.json"), json_file("adaptive-comparison.json")
    certification = coverage(data["coverage"], archive["reference_coverage"], data["policy"], args.bootstrap)
    completed_coverage = Counter()
    for row in certification:
        completed_coverage[row["condition"]] += row["queries"]
    assert completed_coverage == {"unknown": 200856, "derived": 14942}
    assert data["policy"]["timing_budget_seconds"] is timing["wall_budget_seconds"] is None
    assert data["policy"]["repetitions"] == timing["repetitions"]
    match, paired = matched_timing(data["matched"], timing)
    lp_work = {}
    for (method,), trials in group(data["matched"], "method").items():
        if method.startswith("Adaptive LP"):
            calls = [row["lp_calls"] for row in trials]
            lp_work[method] = dict(median=median(calls), p95=p95(calls), maximum=max(calls))
    assert all(v == {"median": 3, "p95": 47, "maximum": 571} for v in lp_work.values())
    small, large = data["integer_small"], data["integer_large"]
    integer = dict(
        enumeration_decisions=sum(int(r["queries"]) for r in small),
        enumeration_undecided=sum(int(r["undecided"]) for r in small),
        enumeration_max_nodes=max(int(r["maximum_nodes"]) for r in small),
        large_inputs=sum(int(r["inputs"]) for r in large),
        large_positive_reuse=sum(int(r["positive"]) for r in large if r["mode"] == "real-positive"),
        large_rounded_negative=sum(int(r["negative"]) for r in large if r["mode"] == "integer"),
        large_undecided=sum(int(r["undecided"]) for r in large),
        large_B_max=max(int(r["max_B"]) for r in large),
        large_search_nodes=max(int(r["max_nodes"]) for r in large),
    )
    assert integer == dict(enumeration_decisions=215592, enumeration_undecided=0, enumeration_max_nodes=21,
                           large_inputs=65, large_positive_reuse=44, large_rounded_negative=21,
                           large_undecided=0, large_B_max=2350, large_search_nodes=0)
    output = dict(
        coverage=certification, latency=match, latency_speedup=timing_contrasts(match),
        completed_coverage=dict(completed_coverage),
        paired_latency=paired,
        adaptive_lp_calls=lp_work,
        integer_validation=integer,
        support_precision=precision_control(data["precision"]),
        split_total_control=split_total_control(json_file("split-total-control.json"), certification),
        scania_fleet=fleet_coverage(data["coverage"]),
        replay=replay(data["replay"], json_file("certificate-replay-data.json"), data["binding"]),
        screening=ablation(data["screening"], data["weights"]),
        scaling=dimensions(data["equivalent"], data["scaling"], archive),
        threshold_stress=near_threshold(data["threshold_stress"]),
        **secondary(data, archive),
    )
    if args.checker:
        output["wmcs_example"] = check_native_example(args.checker.resolve())
        print("WMCS certificate replayed.")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, indent=2) + "\n")
    print("Paper result records checked" + (" with bootstrapped intervals" if args.bootstrap else "") + ".")


if __name__ == "__main__":
    main()
