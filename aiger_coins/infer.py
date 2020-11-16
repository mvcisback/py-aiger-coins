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


def coins_preimage(pcirc, *,
                   inputs=None,
                   outputs=None,
                   latchins=None,
                   latchouts=None) -> BV.UnsignedBVExpr:
    if not pcirc.has_coins:
        return BV.uatom(1, 1)

    # Default IO.
    if inputs is None:
        inputs = {}
    if outputs is None:
        outputs = {}
    if latchouts is None:
        latchouts = {}
    if latchins is None:
        latchins = pcirc.latch2init

    # Check interface.
    assert set(inputs) == pcirc.inputs
    assert set(outputs) == pcirc.outputs
    assert set(latchouts) == pcirc.latches
    assert set(latchins) == pcirc.latches

    # Encode IO.
    mappings = [
        (inputs, pcirc.circ.input_encodings),
        (outputs, pcirc.circ.output_encodings),
    ]
    for val_map, enc_map in mappings:
        val_map.update({k: e.encode(val_map[k]) for k, e in enc_map.items()})

    # Cutlatches and add to i/o.
    circ, relabels = pcirc.aigbv.cutlatches()
    relabels = {k: v for k, (v, _) in relabels.items()}  # Drop init info.
    inputs.update({relabels[k]: v for k, v in latchins.items()})
    outputs.update({relabels[k]: v for k, v in latchouts.items()})

    # Fix inputs.
    srcs = (
        BV.uatom(circ.imap[k].size, v).with_output(k).aigbv
        for k, v in inputs.items()
    )
    circ <<= reduce(lambda x, y: x | y, srcs)
    assert len(circ.inputs) == int(pcirc.has_coins)

    # Test for outputs.
    omap = circ.omap
    tests = (BV.uatom(omap[k].size, k) == v for k, v in outputs.items())
    circ >>= reduce(lambda x, y: x & y, tests).aigbv
    assert len(circ.outputs - {pcirc.circ.valid_id}) == bool(circ.outputs)

    # Test for valid.
    if len(circ.outputs) == 2:  # Force valid.
        left, right = (BV.uatom(1, o) for o in circ.outputs)
        circ >>= (left & right).aigbv

    assert len(circ.outputs) == 1
    return BV.UnsignedBVExpr(circ)


def find_coins(pcirc, *,
               inputs=None,
               outputs=None,
               latchins=None,
               latchouts=None):
    from aiger_sat.sat_bv import solve
    expr = coins_preimage(
        pcirc, inputs=inputs, outputs=outputs,
        latchins=latchins, latchouts=latchouts
    )
    model = solve(expr)
    return {k: BV.decode_int(v, signed=False) for k, v in model.items()}


__all__ = ['prob', 'coins_preimage', 'find_coins']
