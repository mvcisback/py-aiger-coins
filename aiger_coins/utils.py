import math
from fractions import Fraction

from aigerbv import atom, ite


# Python is deprecating fractions.gcd....
# https://stackoverflow.com/questions/147515/least-common-multiple-for-3-or-more-numbers/147539#147539  # noqa: E501
def lcm(a, b):
    """Return lowest common multiple."""
    return a * b // math.gcd(a, b)


# Simplification of py-aiger-gridworld's chain.
def chain(n):
    x0 = 1 << (n // 2)
    x = atom(n, 'x', signed=False)
    forward = atom(1, 'forward', signed=False)

    x2 = ite(forward, x << 1, x >> 1)
    return x2.aigbv['o', {x2.output: 'x'}].feedback(
        inputs=['x'], outputs=['x'], 
        initials=[x0], keep_outputs=True
    )


def to_frac(prob):
    prob = Fraction(*prob) if isinstance(prob, tuple) else Fraction(prob)
    assert 0 <= prob <= 1
    return prob
