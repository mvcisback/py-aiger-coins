[![Build Status](https://travis-ci.org/mvcisback/py-aiger-coins.svg?branch=master)](https://travis-ci.org/mvcisback/py-aiger-coins)
[![codecov](https://codecov.io/gh/mvcisback/py-aiger-coins/branch/master/graph/badge.svg)](https://codecov.io/gh/mvcisback/py-aiger-coins)
[![Updates](https://pyup.io/repos/github/mvcisback/py-aiger-coins/shield.svg)](https://pyup.io/repos/github/mvcisback/py-aiger-coins/)

[![PyPI version](https://badge.fury.io/py/py-aiger-coins.svg)](https://badge.fury.io/py/py-aiger-coins)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


# py-aiger-coins
Library for creating circuits that encode discrete distributions and
Markov Decision PRocesses. The name comes from the random bit model of
drawing from discrete distributions using coin flips.

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->
**Table of Contents**

- [py-aiger-coins](#py-aiger-coins)
- [Install](#install)
- [Usage](#usage)
    - [Biased Coins](#biased-coins)
    - [Distributions on discrete sets](#distributions-on-discrete-sets)
    - [Distributions and Coins](#distributions-and-coins)
        - [Manipulating Distributions](#manipulating-distributions)
    - [Binomial Distributions](#binomial-distributions)
    - [Markov Decision Processes and Probablistic Circuits](#markov-decision-processes-and-probablistic-circuits)

<!-- markdown-toc end -->


# Install

To install this library run:

`$ pip install py-aiger-coins`

Note that to actually compute probabilities, one needs to install with the bdd option.

`$ pip install py-aiger-coins[bdd]`

For developers, note that this project uses the
[poetry](https://poetry.eustace.io/) python package/dependency
management tool. Please familarize yourself with it and then run:

`$ poetry install`

# Usage

Note this tutorial assumes `py-aiger-bdd` has been installed (see the
Install section).

## Biased Coins

We start by encoding a biased coin and computing its bias. The primary
entrypoint for modeling coins is the `coin` function.

```python
from fractions import Fraction

import aiger_coins

bias = Fraction(1, 3)
coin1 = aiger_coins.coin(bias)
coin2 = aiger_coins.coin((1, 3))  # or just use a tuple.

assert coin1.prob() == coin2.prob() == prob
```

## Distributions on discrete sets

We now illustrate how to create a set of mutually exclusive coins that
represent distribution over a finite set. For example, a biased three
sided dice can be 1-hot encoded with:

```python
dice = aiger_coins.dist([1, 3, 2], name='x')
dice = aiger_coins.dist([(1, 6), (3, 6), (2, 6)], name='x')  # equivalent
dice = aiger_coins.dist([Fraction(1, 6), Fraction(3, 6), Fraction(2, 6)], name='x')  # equivalent

print(dice.freqs())
# (Fraction(1, 6), Fraction(1, 2), Fraction(1, 3))
```

Letting, `⚀ = dice[0]`, `⚁ = dice[1]`, `⚂ = dice[2]`, 
```python
one, two, three = dice[0], dice[1], dice[2]
```

We can ask the probability of drawing an element of `{⚀, ⚁}` with:

```python
assert (one | two).prob() == Fraction(2, 3)
assert (~three).prob() == Fraction(2, 3)
```

## Distributions and Coins

`Distribution`s and `Coin`s are really just wrappers around two
`aiger_bv.UnsignedBVExpr` objects stored in the `expr` and `valid`
attributes.

The attributes `expr` and `valid` encode an expression over fair coin
flips and which coin flips are "valid" respectively. Coins is a
special type of `Distribution` where the expression is a predicate
(e.g. has one output).

Note that accessing the ith element of a `Distribution` results in a
`Coin` encoding the probability of drawing that element.

### Manipulating Distributions

In general `Distribution`s can me manipulated by manipulating the
`.expr` attribution to reinterpret the coin flips or manipulating
`.valid` to condition on different coin flip outcomes.

Out of the box `Distribution`s support a small number of operations:
`+, <, <=, >=, >, ==, !=, ~, |, &, ^, .concat`, which they inherit
from `aiger_bv.UnsignedBVExpr`. When using the same `.valid` predicate
(same coin flips), these operations only manipulate the `.expr`
attribute.

More generally, one can use the `apply` method to apply an arbitrary
function to the `.expr` attribute. For example, using the dice from
before:

```python
dice2 = dice.apply(lambda expr: ~expr[2])
assert dice2[0].freqs() == Fraction(2, 3)
```

One can also change the assumptions made on the coin flips by using
the condition method, for example, suppose we condition on the coin
flips never being all `False`. This changes the distribution
as follows:

```python
coins = dice.coins  #  Bitvector Expression of coin variables.
dice3 = dice.condition(coins != 0)

print(dice3.freqs())
# [Fraction(0, 5), Fraction(3, 5), Fraction(2, 5)]
```

## Binomial Distributions

As a convenience, `py-aiger-coins` also supports encoding Binomial
distributions.

```python
x = binomial(3)

print(x.freqs())
# (Fraction(1, 8), Fraction(3, 8), Fraction(3, 8), Fraction(1, 8))
```

## Markov Decision Processes and Probablistic Circuits

`aiger_coins` also supports modeling Probablistic Circuits, Markov
Decision Process (MDPs), and Markov Chains (MDPs with no inputs).

Internally, the `MDP` object is simply an `AIGBV` bitvector circuit
with some inputs annotated with distributions over their inputs.

The primary entropy point to modeling a Markov Decision Process is
the `circ2mdp` functions.

```python
from aiger_bv import atom
from aiger_coins import circ2mdp, dist2mdp

x = atom(2, 'x', signed=False)
y = atom(3, 'y', signed=False)

mdp1 = circ2mdp(x & y)
mdp1 = circ2mdp((x & y).aigbv)  # equivalent

# Put a distribution over the y input.
dist = aiger_coins.dist((0, 1, 2), name='y')

mdp2 = dist >> mdp1
mdp2 = mdp1 << dist  # equivalent
mdp2 = circ2mdp(x & y, {'y': dist})  # equivalent

assert mdp.inputs == {'x', 'y'}
assert mdp2.inputs == {'x'}

# Can recover put AIG or AIGBV objects using .aig and .aigbv attributes.
## Special output, '##valid', monitors if the sequence of inputs and coin flips was valid.

circ2 = mdp2.aigbv
assert cric2.outputs == mdp2.outputs | {'##valid'}
```
