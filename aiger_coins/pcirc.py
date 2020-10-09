from __future__ import annotations

import random
from fractions import Fraction
from typing import Any, Callable, Union

import aiger_discrete
import attr
from aiger_discrete import FiniteFunc
from aiger_discrete.discrete import project, TIMED_NAME
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
    """Wrapper around AIG representing a function with some random inputs."""
    circ: FiniteFunc = attr.ib(converter=to_finite_func)
    dist_map: PMap[str, Probability] = attr.ib(converter=pmap, default=pmap())

    def __attrs_post_init__(self):
        """Make sure unneeded distributions are forgotten."""
        dist_map = project(self.dist_map, self.circ.inputs)
        object.__setattr__(self, "dist_map", dist_map)

    @property
    def inputs(self): return self.circ.inputs - set(self.dist_map.keys())

    @property
    def outputs(self): return self.circ.outputs

    @property
    def latches(self): return self.circ.latches

    @property
    def latch2init(self): return self.circ.latch2init

    @property
    def aig(self): return self.circ.aig

    @property
    def aigbv(self): return self.circ.aigbv

    def assume(self, aigbv_like) -> PCirc:
        """Return Probabilistic Circuit with new assumption over the inputs."""
        return attr.evolve(self, circ=self.circ.assume(aigbv_like))

    def __rshift__(self, other) -> PCirc:
        circ = self.circ >> canon(other).circ
        return PCirc(circ, other.dist_map + self.dist_map)

    def __lshift__(self, other) -> PCirc:
        return canon(other) >> self

    def __or__(self, other) -> PCirc:
        if set(self.dist_map.keys()) & set(self.dist_map.keys()):
            raise ValueError("Circuits have conflicting dist_maps.")
        circ = self.circ | canon(other).circ
        return PCirc(circ, self.dist_map + other.dist_map)

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
        circ = self.circ[others]
        kind, relabels = others

        kwargs = {}
        if kind == 'i':
            evolver = self.dist_map.evolver()
            for old, new in relabels.items():
                if old not in self.dist_map:
                    continue
                evolver[new] = self.dist_map[old]
                del evolver[old]
            kwargs['dist_map'] = evolver.persistent()

        return attr.evolve(self, circ=circ, **kwargs)

    def loopback(self, *wirings) -> PCirc:
        inputs = self.inputs
        assert all(w['input'] in inputs for w in wirings)
        circ = self.circ.loopback(*wirings)
        return attr.evolve(self, circ=circ)

    def unroll(self,
               horizon, *,
               init=True,
               omit_latches=True,
               only_last_outputs=False) -> PCirc:
        circ = self.circ.unroll(
            horizon=horizon,
            init=init,
            omit_latches=omit_latches,
            only_last_outputs=only_last_outputs,
        )
        dist_map = {}
        for timed_name in circ.inputs:
            # Should always match because of unrolling.
            name = TIMED_NAME.match(timed_name).groups()[0]
            if name not in self.dist_map:
                continue
            dist_map[timed_name] = self.dist_map[name]

        return attr.evolve(self, circ=circ, dist_map=dist_map)

    simulator = aiger_discrete.FiniteFunc.simulator
    simulate = aiger_discrete.FiniteFunc.simulate

    def use_faircoins(self) -> PCirc:
        # TODO: return PCirc where
        # 1. every random variable's encoding is i.d.
        # 2. every random distribution is over fair coins.
        pass

    def with_distmap(self, dist_map) -> PCirc:
        """Update the distributions over the inputs."""
        return attr.evolve(self, dist_map=self.dist_map + pmap(dist_map))


def canon(circ) -> PCirc:
    if isinstance(circ, PCirc):
        return circ
    return PCirc(circ)  # Assume aigbv like.


__all__ = ['PCirc']
