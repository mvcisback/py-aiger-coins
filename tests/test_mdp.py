import aiger_bv
import aiger_ptltl

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


def test_find_coin_flips():
    x, c = map(aiger_ptltl.atom, ('x', 'c'))

    sys = (x & c).historically().aig
    sys = circ2mdp(aiger_bv.aig2aigbv(sys))
    sys <<= coin((1, 2), name='c')

    assert sys.inputs == {'x'}
    assert len(sys.outputs) == 1

    out, *_ = sys.outputs
    sys_actions = 3*[{'x': (True,)}]
    states = 3*[{out: (True,)}]

    actions = sys.encode_trc(sys_actions, states)
    assert not any(v['c'][0] for v in actions)

    sys_actions2, states2 = sys.decode_trc(actions)
    assert sys_actions2 == sys_actions
    assert states2 == states


def test_mdp_readme():
    from aiger_bv import atom
    from aiger_coins import circ2mdp

    x = atom(3, 'x', signed=False)
    y = atom(3, 'y', signed=False)
    expr = (x & y).with_output('x&y')

    mdp1 = circ2mdp(expr)
    dist = aiger_coins.dist((0, 1, 2), name='y')

    mdp2 = dist >> mdp1

    assert mdp1.inputs == {'x', 'y'}
    assert mdp2.inputs == {'x'}

    mdp3 = mdp2 | circ2mdp(aiger_bv.identity_gate(3, 'z'))
    assert mdp3.inputs == {'x', 'z'}
    assert mdp3.outputs == {'x&y', 'z'}

    mdp4 = mdp3.feedback(inputs=['z'], outputs=['x&y'], keep_outputs=True)
    assert mdp4.inputs == {'x'}
    assert mdp4.outputs == {'x&y', 'z'}

    action = atom(1, 'action', signed=False)
    x_prev = atom(1, 'x_prev', signed=False)
    c = atom(1, 'c', signed=False)

    x_next = (x_prev & c & action).with_output('x_next')

    sys = circ2mdp(x_next).feedback(
        keep_outputs=True,
        inputs=['x_prev'], outputs=['x_next'], initials=[(True,)],
    )
    sys <<= coin((1, 2), name='c')
    assert sys.inputs == {'action'}
    assert sys.outputs == {'x_next'}

    sys_actions = 3*[{'action': (True,)}]
    states = 3*[{'x_next': (True,)}]

    actions = sys.encode_trc(sys_actions, states)
    assert not any(v['c'][0] for v in actions)

    sys_actions2, states2 = sys.decode_trc(actions)
    assert sys_actions2 == sys_actions
    assert states2 == states
