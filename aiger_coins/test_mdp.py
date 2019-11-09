import aiger_bv

import aiger_coins
from aiger_coins import coin
from aiger_coins.mdp import circ2mdp
from aiger_coins.utils import chain


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

    x = aiger_bv.atom(3, 'x', signed=False)
    y = aiger_bv.atom(3, 'y', signed=False)
    mdp = dist >> circ2mdp(x < y)
    assert mdp.inputs == {'x'}
    assert len(mdp.outputs) == 1


def test_closed_system():
    c1 = aiger_bv.atom(1, 'c1', signed=False)
    a = aiger_bv.atom(1, 'a', signed=False)

    dyn = circ2mdp(chain(n=4, state_name='s', action='a'))
    dyn <<= (c1 & a).with_output('a').aigbv
    dyn <<= coin((1, 8), name='c1')

    assert dyn.inputs == {'a'}
    assert dyn.outputs == {'s'}

    c2 = aiger_bv.atom(1, 'c2', signed=False)
    const_false = aiger_bv.atom(1, 0, signed=False)
    state = aiger_bv.atom(5, 's', signed=False)
    clip = state == 0b00001

    policy = circ2mdp(
        aiger_bv.ite(clip, const_false, c2).with_output('a')
    )
    policy <<= coin((1, 8), name='c2')

    sys = (policy >> dyn).feedback(
        inputs=['s'], outputs=['s'], latches=['s_prev2'], keep_outputs=True
    )
    assert sys.inputs == set()
    assert sys.outputs == {'s'}
