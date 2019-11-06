import math
from functools import reduce

import funcy as fn
from aiger_bv import atom, UnsignedBVExpr

from aiger_coins import utils
from aiger_coins.dice import Distribution


def coin(prob, name=None):
    prob = utils.to_frac(prob)
    return mutex_coins((prob, 1 - prob), name=name)[0]


def mutex_coins(probs, name=None, keep_seperate=False):
    """Mutually exclusive coins.

    Encoded using the common denominator method.
    """
    probs = fn.lmap(utils.to_frac, probs)
    assert sum(probs) == 1

    bots = [p.denominator for p in probs]
    lcm = reduce(utils.lcm, bots, 1)
    word_len = max(math.ceil(math.log2(lcm)), 1)
    max_val = 2**word_len
    weights = map(lambda p: p.numerator*(lcm // p.denominator), probs)

    bits = atom(word_len, name, signed=False)
    const_true = ~(bits @ 0)
    total, coins = 0, []
    for i, weight in enumerate(weights):
        lb = const_true if total == 0 else (bits >= total)
        total += weight
        ub = const_true if total == max_val else (bits < total)
        coins.append(lb & ub)

    is_valid = const_true if lcm == max_val else bits < lcm

    if not keep_seperate:
        coins = reduce(UnsignedBVExpr.concat, coins)

    return Distribution(expr=coins, valid=is_valid)


def binomial(n):
    chain = utils.chain(n)
    expr = UnsignedBVExpr(chain.unroll(n, only_last_outputs=True))
    const_true = ~(expr @ 0)
    return Distribution(expr=expr, valid=const_true)
