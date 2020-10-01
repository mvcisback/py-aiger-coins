import aiger_bv as BV

import aiger_coins as C


def test_pcirc_smoke():
    x = BV.uatom(3, 'x')
    y = BV.uatom(3, 'y')
    z = (x + y).with_output('z')

    pcirc = C.PCirc(circ=z, dist_map={'y': lambda x: 1/3}) \
             .assume(y <= 2)

    rvar = C.RandomVarCirc(pcirc)

    # Warning. May be flaky.
    for i in range(3):
        assert 3 <= rvar({'x': 3}) <= 5
