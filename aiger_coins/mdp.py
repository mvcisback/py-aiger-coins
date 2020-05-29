from typing import Mapping, Sequence

from fractions import Fraction
from functools import lru_cache

import attr
import funcy as fn

import aiger
import aiger_bv
import aiger_bv as BV
from aiger_bv import uatom, identity_gate, AIGBV
from pyrsistent import pmap
from pyrsistent.typing import PMap

import aiger_coins as aigc


def _create_input2dist(input2dist):
    return pmap({
        k: dist.with_output(k) if k != dist.output else dist
        for k, dist in input2dist.items()
    })


def hash_transition(mdp, prev_latch, action, state):
    return hash(tuple(map(pmap, (prev_latch, action, state))))


BVInput = Mapping[str, Sequence[bool]]


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
        is_valid = uatom(1, 1)
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

    @fn.memoize
    def _cutlatches(self):
        circ1 = self.aigbv
        return circ1.aig.cutlatches(), circ1

    @fn.memoize(key_func=hash_transition)
    def _encode(self, prev_latch, action, state):
        (step, lmap), circ1 = self._cutlatches()
        curr_step = step << aiger.source(prev_latch)

        for a, v in action.items():
            size = circ1.imap[a].size
            const = aiger_bv.source(
                size, aiger_bv.decode_int(v, signed=False),
                name=a, signed=False
            )
            curr_step <<= const.aig

        expr = uatom(1, "##valid") == 1
        for k, v in fn.chain(state.items()):
            expr &= _constraint(k, v)

        curr_step >>= expr.aig

        query = curr_step >> aiger.sink(prev_latch.keys())
        assert len(query.outputs) == 1

        model = solve(query)
        assert model is not None

        # Fill in any model don't cares.
        model = fn.merge({i: False for i in circ1.aig.inputs}, model)

        # HACK. Put model back into bitvector.
        coins = circ1.imap.omit(self.inputs).unblast(model)

        if len(prev_latch) > 0:
            next_latch_circ = curr_step >> aiger.sink(expr.aig.outputs)
            next_latch = next_latch_circ(model)[0]
            assert next_latch.keys() == prev_latch.keys()
            prev_latch = next_latch

        return coins, prev_latch

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

    def _transition_coin(self, start, action, end):
        # 1. Init latches to start.
        circ = self.aigbv.reinit(start)

        # 2. Omit observations. `end` specifies latches.
        for out in self.outputs:
            circ >>= BV.sink(circ.omap[out].size, [out])
        assert circ.outputs == {'##valid'}

        # 3. Create circuit to check valid coin flips.
        assert circ.omap['##valid'].size == 1
        is_valid = BV.UnsignedBVExpr(circ.unroll(1))

        circ >>= BV.sink(1, {'##valid'})  # Assume circ has no outputs now.

        # 4. Expose latchouts via unrolling.
        circ = circ.unroll(1, omit_latches=False)
        end = {f'{k}##time_1': v for k, v in end.items()}
        action = {f'{k}##time_0': v for k, v in action.items()}
        assert set(end.keys()) == circ.outputs
        assert set(action.keys()) <= circ.inputs

        # 5. Create circuit to check if inputs lead to end.
        test_equals = uatom(1, 1)
        for k, v in end.items():
            size = circ.omap[k].size
            test_equals &= uatom(size, k) == uatom(size, v)
        match_end = BV.UnsignedBVExpr(circ >> test_equals.aigbv)

        # 6. Create circuit to assert inputs match action.
        match_action = uatom(1, 1)
        for k, v in action.items():
            size = circ.imap[k].size
            match_action &= uatom(size, k) == uatom(size, v)

        return aigc.Coin(
            expr=match_end & match_action,
            valid=is_valid & match_action,
        )

    def prob(self, start, action, end) -> Fraction:
        """
        Returns the probability of transitioning from start to end
        using action.
        """
        return self._transition_coin(start, action, end).prob()

    def find_env_input(self, start, action, end):
        """
        Returns the probability of transitioning from start to end
        using action.
        """
        coin = self._transition_coin(start, action, end)
        query = coin.expr & coin.valid
        default = {i: query.aigbv.imap[i].size*(False,) for i in query.inputs}

        try:
            from aiger_sat.sat_bv import solve
        except ImportError:
            msg = "Need to install py-aiger-sat to use this method."
            raise ImportError(msg)

        model = solve(query)

        if model is None:
            return None

        model = fn.merge(default, solve(query))
        return {remove_suffix(k, '##time_0'): model[k] for k in query.inputs}


def remove_suffix(val: str, suffix: str) -> str:
    assert val.endswith(suffix)
    return val[:-len(suffix)]


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
    var = uatom(len(v), k)
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
    (_, lmap), _ = mdp._cutlatches()
    prev_latch = dict(lmap.values())
    for action, state in zip(actions, states):
        coins, prev_latch = mdp._encode(prev_latch, action, state)
        yield coins
