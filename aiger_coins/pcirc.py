from __future__ import annotations

import heapq
import random
import uuid
from fractions import Fraction
from functools import reduce
from typing import Any, Mapping, Optional, Sequence, Union

import aiger
import aiger_bv as BV
import aiger_discrete
import attr
import funcy as fn
from aiger_discrete import FiniteFunc


Prob = Union[float, Fraction]
Distribution = Mapping[Any, Prob]


def coin_gadget(name: str,
                dist: Distribution,
                func: FiniteFunc,
                tree_encoding: bool = True) -> PCirc:
    """Return a Probabilistic Circuit representing a distribution.

    - chain encoding. O(|support|)
    - tree encoding. O(log|support|)
    """
    # Transform support of dist to UnsignedBVExpr using encoding.
    size = func.circ.imap[name].size
    encode = func.input_encodings \
                 .get(name, aiger_discrete.Encoding()) \
                 .encode
    dist = ((p, BV.uatom(size, encode(v))) for v, p in dist.items())

    # Create priority queue.
    cost = len if tree_encoding else (lambda x: -len(x))
    queue = [(cost(elem), elem) for elem in dist]

    coins = []
    while len(queue) > 1:
        cost1, (weight1, expr1) = heapq.heappop(queue)
        cost2, (weight2, expr2) = heapq.heappop(queue)

        # Create new coin input.
        coin = BV.uatom(1, None)
        bias = weight1 / (weight1 + weight2)
        coins.append((fn.first(coin.inputs), bias))

        # Merge and add back to queue.
        expr12 = BV.ite(coin, expr1, expr2)
        cost12 = cost1 + cost2  # (-x + -y) == -(x + y).
        weight12 = weight1 + weight2
        heapq.heappush(queue, (cost12, (weight12, expr12)))
    assert len(queue) == 1
    _, (weight, expr) = queue[0]

    expr = expr.bundle_inputs(order=[c for c, _ in coins]) \
               .with_output(name)
    assert len(expr.inputs) == 1
    coins_id = fn.first(expr.inputs)
    biases = tuple(bias for _, bias in coins)
    return PCirc(expr.aigbv, coins_id=coins_id, coin_biases=biases)


def coin_gadgets(dist_map: Mapping[str, Distribution],
                 func: FiniteFunc,
                 tree_encoding: bool = True) -> PCirc:
    """Return a Probabilistic Circuit representing a product distribution."""
    gadgets = (
        coin_gadget(k, v, func, tree_encoding) for k, v in dist_map.items()
    )
    return reduce(PCirc.__or__, gadgets)


def to_finite_func(circ) -> FiniteFunc:
    if isinstance(circ, FiniteFunc):
        return circ
    return aiger_discrete.from_aigbv(circ.aigbv)


def merge_pcirc_coins(circ, left: PCirc, right: PCirc, coins_id: str):
    if not left.has_coins and not right.has_coins:
        biases = ()
    elif left.has_coins and not right.has_coins:
        circ <<= BV.uatom(left.num_coins, coins_id) \
                   .with_output(left.coins_id).aigbv
        biases = left.coin_biases
    elif right.has_coins and not left.has_coins:
        circ <<= BV.uatom(right.num_coins, coins_id) \
                   .with_output(right.coins_id).aigbv
        biases = right.coin_biases
    else:
        coins = BV.uatom(left.num_coins + right.num_coins, coins_id)

        relabeler = coins[:left.num_coins].with_output(left.coins_id).aigbv \
                  | coins[left.num_coins:].with_output(right.coins_id).aigbv  # noqa: E127, E501
        circ <<= relabeler
        biases = tuple(left.coin_biases) + tuple(right.coin_biases)
    return circ, biases


def sample_coins(coin_biases: Sequence[float]) -> int:
    """Return integer where bits bias towards 1 as described in coin_biases."""
    result = 0
    for i, bias in enumerate(coin_biases):
        result |= int(random.random() < bias) << i
    return result


