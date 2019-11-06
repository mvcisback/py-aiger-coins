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

## Biased Coins

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

## Distributions on discrete sets

We now illustrate how to create a set of mutually exclusive coins that
represent distribution over a finite set. For example, a biased three
sided dice can be 1-hot encoded with:

```python
dice, bot = aiger_coins.mutex_coins(
    [(1, 6), (3, 6), (2, 6)]
)
```

Letting, `⚀ = dice[0]`, `⚁ = dice[1]`, `⚂ = dice[2]`, we can ask the
probability of drawing an element of `{⚀, ⚁}` with:

```python
assert Fraction(count(dice[0] | dice[1]), count(bot)) == prob
```

Now to ask what the probability of drawing `x` or `y` is,
one can simply feed it into a circuit that performs that test!

```python
test = aiger.or_gate(['x', 'y']) | aiger.sink(['z'])
assert Fraction(count(circ >> test), count(bot)) == Fraction(2, 3)
```

## Binomial Distributions

`py-aiger-coins` also supports encoding Binomial distributions. There are two options for encoding, 1-hot encoding which is a format similar to that in the discrete sets section and as an unsigned integers. The following snippet shows how the counts correspond to entries in Pascal's triangle.

```python
x = binomial(6, use_1hot=False)
y = binomial(6, use_1hot=True)
for i, v in enumerate([1, 6, 15, 20, 15, 6, 1]):
    assert v == count(x == i)
    assert v == count(y == (1 << i))
```

Dividing by `2**n` (64 in the example above) results in the probabilities of a Bionomial Distribution.
