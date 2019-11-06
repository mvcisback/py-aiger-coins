from fractions import Fraction
import hypothesis.strategies as st
from hypothesis import given, settings

import aiger_bv

from aiger_coins import binomial, coin, mutex_coins


@settings(max_examples=4, deadline=None)
@given(st.integers(0, 7), st.integers(1, 7))
def test_biased_coin(k, m):
    f = Fraction(*sorted([k, m]))
    k, m = f.numerator, f.denominator
    for prob in [f, (k, m)]:
        assert coin((k, m), 'x').prob() == f


@settings(max_examples=4, deadline=None)
@given(st.lists(st.integers(1, 5), min_size=2, max_size=10))
def test_mutex_coins(weights):
    denom = sum(weights)
    freqs = [Fraction(w, denom) for w in weights]

    mux = mutex_coins(freqs)

    def is_one_hot(x):
        x = aiger_bv.SignedBVExpr(x.aigbv)
        test = (x != 0) & ((x & (x - 1)) == 0)
        return aiger_bv.UnsignedBVExpr(test.aigbv)

    one_hot = mux.apply(is_one_hot)[0]
    assert one_hot.prob() == 1

    for f1, f2 in zip(freqs, mux.freqs()):
        assert f1 == f2


def test_binomial():
    weights = [1, 6, 15, 20, 15, 6, 1]
    expected_freqs = [Fraction(v, 64) for v in weights]

    assert binomial(6).freqs() == tuple(expected_freqs)
