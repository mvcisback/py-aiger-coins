from functools import reduce

import aiger_bv as BV

import funcy as fn
import networkx as nx
import numpy as np


FALSE = 0b01
TRUE = 0b10


def onehot_gadget(circ):
    output = fn.first(circ.outputs)
    sat = BV.uatom(1, output)
    false, true = BV.uatom(2, FALSE), BV.uatom(2, TRUE)
    return BV.ite(sat, true, false).aigbv


def prob(circ, *, log=False, manager=None):
    from aiger_discrete.mdd import to_mdd
    from mdd.nx import to_nx

    if circ.inputs:
        raise ValueError("All inputs must be randomized.")

    if len(circ.outputs) != 1:
        raise ValueError("Only support querying probability of single output.")

    # Make coins different variables for MDD.
    coins = (BV.uatom(1, f"coin_{i}") for i in range(circ.num_coins))
    coin_blaster = reduce(lambda x, y: x.concat(y), coins)
    coin_blaster = coin_blaster.with_output(circ.coins_id) \
                               .aigbv

    #            Seperate coins          MDD expects 1-hot output
    query = (circ.circ << coin_blaster) >> onehot_gadget(circ)

    # View graph of MDD as circuit over LogSumExp
    graph = to_nx(to_mdd(query))
    biases = {f"coin_{i}": bias for i, bias in enumerate(circ.coin_biases)}

    lprobs = {}
    for node in nx.topological_sort(graph.reverse()):
        val = graph.nodes[node]['label']
        if val == TRUE:
            lprobs[node] = 0
        elif val == FALSE:
            lprobs[node] = -float('inf')
        else:
            left, right = graph.neighbors(node)
            # Swap if polarity switched.
            if graph.edges[node, right]['label']({val: True})[0]:
                right, left = left, right

            bias = biases[val]
            log_biases = np.log(np.array([bias, 1 - bias]))
            kid_lprobs = np.array([lprobs[left], lprobs[right]])

            # Compute average likelihood in log scale.
            lprobs[node] = np.logaddexp(*(log_biases + kid_lprobs))

    result = lprobs[node]
    return result if log else np.exp(result)
