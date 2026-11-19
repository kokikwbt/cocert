"""Reconstruct and verify a known-total audit using retained counts only."""
import csv
from fractions import Fraction as F
import json
from pathlib import Path
import sys


def check(folder):
    request = json.loads((folder / 'request.json').read_text())
    metadata = json.loads((folder / 'count-metadata.json').read_text())
    proof = json.loads((folder / 'certificate.json').read_text())
    statement = json.loads((folder / 'audit-statement.json').read_text())
    assert proof['kind'] == 'support' and proof['found'] is True
    before, cut, after = [request[k] for k in ['before_us', 'cut_us', 'after_us']]
    assert before < cut < after
    assert all(metadata[k] == request[k] for k in ['before_us', 'cut_us', 'after_us'])
    assert request['bins'] == len(request['bin_edges']) + 1
    assert request['bin_edges'] == sorted(set(request['bin_edges']))
    assert all(left < before and after < right for left, right in request['endpoints'])
    points = {}
    with (folder / 'checkpoints.csv').open() as stream:
        for row in csv.DictReader(stream):
            at = int(row['time_us'])
            assert at not in points
            points[at] = [F(row[f'b{j}']) for j in range(request['bins'])]
    assert all(v >= 0 for point in points.values() for v in point)
    ordered = sorted(points)
    assert all(all(u <= v for u, v in zip(points[a], points[b])) for a, b in zip(ordered, ordered[1:]))
    sub = lambda a, b: [v - u for u, v in zip(points[a], points[b])]
    B = sub(before, after)
    A = [sub(left, before) for left, right in request['endpoints']]
    C = [sub(after, right) for left, right in request['endpoints']]
    assert all([list(map(F, row)) for row in proof[k]] == values for k, values in [('A', A), ('C', C)])
    assert list(map(F, proof['B'])) == B
    s = F(metadata['split_total']); ep = F(request['epsilon'])
    assert F(proof['total']) == s and F(proof['epsilon']) == ep
    assert 0 <= s <= sum(B) == F(metadata['boundary_total'])
    weights = list(map(F, proof['weights'])); alpha = [list(map(F, row)) for row in proof['alpha']]
    assert len(weights) == len(alpha) == len(A) and min(weights) >= 0 and sum(weights) == 1
    assert all(len(row) == len(B) and all(abs(v) <= 1 for v in row) for row in alpha)
    constant = F(0); d = [F(0)] * len(B)
    for a, c, w, al in zip(A, C, weights, alpha):
        L, R = sum(a) + s, sum(c) + sum(B) - s
        assert L > 0 and R > 0
        constant += w * sum(z * (u / L - (v + cap) / R) for z, u, v, cap in zip(al, a, c, B)) / 2
        for j in range(len(B)): d[j] += w * al[j] * (1 / L + 1 / R) / 2
    remaining, lower = s, constant
    for j in sorted(range(len(B)), key=lambda j: d[j]):
        mass = min(remaining, B[j]); lower += mass * d[j]; remaining -= mass
    display_lower = F(statement['display_TV_lower_bound'])
    assert remaining == 0 and lower == F(proof['lower']) > display_lower > ep
    return dict(status='passed', scale_weights=[str(v) for v in weights], verified_TV_lower_bound=str(lower),
                TV_lower_bound_float=float(lower), threshold=str(ep), uses_transformed_Gamma=False,
                checkpoint_reconstruction=True, raw_observations_read=False, standard_library_only=True,
                input_checks=dict(nonnegative_monotone_checkpoints=True, bin_definition=True, request_times=True,
                                  split_count_binding=True, positive_window_totals=True),
                certificate_checks=dict(unit_sum_nonnegative_weights=True, bounded_support_vectors=True,
                                        exact_TV_lower_bound=True, display_bound_exceeded=True, threshold_exceeded=True),
                display_TV_lower_bound=str(display_lower),
                verified_inequality=f"R(s) >= {lower} > {display_lower} > {ep}")


if __name__ == '__main__':
    print(json.dumps(check(Path(sys.argv[1]))))
