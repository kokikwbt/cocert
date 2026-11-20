"""Check comparison semantics of the optional comparison adapters."""

from fractions import Fraction
import importlib.util

import pytest

from cocert.baselines.recent import adaptive_lp, conditional_lp, eris_lp, minimum_tv_bounds, mmd_tv

QUERY = {'A': [[1, 0], [1, 2]], 'B': [1, 1], 'C': [[0, 1], [2, 1]]}


@pytest.mark.skipif(importlib.util.find_spec('networkx') is None, reason='Optional core-distance dependency')
def test_independent_cores_do_not_certify_shared_conflict():
    assert all(Fraction(v) == 0 for v in minimum_tv_bounds(QUERY)['bounds'])
    assert conditional_lp(QUERY)['status'] == 'positive'
    assert conditional_lp(QUERY, total=1)['status'] == 'positive'


@pytest.mark.skipif(importlib.util.find_spec('osqp') is None, reason='Optional OSQP dependency')
def test_linear_adapter_requires_a_known_total():
    assert eris_lp(QUERY)['status'] == 'not_applicable'
    assert eris_lp(QUERY, total=1)['status'] == 'positive'


@pytest.mark.parametrize('decide', (conditional_lp, adaptive_lp))
def test_conditional_search_checks_both_answers(decide):
    assert decide(QUERY)['status'] == 'positive'
    assert decide(QUERY, '3/2')['status'] == 'negative'


def test_mmd_tv_is_a_one_sided_certificate():
    query = {'A': [[20, 0]], 'B': [0, 0], 'C': [[0, 20]]}
    assert mmd_tv(query, total=0)['status'] == 'positive'
    assert mmd_tv(query, total=0, bandwidth='median')['status'] == 'positive'
    assert mmd_tv(QUERY)['status'] == 'not_applicable'
