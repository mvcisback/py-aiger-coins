from fractions import Fraction
import hypothesis.strategies as st
from hypothesis import given, settings

from aiger_bdd import count

from aiger_coins import biased_coin


@settings(max_examples=4, deadline=None)
@given(st.integers(0, 7), st.integers(1, 7))
def test_biased_coin(k, m):
    f = Fraction(*sorted([k, m]))
    k, m = f.numerator, f.denominator
    for prob in [f, (k, m)]:
        k_expr, m_expr = biased_coin((k, m))
        k2, m2 = count(k_expr, fraction=False), count(m_expr, fraction=False)
        assert (k == k2) and (m == m2)
