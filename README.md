[![Build Status](https://travis-ci.org/mvcisback/py-aiger-coins.svg?branch=master)](https://travis-ci.org/mvcisback/py-aiger-coins)
[![codecov](https://codecov.io/gh/mvcisback/py-aiger-coins/branch/master/graph/badge.svg)](https://codecov.io/gh/mvcisback/py-aiger-coins)
[![Updates](https://pyup.io/repos/github/mvcisback/py-aiger-coins/shield.svg)](https://pyup.io/repos/github/mvcisback/py-aiger-coins/)

[![PyPI version](https://badge.fury.io/py/py-aiger-coins.svg)](https://badge.fury.io/py/py-aiger-coins)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


# py-aiger-coins
Library for creating circuits that encode discrete distributions. The
name comes from the random bit model of drawing from discrete
distributions using coin flips.

# Install

To install this library run:

`$ pip install py-aiger-coins`

# Usage

This tutorial assumes familiarity with
[py-aiger](https://github.com/mvcisback/py-aiger) and
[py-aiger-bdd](https://github.com/mvcisback/py-aiger-bdd).  `py-aiger`
should automatically be installed with `py-aiger-coins` and
`py-aiger-bdd` can be installed via:

`$ pip install py-aiger-bdd`

We start by encoding a biased coin and computing its
bias. The coin will be encoded as two circuits
`top` and `bot` such that `bias = #top / #bot`, where `#`
indicates model counting.
```python
from fractions import Fraction

import aiger
import aiger_coins
from aiger_bdd import count

prob = Fraction(1, 3)
top, bot = aiger_coins.coin(prob)
top, bot = aiger_coins.coin((1, 3))  # or just use a tuple.

assert Fraction(count(top), count(bot)) == prob
```

Next, we illustrate how to create a set of mutually exclusive coins
that represent distribution over a finite set. Namely, coordinate
`i` is `1` iff the `i`th element of the set is drawn. For
example, a three sided dice can be encoded with:

```
circ, bot = aiger_coins.mutex_coins(
    {'x': (1, 6), 'y': (3, 6), 'z': (1, 6)}
)
```

Now to ask what the probability of drawing `x` or `y` is,
one can simply feed it into a circuit that performs that test!

```
test = aiger.or_gate(['x', 'y']) | aiger.sink(['z'])
assert Fraction(count(circ >> test), count(bot)) == Fraction(2, 3)
```
