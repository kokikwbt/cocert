"""Public CoCert workflow: validate -> propose -> recover -> verify.

Optimizers only propose answers. A resolved result always carries a rational
certificate; failed recovery is reported as undecided, never as low change.
"""

from fractions import Fraction
import time
import numpy as np
from . import _certificate, _facets, _screen
from ._histogram import minimum_unrecorded_cut
from .backends import decision, fixed, full, simple
from .backends.fixed_certificates import rational_lp_candidates, single_optimum
from .configuration import METHODS, SCREENED_KNOWN_METHODS
from .queries import fraction_arrays, normalize, numeric_arrays, split_total, threshold
from .verification import tv, verify


def _direct_certificate(query, epsilon, total):
    """Handle a fully recorded boundary or the universal TV upper bound 1."""
    before, boundary, after = fraction_arrays(query)
    boundary_mass = sum(boundary)
    if total is None:
        allocation = [value / 2 for value in boundary]
    else:
        allocation = (
            [value * total / boundary_mass for value in boundary]
            if boundary_mass
            else boundary
        )
    changed = (
        max(tv(a, boundary, c, allocation) for a, c in zip(before, after)) > epsilon
    )
    proof = dict(
        query,
        epsilon=str(epsilon),
        kind="direct" if boundary_mass == 0 else "feasible",
        allocation=list(map(str, allocation)),
        found=changed,
        stage="direct",
    )
    if total is not None:
        proof["total"] = str(total)
    return proof


def _known_certificate(query, epsilon, total, *, screened):
    """Try exact single-scale/feasible certificates, then the fixed-total LP."""
    before, boundary, after = fraction_arrays(query)
    proof = dict(query, total=str(total), epsilon=str(epsilon))
    if screened:
        singles = [single_optimum(a, boundary, c, total) for a, c in zip(before, after)]
        strongest = max(range(len(before)), key=lambda k: singles[k][0])
        if singles[strongest][0] > epsilon:
            value, allocation = singles[strongest]
            proof.update(
                kind="single",
                found=True,
                scale_index=strongest,
                value=str(value),
                allocation=list(map(str, allocation)),
            )
            return proof, "known_single"
        candidates = [result[1] for result in singles]
        candidates.append([value * total / sum(boundary) for value in boundary])
        for allocation in candidates:
            if (
                max(tv(a, boundary, c, allocation) for a, c in zip(before, after))
                <= epsilon
            ):
                proof.update(
                    kind="feasible", found=False, allocation=list(map(str, allocation))
                )
                return proof, "known_feasible"
    solution = fixed.minimum_shared_tv(*numeric_arrays(query), float(total))
    # At a zero optimum the objective can carry the whole dual weight.
    if sum(solution["weights"]) == 0:
        solution = dict(
            solution,
            weights=[1.0] + [0.0] * (len(before) - 1),
            subgradients=[[0.0] * len(boundary) for _ in before],
        )
    candidate = rational_lp_candidates(before, boundary, after, total, solution)
    if candidate["upper"] <= epsilon:
        proof.update(kind="feasible", found=False, allocation=candidate["allocation"])
    elif candidate["lower"] > epsilon:
        proof.update(
            kind="support",
            found=True,
            lower=str(candidate["lower"]),
            weights=candidate["weights"],
            alpha=candidate["alpha"],
        )
    else:
        raise RuntimeError("No exact fixed-total witness recovered")
    return proof, "known_solver"


class Engine:
    """Answer a histogram query with an exact certificate, otherwise undecided.

    total=None leaves the split total unknown. A known total must be supplied
    separately from the count-only query dictionary.
    """

    def __init__(self, *, master_iterations=8, pair_scales=5):
        if not isinstance(master_iterations, int) or master_iterations < 1:
            raise ValueError("Positive master-iteration budget required")
        self.master_iterations = master_iterations
        if type(pair_scales) is not int or pair_scales < 0 or pair_scales == 1:
            raise ValueError(
                "Pair screening requires zero or at least two candidate scales"
            )
        self.pair_scales = pair_scales

    def propose(self, before, boundary, after, epsilon, method):
        """Select a numerical path; the returned candidate is not a certificate."""
        if method in ("cocert", "cocert-facets"):
            return _screen.threshold(
                before,
                boundary,
                after,
                epsilon=epsilon,
                solver="facets" if method == "cocert-facets" else "socp",
                max_iterations=self.master_iterations,
                pair_scales=self.pair_scales,
            )
        if method == "simple-filter":
            return simple.simple_two_sided(
                before,
                boundary,
                after,
                epsilon,
                minimum_unrecorded_cut,
                full.threshold_residual,
            )
        if method == "sharp-filter":
            values = [
                minimum_unrecorded_cut(a, boundary, c)["value"]
                for a, c in zip(before, after)
            ]
            strongest = int(np.argmax(values))
            if values[strongest] > epsilon + 1e-8:
                return dict(
                    found=True,
                    kind="single",
                    stage="sharp_single",
                    scale_index=strongest,
                )
        backend = decision if method == "decision" else full
        options = dict(epsilon=epsilon)
        if method == "facets":
            backend = _facets
            options["max_iterations"] = self.master_iterations
        candidate = backend.threshold_residual(before, boundary, after, **options)
        changed = candidate["lower"] > 1e-8
        return dict(
            candidate,
            found=changed,
            kind="support" if changed else "feasible",
            stage="solver",
        )

    def query(self, query, epsilon="1/10", *, method="cocert", total=None):
        """Validate one query, propose a decision, and recover an exact proof."""
        if method not in METHODS:
            raise ValueError(f"Unknown method: {method}")
        query = normalize(query)
        epsilon = threshold(epsilon)
        total = split_total(total, query["B"])
        boundary_mass = sum(map(Fraction, query["B"]))
        started = time.perf_counter()
        proposal_seconds = 0.0
        stage = "proposal"
        try:
            if boundary_mass == 0 or epsilon >= 1:
                proof = _direct_certificate(query, epsilon, total)
                verify(proof, query, total=total, epsilon=epsilon)
                stage = "direct"
            elif total is not None:
                proof, stage = _known_certificate(
                    query, epsilon, total, screened=method in SCREENED_KNOWN_METHODS
                )
                proof["stage"] = stage
                verify(proof, query, total=total, epsilon=epsilon)
            else:
                candidate = self.propose(*numeric_arrays(query), float(epsilon), method)
                proposal_seconds = time.perf_counter() - started
                stage = candidate["stage"]
                proof = _certificate.certificate(query, epsilon, candidate=candidate)
            status = "positive" if proof["found"] else "negative"
            error = None
        except (AssertionError, ArithmeticError, RuntimeError) as failure:
            status, proof = "undecided", None
            error = f"{type(failure).__name__}: {failure}"
        elapsed = time.perf_counter() - started
        answer = dict(
            query_id=query["query_id"],
            status=status,
            stage=stage,
            proof=proof,
            seconds=elapsed,
            proposal_seconds=proposal_seconds,
            proof_seconds=elapsed - proposal_seconds,
        )
        if error is not None:
            answer["error"] = error
        return answer


def query(query, epsilon="1/10", *, method="cocert", total=None):
    """Convenience wrapper for a single Engine query."""
    return Engine().query(query, epsilon, method=method, total=total)


def compare(query, epsilon="1/10", *, total=None):
    """Compare the six certification strategies in the main coverage table."""
    from .comparison import compare as compare_strategies

    return compare_strategies(query, epsilon, total=total)
