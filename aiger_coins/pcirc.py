from __future__ import annotations

import random
from fractions import Fraction
from typing import Any, Callable, Union

import aiger_discrete
import attr
from aiger_discrete import FiniteFunc
from pyrsistent import pmap
from pyrsistent.typing import PMap


Probability = Union[float, Fraction]
Distribution = Callable[[Any], Union[float, Fraction]]


def rejection_sample(name: str, func: FiniteFunc, dist: Distribution) -> Any:
    size = func.imap[name].size
    encoding = func.input_encodings.get(name, aiger_discrete.Encoding())
    while True:
        val = encoding.decode(random.getrandbits(size))
        prob = dist(val)

        if prob == 1:
            return val
        elif prob == 0:
            continue
        elif random.random() <= dist(val):
            return val


def to_finite_func(circ) -> FiniteFunc:
    if isinstance(circ, FiniteFunc):
        return circ
    return aiger_discrete.from_aigbv(circ.aigbv)


@attr.s(frozen=True, auto_attribs=True)
class PCirc:
    circ: FiniteFunc = attr.ib(converter=to_finite_func)
    dist_map: PMap[str, Weights] = attr.ib(converter=pmap, default=pmap())

    @property
    def inputs(self): return self.circ.inputs

    @property
    def outputs(self): return self.circ.outputs

    @property
    def latches(self): return self.circ.latches

    @property
    def latch2init(self): return self.circ.latch2init

    def assume(self, aigbv_like) -> PCirc:
        return attr.evolve(self, circ=self.circ.assume(aigbv_like))
        
    def aig(self):
        pass

    def __lshift__(self, other) -> PCirc:
        pass

    def __rshift__(self, other) -> PCirc:
        pass

    def __or__(self, other) -> PCirc:
        pass

    def __call__(self, inputs, latches=None, max_tries=1_000):
        inputs = dict(inputs)
        for count in range(max_tries + 1):
            inputs.update({
                k: rejection_sample(k, self.circ, dist) 
                for k, dist in self.dist_map.items()
            })
            
            try:
                return self.circ(inputs=inputs, latches=latches)
            except ValueError:  # Invalid input selected.
                # TODO: build BDD to uniformly sample.
                if count <= max_tries:
                    continue
                raise RuntimeError("Rejection Sampling failed!")

    def __getitem__(self, others) -> PCirc:
        pass

    def loopback(self, *wirings) -> PCirc:
        pass

    def unroll(self,
               horizon, *, 
               init=True, 
               omit_latches=True,
               only_last_outputs=False) -> PCirc:
        pass

    simulator = aiger_discrete.FiniteFunc.simulator
    simulate = aiger_discrete.FiniteFunc.simulate


__all__ = ['PCirc']
