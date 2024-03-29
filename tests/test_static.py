import sys
sys.path.append('..')

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from composites.laminate import read_stack

from bfsplate2d import (BFSPlate2D, update_KC0, DOF, KC0_SPARSE_SIZE, DOUBLE,
        INT)
from bfsplate2d.quadrature import get_points_weights

def test_static(plot=False):
    # number of nodes
    nx = 7
    ny = 5
    points, weights = get_points_weights(nint=4)

    # geometry
    a = 0.5
    b = 0.5

    # material properties
    E = 0.7e11
    nu = 0.3
    lam = read_stack(stack=[0], plyt=0.001, laminaprop=[E, E, nu])

    x = np.linspace(0, a, nx)
    y = np.linspace(0, b, ny)
    x, y = np.meshgrid(x, y)

    # getting nodes
    ncoords = np.vstack((x.T.flatten(), y.T.flatten())).T
    nids = 1 + np.arange(ncoords.shape[0])
    nid_pos = dict(zip(nids, np.arange(len(nids))))

    nids_mesh = nids.reshape(nx, ny)

    n1s = nids_mesh[:-1, :-1].flatten()
    n2s = nids_mesh[1:, :-1].flatten()
    n3s = nids_mesh[1:, 1:].flatten()
    n4s = nids_mesh[:-1, 1:].flatten()

    num_elements = len(n1s)
    print('num_elements', num_elements)

    N = DOF*nx*ny
    Kr = np.zeros(KC0_SPARSE_SIZE*num_elements, dtype=INT)
    Kc = np.zeros(KC0_SPARSE_SIZE*num_elements, dtype=INT)
    Kv = np.zeros(KC0_SPARSE_SIZE*num_elements, dtype=DOUBLE)
    init_k_KC0 = 0

    plates = []
    for n1, n2, n3, n4 in zip(n1s, n2s, n3s, n4s):
        plate = BFSPlate2D()
        plate.n1 = n1
        plate.n2 = n2
        plate.n3 = n3
        plate.n4 = n4
        plate.c1 = DOF*nid_pos[n1]
        plate.c2 = DOF*nid_pos[n2]
        plate.c3 = DOF*nid_pos[n3]
        plate.c4 = DOF*nid_pos[n4]
        plate.ABD = lam.ABD
        plate.lex = a/(nx - 1)
        plate.ley = b/(ny - 1)
        plate.init_k_KC0 = init_k_KC0
        update_KC0(plate, points, weights, Kr, Kc, Kv)
        init_k_KC0 += KC0_SPARSE_SIZE
        plates.append(plate)

    KC0 = coo_matrix((Kv, (Kr, Kc)), shape=(N, N)).tocsc()

    # applying boundary conditions
    # simply supported

    check = np.isclose(ncoords[:, 0], 0.)
    print('boundary conditions', check.sum())
    bk = np.zeros(KC0.shape[0], dtype=bool)
    bk[0::DOF] = check
    bk[1::DOF] = check
    bk[2::DOF] = check
    bk[3::DOF] = check

    bu = ~bk
    print('boundary conditions bu',  bu.sum())

    f = np.zeros(KC0.shape[0], dtype=float)
    check = np.isclose(ncoords[:, 0], a)
    f[2::DOF] = check*1

    Kuu = KC0[bu, :][:, bu]
    fu = f[bu]

    # solving
    uu = spsolve(Kuu, fu)
    u = np.zeros(KC0.shape[0], dtype=float)
    u[bu] = uu

    if False:
        import matplotlib
        matplotlib.use('TkAgg')
        import matplotlib.pyplot as plt
        plt.gca().set_aspect('equal')
        for plate in plates:
            pos1 = nid_pos[plate.n1]
            pos2 = nid_pos[plate.n2]
            pos3 = nid_pos[plate.n3]
            pos4 = nid_pos[plate.n4]
            x1, y1 = ncoords[pos1]
            x2, y2 = ncoords[pos2]
            x3, y3 = ncoords[pos3]
            x4, y4 = ncoords[pos4]
            plt.plot([x1, x2, x3, x4, x1], [y1, y2, y3, y4, y1], '-')
        plt.show()

    w = u[2::DOF].reshape(nx, ny).T
    print('w min max', w.min(), w.max())
    if plot:
        import matplotlib
        matplotlib.use('TkAgg')
        import matplotlib.pyplot as plt
        plt.gca().set_aspect('equal')
        levels = np.linspace(w.min(), w.max(), 300)
        plt.contourf(x, y, w, levels=levels)
        plt.colorbar()
        plt.show()

    assert np.isclose(w.max(), 0.0717, rtol=1e-3)

if __name__ == '__main__':
    test_static(plot=True)
