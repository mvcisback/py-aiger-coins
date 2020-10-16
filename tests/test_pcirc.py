from fractions import Fraction

import aiger_bv as BV
import aiger_discrete
from bidict import bidict

import aiger_coins as C


def test_pcirc1():
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
    circ = C.pcirc(func) \
            .randomize({'🎲': {'⚀': 1/6, '⚁': 2/6, '⚂': 3/6}})

    assert circ.inputs == {'x'}
    assert circ.outputs == {expr2.output}
    assert circ.coin_biases == (1/3, 1/2)


def test_pcirc2():
    expr1 = BV.uatom(2, 'x') + BV.uatom(2, 'y')

    # Create distribution over bits.
    circ = C.pcirc(expr1.aigbv, dist_map={
        'x': {
            0: Fraction(1, 6),
            1: Fraction(2, 6),
            2: Fraction(3, 6),
        },
    })

    assert circ.inputs == {'y'}
    assert circ.outputs == {expr1.output}
    assert circ.coin_biases == (Fraction(1, 3), Fraction(1, 2))


def test_seqcompose():
    adder = (BV.uatom(2, 'x') + BV.uatom(2, 'y')).with_output('z')
    incr = (BV.uatom(2, 'z') + 1).with_output('w')

    # Create distribution over bits.
    pcirc = C.pcirc(adder) \
             .randomize({'x': {0: 1/6, 1: 2/6, 2: 3/6}})
    pcirc >>= incr

    assert pcirc.inputs == {'y'}
    assert pcirc.outputs == {'w'}
    assert pcirc.num_coins == 2

    # Check support.
    assert pcirc.circ({pcirc.coins_id: 0b00, 'y': 0})[0]['w'] == 3
    assert pcirc.circ({pcirc.coins_id: 0b01, 'y': 0})[0]['w'] == 3
    assert pcirc.circ({pcirc.coins_id: 0b10, 'y': 0})[0]['w'] == 2
    assert pcirc.circ({pcirc.coins_id: 0b11, 'y': 0})[0]['w'] == 1


def test_parcompose():
    inc_x = C.pcirc(BV.uatom(2, 'x') + 1) \
             .randomize({'x': {0: 1/3, 2: 2/3}})

    inc_y = C.pcirc(BV.uatom(3, 'y') + 1) \
             .randomize({'y': {0: 1/3, 5: 1/3, 3: 1/3}})

    inc_xy = inc_x | inc_y

    assert inc_xy.inputs == set()
    assert len(inc_xy.outputs) == 2
    assert inc_xy.num_coins == inc_x.num_coins + inc_y.num_coins
    assert inc_xy.num_coins == 3
