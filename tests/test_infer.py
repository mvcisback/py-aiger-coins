import pytest

import aiger_bv as BV
import aiger_discrete
from bidict import bidict

import aiger_coins as C
from aiger_coins.infer import prob


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
