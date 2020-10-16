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
