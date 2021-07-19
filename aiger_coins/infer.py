from functools import reduce

import aiger_bv as BV
import networkx as nx
import numpy as np


def prob(circ, *, log=False):
    """Return probability that the output of circ is True given a valid run."""
    # Validate Input
    if circ.inputs:
        raise ValueError("All inputs must be randomized.")

    if len(circ.outputs) != 1:
        raise ValueError("Only support querying probability of single output.")
    output, *_ = circ.outputs
    if len(circ.omap[output]) != 1:
        raise ValueError("Only support single bit output queries.")

    # Note: circ represents Pr(query & valid)
    # Want: Pr(query | valid) = Pr(query & valid) / Pr(valid)
    #
    # Can answer Pr(valid) by creating another circuit such that:
    #
    #      query' = valid, and valid' = True.
    #
    valid_id = circ.circ.valid_id
    valid_test = circ.circ.aigbv.cone(valid_id)
    query_and_valid_test = (BV.uatom(1, output) & BV.uatom(1, valid_id)).aigbv
    query_and_valid_test <<= circ.circ.aigbv
    biases = circ.coin_biases

    result = _lprob(query_and_valid_test, biases)
    result -= _lprob(valid_test, biases)
    return result if log else np.exp(result)


def _lprob(circ, biases):
    # Convert circuit into labeled DAG based on BDD.
    from dfa import dfa2dict
    from bdd2dfa import to_dfa
    from aiger_bdd import to_bdd

    bdd, *_ = to_bdd(circ, renamer=lambda _, x: x)
    dag, root = dfa2dict(to_dfa(bdd, qdd=False))
    graph = nx.DiGraph()
    for node, (label, transitions) in dag.items():
        label = node.label()
        graph.add_node(node, label=label)

        if isinstance(label, bool):
            continue

        for token, node2 in transitions.items():
            graph.add_edge(node, node2, label=token)

    # View graph of MDD as circuit over LogSumExp
    lprobs = {'DUMMY': -float('inf')}
    for node in nx.topological_sort(graph.reverse()):
        val = graph.nodes[node]['label']
        if isinstance(val, bool):
            lprobs[node] = 0 if val else -float('inf')
        else:
            if graph.out_degree(node) == 1:
                left, *_ = graph.neighbors(node)
                right = 'DUMMY'
            else:
                left, right = graph.neighbors(node)

            # Swap if polarity switched.
            if not graph.edges[node, left]['label']:
                right, left = left, right

            _, idx = BV.aigbv.unpack_name(val)
            bias = float(biases[idx])
            log_biases = np.log(np.array([bias, 1 - bias]))
            kid_lprobs = np.array([lprobs[left], lprobs[right]])

            # Compute average likelihood in log scale.
            lprobs[node] = np.logaddexp(*(log_biases + kid_lprobs))

    return lprobs[node]


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
