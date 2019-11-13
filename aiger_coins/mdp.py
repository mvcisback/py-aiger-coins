import attr
import funcy as fn

import aiger_bv
from aiger_bv import atom, identity_gate, AIGBV
from pyrsistent import pmap
from pyrsistent.typing import PMap

import aiger_coins as aigc


def _create_input2dist(input2dist):
    return pmap({
        k: dist.with_output(k) if k != dist.output else dist
        for k, dist in input2dist.items()
    })


@attr.s(frozen=True, auto_attribs=True, eq=False, order=False)
class MDP:
    _aigbv: AIGBV
    input2dist: PMap[str, aigc.Distribution] = attr.ib(
        default=pmap(), converter=_create_input2dist
    )

    @property
    def env_inputs(self):
        return set(self.input2dist.keys())

    @property
    def inputs(self):
        return self._aigbv.inputs - self.env_inputs

    @property
    def outputs(self):
        return self._aigbv.outputs

    @property
    def aigbv(self):
        assert "##valid" not in self.outputs

        circ = self._aigbv
        is_valid = atom(1, 1, signed=False)
        for dist in self.input2dist.values():
            circ <<= dist.expr.aigbv
            is_valid &= dist.valid

        circ |= is_valid.with_output("##valid").aigbv
        return circ

    @property
    def aig(self):
        return self.aigbv.aig

    def __lshift__(self, other):
        if isinstance(other, aigc.Distribution):
            other = dist2mdp(other)
        elif isinstance(other, AIGBV):
            other = circ2mdp(other)

        assert isinstance(other, MDP)
        assert not (self.env_inputs & other.env_inputs)
        return circ2mdp(
            circ=self._aigbv << other._aigbv,
            input2dist=self.input2dist + other.input2dist,
        )

    def __rshift__(self, other):
        assert not isinstance(other, aigc.Distribution)
        return other << self

    def __or__(self, other):
        assert not (self.env_inputs & other.env_inputs)
        return circ2mdp(
            circ=self._aigbv | other._aigbv,
            input2dist=self.input2dist + other.input2dist,
        )

    def feedback(self, inputs, outputs, initials=None, latches=None,
                 keep_outputs=False):
        assert set(inputs) <= self.inputs
        circ = self._aigbv.feedback(
            inputs, outputs, initials, latches, keep_outputs
        )
        return circ2mdp(circ, input2dist=self.input2dist)

    def encode_trc(self, sys_actions, states):
        coin_flips = find_coin_flips(sys_actions, states, mdp=self)
        return [fn.merge(a, c) for a, c in zip(sys_actions, coin_flips)]

    def decode_trc(self, actions):
        circ = self.aigbv
        sys_actions = [fn.project(a, self.inputs) for a in actions]

        states = fn.lpluck(0, circ.simulate(actions))
        assert all(s['##valid'] for s in states)
        states = [fn.omit(s, {'##valid'}) for s in states]

        return sys_actions, states


def circ2mdp(circ, input2dist=None):
    if not isinstance(circ, AIGBV):
        circ = circ.aigbv

    if input2dist is None:
        return MDP(circ)

    return MDP(circ, input2dist=input2dist)


def dist2mdp(dist):
    circ = identity_gate(dist.size, dist.output)
    return circ2mdp(circ=circ, input2dist={dist.output: dist})


def find_coin_flips(actions, states, mdp):
    return list(_find_coin_flips(actions, states, mdp))


def _constraint(k, v):
    var = atom(len(v), k, signed=False)
    return var == aiger_bv.decode_int(v, signed=False)


def _find_coin_flips(actions, states, mdp):
    try:
        from aiger_sat import sat_bv
    except ImportError:
        raise ImportError("Need to install py-aiger-sat to use this method.")
    assert len(actions) == len(states)

    circ1 = mdp.aigbv
    circ2 = circ1.unroll(1)
    for action, state in zip(actions, states):
        action = fn.walk_keys("{}##time_0".format, action)
        state = fn.walk_keys("{}##time_1".format, state)

        circ3 = circ2
        for i in mdp.inputs:
            size = circ1.imap[i].size
            circ3 |= aiger_bv.identity_gate(size, f"{i}##time_0")

        expr = atom(1, f"##valid##time_1", signed=False) == 1
        for k, v in fn.chain(state.items(), action.items()):
            expr &= _constraint(k, v)

        circ3 >>= expr.aigbv
        assert len(circ3.outputs) == 1

        model = sat_bv.solve(aiger_bv.UnsignedBVExpr(circ3))
        model = fn.walk_keys(lambda x: x.split("##time_")[0], model)
        yield model