@attr.s(frozen=True, auto_attribs=True)
class PCirc:
    """Wrapper around AIG representing a function with some random inputs."""
    circ: FiniteFunc = attr.ib(converter=to_finite_func)
    coin_biases: Sequence[Prob]           # Bias of each coin flips.
    coins_id: str = "##coins"             # Input reservered for coin flips.

    def __attrs_post_init__(self):
        if not self.has_coins:
            return
        circ: BV.AIGBV = self.circ.circ
        if self.coins_id not in circ.imap:
            raise ValueError("Underlying circuit doesn't have coins input.")
        if circ.imap[self.coins_id].size != len(self.coin_biases):
            raise ValueError("Underlying circuit doesn't have enough coins.")

    @property
    def has_coins(self): return len(self.coin_biases) > 0

    @property
    def inputs(self): return self.circ.inputs - {self.coins_id}

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

    @property
    def num_coins(self): return len(self.coin_biases)

    @property
    def imap(self):
        return self.circ.imap.omit([self.coins_id])

    @property
    def omap(self):
        return self.circ.omap.omit([self.coins_id])

    def assume(self, aigbv_like) -> PCirc:
        """Return Probabilistic Circuit with new assumption over the inputs."""
        return attr.evolve(self, circ=self.circ.assume(aigbv_like))

    def with_coins_id(self, name=None):
        if name is None:
            name = str(uuid.uuid1())
        circ = self.circ
        if self.has_coins:
            circ = self.circ['i', {self.coins_id: name}]
        return attr.evolve(self, circ=circ, coins_id=name)

    def __rshift__(self, other) -> PCirc:
        other = canon(other)
        circ = self.circ >> other.circ
        circ, biases = merge_pcirc_coins(circ, self, other, self.coins_id)
        return PCirc(circ, coins_id=self.coins_id, coin_biases=biases)

    def __lshift__(self, other) -> PCirc:
        return canon(other) >> self

    def __or__(self, other) -> PCirc:
        other = canon(other)
        circ = self.circ | other.circ
        circ, biases = merge_pcirc_coins(circ, self, other, self.coins_id)
        return PCirc(circ, coins_id=self.coins_id, coin_biases=biases)

    def __call__(self, inputs, latches=None):
        inputs = dict(inputs)
        if self.has_coins:
            inputs.setdefault(self.coins_id, sample_coins(self.coin_biases))
        return self.circ(inputs=inputs, latches=latches)

    def __getitem__(self, others) -> PCirc:
        circ = self.circ[others]
        kind, relabels = others
        if (kind == 'i') and (self.coins_id in relabels):
            raise ValueError("Use with_coins_id to relabel coins.")
        return attr.evolve(self, circ=circ)

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
        # Unroll underlying circuit.
        circ = self.circ.unroll(
            horizon=horizon, init=init, omit_latches=omit_latches,
            only_last_outputs=only_last_outputs,
        )

        if not self.has_coins:
            return attr.evolve(self, circ=circ)

        # Merge timed coin sequences into a single input.
        coins = BV.uatom(self.num_coins * horizon, self.coins_id)
        relabeler = BV.aig2aigbv(aiger.empty())
        for time in range(horizon):
            name = f"{self.coins_id}##time_{time}"
            assert name in circ.inputs

            start = time * self.num_coins
            end = start + self.num_coins
            relabeler |= coins[start:end].with_output(name).aigbv
        circ <<= relabeler
        biases = self.coin_biases * horizon

        return PCirc(circ, coins_id=self.coins_id, coin_biases=biases)

    def randomize(self, dist_map: Mapping[str, Distribution]) -> PCirc:
        """Apply distributions in dist_map to corresponding inputs."""
        circ = BV.aig2aigbv(aiger.empty())
        for name in dist_map.keys():
            size = self.circ.circ.imap[name].size  # TODO: propogate imap.
            circ |= BV.identity_gate(size, name)

        func = aiger_discrete.from_aigbv(
            circ=circ,
            input_encodings=self.circ.input_encodings,
            output_encodings=self.circ.output_encodings,
        )
        return pcirc(func, dist_map) >> self

    simulator = aiger_discrete.FiniteFunc.simulator
    simulate = aiger_discrete.FiniteFunc.simulate


def pcirc(func,
          dist_map: Optional[Mapping[str, Distribution]] = None,
          tree_encoding: bool = False) -> PCirc:
    """Lift Discrete Function to a probilistic circuit."""
    func = to_finite_func(func)
    if dist_map is None:
        return PCirc(circ=func, coin_biases=())

    gadgets = coin_gadgets(dist_map, func, tree_encoding)
    return gadgets >> func


def canon(circ) -> PCirc:
    if not isinstance(circ, PCirc):
        circ = PCirc(circ, coin_biases=())
    return circ.with_coins_id()


__all__ = ['PCirc', 'pcirc']
