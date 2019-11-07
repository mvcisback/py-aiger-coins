import aiger_bv

import aiger_coins
from aiger_coins.mdp import circ2mdp


def test_mdp_smoke():
    x = aiger_bv.identity_gate(2, 'x')
    y = aiger_bv.identity_gate(3, 'y')

    circ = x | y
    dist = aiger_coins.dist(((0, 3), (1, 3), (2, 3)), name='y')
    assert dist.expr.output == 'y'

    dyn = circ2mdp(circ, {'y': dist})
    assert dyn.inputs == {'x'}

    dyn2 = dist >> circ2mdp(circ)
    assert dyn2.inputs == {'x'}

    assert dyn2.aigbv.inputs == {'x'} | dist.inputs
    assert dyn2.aigbv.outputs == dyn2.outputs | {'##valid'}

    assert '##valid[0]' in dyn2.aig.outputs
