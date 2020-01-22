from functools import lru_cache

import attr
import funcy as fn

import aiger
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


@lru_cache(maxsize=10_000)
def solve(query):
    try:
        from aiger_sat import solve
    except ImportError:
        raise ImportError("Need to install py-aiger-sat to use this method.")
    return solve(query)


def _find_coin_flips(actions, states, mdp):
    if len(mdp.env_inputs) == 0:
        yield from [{} for _ in actions]
        return

    assert len(actions) == len(states)

    circ1 = mdp.aigbv
    step, lmap = circ1.aig.cutlatches()

    prev_latch = dict(lmap.values())
    for action, state in zip(actions, states):
        curr_step = step << aiger.source(prev_latch)

        for a, v in action.items():
            size = circ1.imap[a].size
            const = aiger_bv.source(
                size, aiger_bv.decode_int(v, signed=False),
                name=a, signed=False
            )
            curr_step <<= const.aig

        expr = atom(1, f"##valid", signed=False) == 1
        for k, v in fn.chain(state.items()):
            expr &= _constraint(k, v)

        curr_step >>= expr.aig

        query = curr_step >> aiger.sink(prev_latch.keys())
        assert len(query.outputs) == 1

        model = solve(query)
        assert model is not None
        # HACK. Put model back into bitvector.
        yield circ1.imap.omit(mdp.inputs).unblast(model)

        if len(prev_latch) > 0:
            next_latch_circ = curr_step >> aiger.sink(expr.aig.outputs)
            next_latch = next_latch_circ(model)[0]
            assert next_latch.keys() == prev_latch.keys()
            prev_latch = next_latch
