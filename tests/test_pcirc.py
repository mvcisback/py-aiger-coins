import aiger_bv as BV

import aiger_coins as C


def test_pcirc_smoke():
    x = BV.uatom(3, 'x')
    y = BV.uatom(3, 'y')
    z = (x + y).with_output('z')

    pcirc = C.PCirc(circ=z, dist_map={'y': lambda _: 1/3}) \
             .assume(y <= 2)

    rvar = C.RandomVarCirc(pcirc)

    # Warning. May be flaky.
    for i in range(3):
        assert 3 <= rvar({'x': 3}) <= 5


def test_pcirc_relabel():
    x = BV.uatom(3, 'x')
    pcirc = C.PCirc(circ=x, dist_map={'x': lambda _: 1/3})
    pcirc2 = pcirc['i', {'x': 'y'}]
    assert pcirc2.inputs == set()
    assert pcirc2.circ.inputs == {'y'}
    assert pcirc2.dist_map['y'](0) == 1/3


def test_seq_compose():
    x = BV.uatom(3, 'x').with_output('y')
    y = BV.uatom(3, 'y').with_output('y')
    pcirc = C.PCirc(circ=y)
    pcirc2 = C.PCirc(circ=x, dist_map={'x': lambda _: 1/3}) >> pcirc
    pcirc3 = pcirc << C.PCirc(circ=x, dist_map={'x': lambda _: 1/3})

    assert pcirc2.outputs == pcirc3.outputs == {'y'}
    assert pcirc2.inputs == pcirc3.inputs == set()
    assert pcirc2.dist_map['x'](0) == pcirc3.dist_map['x'](0) == 1/3

    assert 0 <= pcirc2({})[0]['y'] <= 7

    pcirc4 = C.PCirc(circ=(x + 1).with_output('y')) >> pcirc
    assert pcirc4({'x': 0})[0] == {'y': 1}


def test_par_compose():
    x = BV.uatom(3, 'x').with_output('x')
    y = BV.uatom(3, 'y').with_output('y')

    pcirc_x = C.PCirc(circ=x)
    pcirc_y = C.PCirc(circ=y, dist_map={'y': lambda _: 1/3})

    pcirc_xy = pcirc_x | pcirc_y
    assert pcirc_xy.inputs == {'x'}
    assert pcirc_xy.outputs == {'x', 'y'}
    assert pcirc_xy.dist_map['y'](0) == 1/3


def test_loopback_unroll():
    x = BV.uatom(3, 'x')
    y = BV.uatom(3, 'y')
    adder = (x + y).with_output('z')

    pcirc = C.PCirc(adder, dist_map={'y': lambda _: 1/3}) \
             .assume((y > 0) & (y < 4))

    pcirc2 = pcirc.loopback({
        'input': 'x', 
        'output': 'z',
        'init': 4,
        'keep_output': True,
    })

    assert pcirc2.inputs == set()
    assert pcirc2.outputs == {'z'}
    assert len(pcirc2.latches) == 1
    assert 4 < pcirc2({})[0]['z'] < 8

    pcirc3 = pcirc2.unroll(3)
    assert pcirc3.inputs == set()
    assert pcirc3.outputs == {'z##time_1', 'z##time_2', 'z##time_3'}

    pcirc4 = pcirc2.unroll(3, only_last_outputs=True)
    assert pcirc4.outputs == {'z##time_3'}
    pcirc4({})  # Could technically be any value due to roll back. 
