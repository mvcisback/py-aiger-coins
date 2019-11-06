from fractions import Fraction
import hypothesis.strategies as st
from hypothesis import given, settings

import aiger_bv

from aiger_coins import binomial, coin, dist


@settings(max_examples=4, deadline=None)
@given(st.integers(0, 7), st.integers(1, 7))
def test_biased_coin(k, m):
    f = Fraction(*sorted([k, m]))
    k, m = f.numerator, f.denominator
    for prob in [f, (k, m)]:
        assert coin((k, m), 'x').prob() == f


@settings(max_examples=4, deadline=None)
@given(st.lists(st.integers(1, 5), min_size=2, max_size=10))
def test_dist(weights):
    denom = sum(weights)
    freqs = [Fraction(w, denom) for w in weights]

    mux = dist(freqs)

    def is_one_hot(x):
        x = aiger_bv.SignedBVExpr(x.aigbv)
        test = (x != 0) & ((x & (x - 1)) == 0)
        return aiger_bv.UnsignedBVExpr(test.aigbv)

    one_hot = mux.apply(is_one_hot)[0]
    assert one_hot.prob() == 1

    for f1, f2 in zip(freqs, mux.freqs()):
        assert f1 == f2


def test_dice():
    weights = [1, 3, 2]
    freqs = [Fraction(w, 6) for w in weights]
    dice = dist(freqs)

    assert dice.freqs() == tuple(freqs)

    assert (dice[0] | dice[1]).prob() == Fraction(2, 3)
    assert (~dice[2]).prob() == Fraction(2, 3)

    dice2 = dice.apply(lambda expr: ~expr[2])
    assert dice2.freqs() == (Fraction(2, 3),)

    assert len(dice.inputs) == 1
    assert len(dice.aigbv.outputs) == 1
    assert dice.output == dice.expr.output

    assert len(dice.aig.inputs) == 3
    assert len(dice.aig.outputs) == dice.size

    dice3 = dice.condition(dice.coins != 0)
    new_freqs = [Fraction(w, 5) for w in [0, 3, 2]]
    assert dice3.freqs() == tuple(new_freqs)

    dice4 = dice[0].concat(dice[1]).concat(dice[2])
    assert dice4.freqs() == tuple(freqs)


def test_binomial():
    weights = [1, 6, 15, 20, 15, 6, 1]
    expected_freqs = [Fraction(v, 64) for v in weights]

    assert binomial(6).freqs() == tuple(expected_freqs)
