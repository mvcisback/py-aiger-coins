import pytest

import aiger_bv as BV
import aiger_discrete
from bidict import bidict

import aiger_coins as C
from aiger_coins.infer import prob, find_coins


def test_infer():
    # Create encoder/decoder for dice.
    lookup = bidict({0: '⚀', 1: '⚁', 2: '⚂', 3: '⚃'})
    encoder = aiger_discrete.Encoding(decode=lookup.get, encode=lookup.inv.get)

    # Represent dice with a 2 bit vector.
    expr1 = BV.uatom(2, '🎲') == encoder.encode('⚀')

    func = aiger_discrete.from_aigbv(
        expr1.aigbv, input_encodings={'🎲': encoder}
    )
    # Create distribution over bits.
    circ = C.pcirc(func) \
            .randomize({'🎲': {'⚀': 1/6, '⚁': 2/6, '⚂': 3/6}})

    assert circ.inputs == set()
    assert circ.outputs == {expr1.output}
    assert circ.coin_biases == (1/3, 1/2)
    assert prob(circ) == pytest.approx(1/6)


def test_find_coins():
    # Create encoder/decoder for dice.
    lookup = bidict({0: '⚀', 1: '⚁', 2: '⚂', 3: '⚃'})
    encoder = aiger_discrete.Encoding(decode=lookup.get, encode=lookup.inv.get)

    expr1 = BV.uatom(2, '🎲') + BV.uatom(2, 'x') + BV.uatom(2, 'z')

    circ = expr1.with_output('y') \
                .aigbv \
                .loopback({'input': 'x', 'output': 'y', 'keep_output': True})

    func = aiger_discrete.from_aigbv(circ, input_encodings={'🎲': encoder})

    # Create distribution over bits.
    pcirc = C.pcirc(func) \
             .randomize({'z': {0: 1/6, 1: 2/6, 2: 3/6}}) \

    model = find_coins(
        pcirc,
        inputs={'🎲': '⚁'},
        outputs={'y': 2},
        latchouts={'x': 2}
    )
    assert model
    len(model) == 1
    model.update({'🎲': '⚁'})
    assert pcirc.circ(model) == ({'y': 2}, {'x': (False, True)})
