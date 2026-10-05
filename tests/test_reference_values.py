import unittest
import numpy as np
from core import compute_Q_matrix, transform_Q

class ReferenceValueTests(unittest.TestCase):
    def test_graphite_epoxy_q_matches_independent_rounded_values(self):
        # Hand calculation: nu21 = 0.28*10.3/181 = 0.015934; D = 1 - nu12*nu21 = 0.995539
        # Q11 = 181/D = 181.811, Q22 = 10.3/D = 10.346, Q12 = 0.28*10.3/D = 2.897 GPa.
        q = compute_Q_matrix(181e9, 10.3e9, 7.17e9, 0.28) / 1e9
        reference = np.array([[181.811, 2.897, 0.0], [2.897, 10.346, 0.0], [0.0, 0.0, 7.17]])
        np.testing.assert_allclose(q, reference, rtol=0.0, atol=6e-4)

    def test_glass_epoxy_30_degree_qbar_matches_closed_form(self):
        q = compute_Q_matrix(38.6e9, 8.27e9, 4.14e9, 0.26)
        qbar = transform_Q(q, 30.0)
        m, n = np.cos(np.deg2rad(30.0)), np.sin(np.deg2rad(30.0))
        q11, q22, q12, q66 = q[0,0], q[1,1], q[0,1], q[2,2]
        expected11 = q11*m**4 + 2*(q12+2*q66)*m**2*n**2 + q22*n**4
        expected22 = q11*n**4 + 2*(q12+2*q66)*m**2*n**2 + q22*m**4
        expected12 = (q11+q22-4*q66)*m**2*n**2 + q12*(m**4+n**4)
        expected66 = (q11+q22-2*q12-2*q66)*m**2*n**2 + q66*(m**4+n**4)
        expected16 = (q11-q12-2*q66)*m**3*n - (q22-q12-2*q66)*m*n**3
        expected26 = (q11-q12-2*q66)*m*n**3 - (q22-q12-2*q66)*m**3*n
        expected = np.array([[expected11, expected12, expected16], [expected12, expected22, expected26], [expected16, expected26, expected66]])
        np.testing.assert_allclose(qbar, expected, rtol=1e-12, atol=1e-3)

if __name__ == '__main__': unittest.main()
