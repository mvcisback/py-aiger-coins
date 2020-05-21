from fractions import Fraction
from functools import reduce, wraps

import attr
from aiger_bv import identity_gate, UnsignedBVExpr

import aiger_coins as aigc


def unrelated_coins(left, right):
    return len(left.inputs & right.inputs) == 0


def same_coins(left, right):
    return left.valid.aigbv == right.valid.aigbv


def unary_op(op):
    @wraps(op)
    def _unary_op(dice):
        return dice.evolve(expr=op(dice.expr), valid=dice.valid)

    return _unary_op


def binop(op):
    @wraps(op)
    def binop(left, right):
        if isinstance(right, int):
            return left.evolve(expr=op(left.expr, 1), valid=left.valid)

        expr = op(left.expr, right.expr)
        if same_coins(left, right):
            return left.evolve(expr=expr, valid=left.valid)

        assert unrelated_coins(left, right)
        return left.evolve(expr=expr, valid=left.valid & right.valid)

    return binop


@attr.s(frozen=True, auto_attribs=True, eq=False, order=False)
class Distribution:
    expr: UnsignedBVExpr
    valid: UnsignedBVExpr

    @property
    def aig(self):
        return self.aigbv.aig

    @property
    def aigbv(self):
        return self.expr.aigbv

    @property
    def output(self):
        return self.expr.output

    @property
    def inputs(self):
        return self.expr.inputs

    @property
    def size(self):
        return self.expr.size

    def __getitem__(self, idx):
        expr = self.expr[idx]
        kind = Coin if isinstance(idx, int) else Distribution
        return kind(expr=expr, valid=self.valid)

    def apply(self, func):
        expr = func(self.expr)
        kind = Coin if expr.size == 1 else Distribution
        return kind(expr=expr, valid=self.valid)

    @property
    def coins(self) -> UnsignedBVExpr:
        coins = (
            identity_gate(self.aigbv.imap[i].size, i) for i in self.inputs
        )
        coins = reduce(lambda x, y: x | y, coins)
        return UnsignedBVExpr(coins)

    def condition(self, expr):
        return type(self)(self.expr, expr & self.valid)

    def freqs(self):
        return tuple(self[i].prob() for i in range(self.size))

    def evolve(self, **kwargs):
        return attr.evolve(self, **kwargs)

    def concat(self, other):
        dist = self.apply(lambda x: x.concat(other))
        if same_coins(self, other):
            return dist
        assert unrelated_coins(self, other)
        return dist.condition(other.valid)

    def with_output(self, name):
        return attr.evolve(self, expr=self.expr.with_output(name))

    __add__ = binop(UnsignedBVExpr.__add__)
    __le__ = binop(UnsignedBVExpr.__le__)
    __lt__ = binop(UnsignedBVExpr.__lt__)
    __gt__ = binop(UnsignedBVExpr.__gt__)
    __ge__ = binop(UnsignedBVExpr.__ge__)
    __eq__ = binop(UnsignedBVExpr.__eq__)
    __ne__ = binop(UnsignedBVExpr.__ne__)
    __invert__ = unary_op(UnsignedBVExpr.__invert__)
    __or__ = binop(UnsignedBVExpr.__or__)
    __and__ = binop(UnsignedBVExpr.__and__)
    __xor__ = binop(UnsignedBVExpr.__xor__)

    def __rshift__(self, other):
        assert isinstance(other, aigc.MDP)
        return other << self


@attr.s(frozen=True)
class Coin(Distribution):
    expr: UnsignedBVExpr = attr.ib()
    valid: UnsignedBVExpr = attr.ib()

    @expr.validator
    def check_expr(self, attribute, value):
        if value.size != 1:
            raise ValueError("Must be a 1 sided dice.")

    def prob(self):
        import aiger_bdd
        top, bot = map(aiger_bdd.count, (self.expr & self.valid, self.valid))
        return Fraction(top, bot)


__all__ = ['Coin', 'Distribution']
