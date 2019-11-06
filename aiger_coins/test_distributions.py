from fractions import Fraction
import hypothesis.strategies as st
from hypothesis import given, settings

import aiger_bv
from aiger_bdd import count

from aiger_coins import binomial, coin, mutex_coins


@settings(max_examples=4, deadline=None)
@given(st.integers(0, 7), st.integers(1, 7))
def test_biased_coin(k, m):
    f = Fraction(*sorted([k, m]))
    k, m = f.numerator, f.denominator
    for prob in [f, (k, m)]:
        k_expr, m_expr = coin((k, m), 'x')
        f2 = Fraction(count(k_expr), count(m_expr))
        assert f == f2


@settings(max_examples=4, deadline=None)
@given(st.lists(st.integers(1, 5), min_size=2, max_size=10))
def test_mutex_coins(weights):
    denom = sum(weights)
    mux, is_valid = mutex_coins((w, denom) for w in weights)
    mux = aiger_bv.SignedBVExpr(mux.aigbv)

    one_hot = (mux != 0) & ((mux & (mux - 1)) == 0)
    assert count(one_hot) == count(is_valid)


def test_binomial():
    x = binomial(6, use_1hot=False)
    y = binomial(6, use_1hot=True)
    for i, v in enumerate([1, 6, 15, 20, 15, 6, 1]):
        assert v == count(x == i)
        assert v == count(y == (1 << i))
