import attr

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


def circ2mdp(circ, input2dist=None):
    if not isinstance(circ, AIGBV):
        circ = circ.aigbv

    if input2dist is None:
        return MDP(circ)

    return MDP(circ, input2dist=input2dist)


def dist2mdp(dist):
    circ = identity_gate(dist.size, dist.output)
    return circ2mdp(circ=circ, input2dist={dist.output: dist})


def find_coin_flips(trc, mdp):
    from aiger_sat import sat_bv
    circ = mdp.aigbv.unroll(len(trc))

    expr = atom(1, True, signed=False)
    for t, (ivals, ovals) in enumerate(trc):
        expr &= atom(1, f"##valid##time_{t+1}", signed=False) == 1

        for k, v in ovals.items():
            var = atom(len(v), k + f"##time_{t+1}", signed=False)
            expr &= var == aiger_bv.decode_int(v, signed=False)

        for k, v in ivals.items():
            name = k + f"##time_{t}"
            circ <<= aiger_bv.source(len(v), v, name=name, signed=False)

    circ = circ >> expr.aigbv
    assert len(circ.outputs) == 1

    model = sat_bv.solve(aiger_bv.UnsignedBVExpr(circ))
    return [
        {k: model[f"{k}##time_{t}"] for k in mdp.env_inputs}
        for t in range(len(trc))
    ]
