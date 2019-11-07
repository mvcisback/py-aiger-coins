import attr

from aiger_bv import identity_gate, AIGBV
from pyrsistent import pmap
from pyrsistent.typing import PMap

import aiger_coins as aigc


@attr.s(frozen=True, auto_attribs=True, eq=False, order=False)
class MDP:
    aigbv: AIGBV
    input2dist: PMap[str, aigc.Distribution] = pmap()

    @property
    def env_inputs(self):
        return set(self.input2dist.keys())

    @property
    def inputs(self):
        return self.aigbv.inputs - self.env_inputs

    def __lshift__(self, other):
        if isinstance(other, aigc.Distribution):
            other = dist2mdp(other)
        elif isinstance(other, AIGBV):
            other = circ2mdp(other)

        assert isinstance(other, MDP)
        assert not (self.env_inputs & other.env_inputs)
        return circ2mdp(
            circ=self.aigbv >> other.aigbv,
            input2dist=self.input2dist + other.input2dist,
        )

    def __rshift__(self, other):
        assert not isinstance(other, aigc.Distribution)
        return self << other


def circ2mdp(circ, input2dist=None):
    if input2dist is None:
        return MDP(circ)
    return MDP(circ, input2dist=input2dist)


def dist2mdp(dist):
    circ = identity_gate(dist.size, dist.output)
    return circ2mdp(circ=circ, input2dist={dist.output: dist})
