from fractions import Fraction
import hypothesis.strategies as st
from hypothesis import given, settings

import aiger
from aiger_bdd import count

from aiger_coins import coin, mutex_coins


@settings(max_examples=4)
@given(st.integers(0, 7), st.integers(1, 7))
def test_biased_coin(k, m):
    f = Fraction(*sorted([k, m]))
    k, m = f.numerator, f.denominator
    for prob in [f, (k, m)]:
        k_expr, m_expr = coin((k, m), 'x')
        f2 = Fraction(count(k_expr), count(m_expr))
        assert f == f2


@settings(max_examples=4)
@given(st.lists(st.integers(1, 5), min_size=2, max_size=10))
def test_mutex_coins(weights):
    denom = sum(weights)
    mux, is_valid = mutex_coins(
        name2prob={f'x{i}': (w, denom) for i, w in enumerate(weights)}
    )
    bot = count(is_valid)

    # Sanity checks.
    neq0 = aiger.or_gate(mux.outputs)
    is_odd = aiger.parity_gate(mux.outputs)
    for gate in [neq0, is_odd]:
        prob  = Fraction(count(mux >> gate) , bot)
        assert prob == 1
