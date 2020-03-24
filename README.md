# py-aiger-coins


[![Build Status](https://cloud.drone.io/api/badges/mvcisback/py-aiger-coins/status.svg)](https://cloud.drone.io/mvcisback/py-aiger-coins)
[![codecov](https://codecov.io/gh/mvcisback/py-aiger-coins/branch/master/graph/badge.svg)](https://codecov.io/gh/mvcisback/py-aiger-coins)
[![Updates](https://pyup.io/repos/github/mvcisback/py-aiger-coins/shield.svg)](https://pyup.io/repos/github/mvcisback/py-aiger-coins/)
[![PyPI version](https://badge.fury.io/py/py-aiger-coins.svg)](https://badge.fury.io/py/py-aiger-coins)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


Library for creating circuits that encode discrete distributions and
Markov Decision Processes. The name comes from the random bit model of
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
the `circ2mdp` function.

```python
from aiger_bv import atom
from aiger_coins import circ2mdp

x = atom(3, 'x', signed=False)
y = atom(3, 'y', signed=False)
expr = (x & y).with_output('x&y')

mdp1 = circ2mdp(expr)
mdp1 = circ2mdp(expr.aigbv)  # equivalent
```

### Composition

`MDP` can be composed using an API analogous to `aiger_bv.AIGBV` and
`aiger.AIG` sequential circuits. In addition, `MDP` support being feed
actions from a distribution via sequential composition.

```python
# Put a distribution over the y input.
dist = aiger_coins.dist((0, 1, 2), name='y')

mdp2 = dist >> mdp1
mdp2 = mdp1 << dist  # equivalent
mdp2 = circ2mdp(expr, {'y': dist})  # equivalent

assert mdp1.inputs == {'x', 'y'}
assert mdp2.inputs == {'x'}

mdp3 = mdp2 | circ2mdp(aiger_bv.identity_gate(4, 'z'))
assert mdp3.inputs == {'x', 'z'}
assert mdp3.outputs == {'x&y', 'z'}

mdp4 = mdp3.feedback(inputs=['z'], outputs=['x&y'], keep_outputs=True)
assert mdp4.inputs == {'x'}
assert mdp4.outputs == {'x&y', 'z'}
```

### Extracting Circuit
One can transform an `MDP` into an `AIG` or `AIGBV` object using
`.aig` and `.aigbv` attributes. This adds as the coinflips explicitly
as inputs and also adds a special output `##valid` that monitors if
the sequence of inputs and coin flips was valid.

```python
assert mdp.aigbv.outputs == mdp.outputs | {'##valid'}

assert '##valid[0]' in mdp.aig.outputs
```


### Encoding and Decoding Traces

Often times, one is interested in analyzing traces, sequences of
states and actions, through a Markov Decision Process. 

In order to map this to an execution of an `MDP` object, one needs to
find a sequence of coin flip inputs such that feeding the actions and
the coin flip inputs into the circuit generated by `MDP.aigbv`.

This (and its inverse) can be done via the `MDP.encode_trc` and
`MDP.decode_trc` methods.

For example, consider the simple MDP modeled by:

```python
from aiger_bv import atom
from aiger_coins import circ2mdp

action = atom(1, 'action', signed=False)
x_prev = atom(1, 'x_prev', signed=False)
c = atom(1, 'c', signed=False)

x_next = (x_prev & c & action).with_output('x_next')

sys = circ2mdp(x_next).feedback(
    keep_outputs=True,
    inputs=['x_prev'], outputs=['x_next'], initials=[(True,)],
)
sys <<= coin((1, 2), name='c')
assert sys.inputs == {'action'}
assert sys.outputs == {'x_next'}
```

We can encode and decode traces into this model as follows:

```
# Encoding and Decoding

sys_actions = 3*[{'action': (True,)}]
states = 3*[{out: (True,)}]

actions = sys.encode_trc(sys_actions, states)
assert not any(v['c'][0] for v in actions)

sys_actions2, states2 = sys.decode_trc(actions)
assert sys_actions2 == sys_actions
assert states2 == states
```
