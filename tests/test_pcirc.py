from fractions import Fraction

import aiger_bv as BV
import aiger_discrete
from bidict import bidict

from aiger_coins.pcirc import coin, die, pcirc, PCirc


def test_coin():
    my_coin = coin(0.3, name='x')
    assert my_coin.inputs == set()
    assert my_coin.outputs == {'x'}
    assert my_coin.coin_biases == (0.7,)
    assert my_coin.circ({my_coin.coins_id: 0})[0]['x'] == 1
    assert my_coin.circ({my_coin.coins_id: 1})[0]['x'] == 0


def test_die():
    my_die = die((
        Fraction(1, 6),
        Fraction(1, 3),
        Fraction(1, 2),
    ), name='x')
    assert my_die.inputs == set()
    assert my_die.outputs == {'x'}
    assert my_die.num_coins == 2
    assert my_die.coin_biases == (Fraction(1, 3), Fraction(1, 2))

    assert my_die.circ({my_die.coins_id: 0b00})[0]['x'] == 1
    assert my_die.circ({my_die.coins_id: 0b01})[0]['x'] == 0
    assert my_die.circ({my_die.coins_id: 0b10})[0]['x'] == 2
    assert my_die.circ({my_die.coins_id: 0b11})[0]['x'] == 2

    assert (1 - my_die.coin_biases[0]) * (1 -my_die.coin_biases[1]) == \
        Fraction(1, 3)
    assert my_die.coin_biases[0] * (1 -my_die.coin_biases[1]) == Fraction(1, 6)
    assert my_die.coin_biases[1] == Fraction(1, 2)


def test_pcirc():
    # Create encoder/decoder for dice.
    lookup = bidict({0: '⚀', 1: '⚁', 2: '⚂', 3: '⚃'})
    encoder = aiger_discrete.Encoding(decode=lookup.get, encode=lookup.inv.get)

    # Represent dice with a 2 bit vector.
    expr1 = BV.uatom(2, '🎲') 

    # Add encoded dice to x. Because why not.
    expr2 = BV.uatom(2, 'x') + expr1
    func = aiger_discrete.from_aigbv(
        expr2.aigbv, input_encodings={'🎲': encoder}
    )

    # Create distribution over bits.
    circ = pcirc(func, dist_map={
        '🎲': {
            '⚀': Fraction(1, 6),
            '⚁': Fraction(2, 6),
            '⚂': Fraction(3, 6),
        },
    })

    assert circ.inputs == {'x'}
    assert circ.outputs == {expr2.output}
    assert circ.coin_biases == (Fraction(1, 3), Fraction(1, 2))
