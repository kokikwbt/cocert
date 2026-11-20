"""Shared tangent certificates and exact verification on incompatible windows."""
from fractions import Fraction
from unittest.mock import patch

import pytest

from cocert.api import Engine
from cocert.verification import verify
from cocert._screen import ranked_pairs

SHARING = dict(A=[[1, 0], [1, 2]], B=[1, 1], C=[[0, 1], [2, 1]])


def test_pair_certifies_shared_change_without_calling_a_solver():
    with patch('cocert.backends.full.threshold_residual', side_effect=AssertionError('Unexpected solve')):
        answer = Engine().query(SHARING, '1/10')
    assert answer['status'] == 'positive'
    assert answer['stage'] == 'tangent_pair'
    assert verify(answer['proof'], SHARING, epsilon='1/10')
    assert Fraction(answer['proof']['bound']) == Fraction(7, 120)


def test_pair_keeps_common_low_change_completion():
    answer = Engine(pair_scales=5).query(SHARING, '1/2')
    assert answer['status'] == 'negative'
    assert verify(answer['proof'], SHARING, epsilon='1/2') is False


def test_pair_order_uses_stable_scale_ranks():
    assert ranked_pairs([1, 3, 3, 2], 3) == [(1, 2), (1, 3), (2, 3)]
    assert ranked_pairs([1, 1, 1], 2) == [(0, 1)]


@pytest.mark.parametrize('count', [-1, 1, 2.5, True])
def test_invalid_pair_budget(count):
    with pytest.raises(ValueError):
        Engine(pair_scales=count)
