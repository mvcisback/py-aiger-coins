import math
from fractions import Fraction

from aiger_bv import atom, encode_int, ite


# Python is deprecating fractions.gcd....
# https://stackoverflow.com/questions/147515/least-common-multiple-for-3-or-more-numbers/147539#147539  # noqa: E501
def lcm(a, b):
    """Return lowest common multiple."""
    return a * b // math.gcd(a, b)


# Simplification of py-aiger-gridworld's chain.
def chain(n, state_name='x', action='H'):
    bits = n + 1
    start = encode_int(bits, 1, signed=False)

    x = atom(bits, state_name, signed=False)
    forward = atom(1, action, signed=False)

    x2 = ite(forward, x << 1, x)
    circ = x2.aigbv['o', {x2.output: state_name}]
    return circ.feedback(
        inputs=[state_name], outputs=[state_name],
        latches=[f"{state_name}_prev"],
        initials=[start], keep_outputs=True
    )


def to_frac(prob):
    prob = Fraction(*prob) if isinstance(prob, tuple) else Fraction(prob)
    assert 0 <= prob <= 1
    return prob
