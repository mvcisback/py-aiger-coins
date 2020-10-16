# py-aiger-coins

**warning** 3.0.0 and greater are a **major** rewrite of this code
base. I am trying to port most of the useful features.


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

`py-aiger-coins` extends the standard `py-aiger-bv` and
`py-aiger-discrete` abstractions to allow for certain bits to be set
via **biased** coins.

The library centers around the `PCirc` object. The easiest way to use
`py-aiger-coins` is to throught the `pcirc` function.


```python
import aiger_bv as BV
import aiger_coins as C


expr1 = BV.uatom(2, 'x') + BV.uatom(2, 'y')

# Create distribution over bits.
my_pcirc = C.pcirc(expr1) \
            .randomize({'x': {0: 1/6, 1: 2/6, 2: 3/6}})

assert my_pcirc.outputs == {expr1.output}

# This probablistic circuit uses 2 biased coins to represent this input.
assert my_pcirc.num_coins == 2
assert my_pcirc.coin_biases == (1/3, 1/2)

# 'x' input is replaced with coinflips.
assert my_pcirc.inputs == {'y'}

# Underlying circuit now has a single input representing coin inputs.
underlying_circ = my_pcirc.circ

assert underlying_circ.inputs == {'y', my_pcirc.coins_id}
```

Note that `aiger_coins.PCirc` implements the same API as `aiger_bv`
and `aiger_coins`.

## Sequential Circuit API

For example, sequential and parallel composition allow combining
probablistic circuits.

```python
incr = (BV.uatom(2, 'z') + 1)
adder = (BV.uatom(2, 'x') + BV.uatom(2, 'y')).with_output('z')

# Create distribution over bits.
pcirc = C.pcirc(adder)                                         \
         .randomize({'x': {0: 1/6, 1: 2/6, 2: 3/6}})
pcirc >>= incr
```

or

```python
inc_x = C.pcirc(BV.uatom(2, 'x') + 1)          \
         .randomize({'x': {0: 1/3, 2: 2/3}})                      # Pr(x=2) = 2/3

inc_y = C.pcirc(BV.uatom(3, 'y') + 1)          \
         .randomize({'y': {0: 1/3, 5: 1/3, 3: 1/3}})

inc_xy = inc_x | inc_y  #
```

Similarly, `unroll`, `loopback` are also implemented.

**note** `unroll` combines all coin flips into a *single* input in
temporal order.


## Finite Functions

`py-aiger-coins` also works well with the `py-aiger-discrete` API for
working with arbitrary functions over finite sets. For example:

```python
from bidict import bidict  # `pip install bidict`

# Create encoder/decoder for dice.
lookup = bidict({0: '⚀', 1: '⚁', 2: '⚂', 3: '⚃'})     # invertable dictionary.
encoder = aiger_discrete.Encoding(decode=lookup.get, encode=lookup.inv.get)

# Represent dice with a 2 bit vector.
expr1 = BV.uatom(2, '🎲')

# Add encoded dice to x. Because why not.
expr2 = BV.uatom(2, 'x') + expr1
func = aiger_discrete.from_aigbv(
    expr2.aigbv, input_encodings={'🎲': encoder}
)

# Create distribution over bits.
circ = C.pcirc(func) \
        .randomize({'🎲': {'⚀': 1/6, '⚁': 2/6, '⚂': 3/6}})

assert circ.inputs == {'x'}
assert circ.outputs == {expr2.output}
assert circ.coin_biases == (Fraction(1, 3), Fraction(1, 2))
```
