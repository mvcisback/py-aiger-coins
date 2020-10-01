from __future__ import annotations

import attr
import funcy as fn

import aiger_coins as C


@attr.s(frozen=True, auto_attribs=True)
class RandomVarCirc:
    pcirc: C.PCirc

    def __attrs_post_init__(self):
        assert len(self.pcirc.outputs) == 1

    def __call__(self, inputs, latches=None):
        return self.pcirc(inputs, latches=latches)[0][self.output]

    @property
    def output(self) -> str:
        return fn.first(self.pcirc.outputs)

    def with_output(self, name: str) -> RandomVarCirc:
        return attr.evolve(self, pcirc=self.pcirc.with_output(name))

    def assume(self, pred) -> RandomVarCirc:
        return attr.evolve(self, pcirc=pcirc.assume(pred))


__all__ = ['RandomVarCirc']
