import math
from fractions import Fraction

from aigerbv import atom


def _kmodels(var, k, max_val):
    return atom(var.size, 1, signed=False) if k == max_val else var < k


def biased_coin(prob, input_name=None):
    prob = Fraction(*prob) if isinstance(prob, tuple) else Fraction(prob)
    assert 0 <= prob <= 1

    word_len = max(math.ceil(math.log2(prob.denominator)), 1)
    max_val = 2**word_len

    var = atom(word_len, input_name, signed=False)
    num = _kmodels(var, prob.numerator, max_val)
    dem = _kmodels(var, prob.denominator, max_val)
    return num, dem
