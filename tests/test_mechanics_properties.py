"""Additional independent checks: Q-bar invariants and signs, D16 coupling, failure criteria."""
import math
import unittest
import numpy as np
from core import (assemble_laminate_stiffness, compute_Q_matrix, transform_Q, StrengthAllowables,
                  evaluate_failure, tsai_wu_load_factor)
from core.transformations import transform_stress_strain

GR = {"E1": 181e9, "E2": 10.3e9, "G12": 7.17e9, "v12": 0.28}
STR = StrengthAllowables(1500e6, 1500e6, 40e6, 246e6, 68e6)


class QbarInvariantTests(unittest.TestCase):
    def test_rotation_invariants_and_angle_signs(self):
        q = compute_Q_matrix(**GR)
        # Tsai-Pagano: cos2/cos4 terms cancel in these sums, so they are independent of ply angle
        inv_a = q[0, 0] + q[1, 1] + 2 * q[0, 1]
        inv_b = q[0, 0] + q[1, 1] + 2 * q[2, 2]
        for theta in (15.0, 30.0, 45.0, 60.0, 75.0):
            qb, qm = transform_Q(q, theta), transform_Q(q, -theta)
            self.assertAlmostEqual((qb[0, 0] + qb[1, 1] + 2 * qb[0, 1]) / inv_a, 1.0, places=12)
            self.assertAlmostEqual((qb[0, 0] + qb[1, 1] + 2 * qb[2, 2]) / inv_b, 1.0, places=12)
            np.testing.assert_allclose(qb, qb.T, rtol=1e-12)
            self.assertAlmostEqual(qb[0, 0], qm[0, 0], delta=1.0)           # even in theta
            self.assertAlmostEqual(qb[0, 2], -qm[0, 2], delta=1.0)          # Q16 odd in theta
        qb90 = transform_Q(q, 90.0)
        self.assertAlmostEqual(qb90[0, 0], q[1, 1], delta=1.0)
        self.assertAlmostEqual(qb90[1, 1], q[0, 0], delta=1.0)

    def test_45_degree_stress_rotation_and_strain_energy(self):
        sig = transform_stress_strain(np.array([100e6, 0.0, 0.0]), 45.0, "stress")
        np.testing.assert_allclose(sig, [50e6, 50e6, -50e6], rtol=1e-12)
        eps_xy = np.array([1e-3, -2e-4, 5e-4])
        q = compute_Q_matrix(**GR)
        eps12 = transform_stress_strain(eps_xy, 30.0, "strain")
        sig12 = q @ eps12
        sig_xy = transform_stress_strain(sig12, -30.0, "stress")          # back to x-y
        self.assertAlmostEqual(float(sig_xy @ eps_xy), float(sig12 @ eps12), delta=1e-6 * abs(float(sig12 @ eps12)))
        np.testing.assert_allclose(sig_xy, transform_Q(q, 30.0) @ eps_xy, rtol=1e-10)


class CouplingTests(unittest.TestCase):
    def test_pm45_symmetric_has_bending_twisting_but_no_extension_coupling(self):
        layup = [{"theta": a, "t": 0.125e-3, "mat": 0} for a in (45.0, -45.0, -45.0, 45.0)]
        r = assemble_laminate_stiffness(layup, [GR])
        np.testing.assert_allclose(r.B, 0.0, atol=1e-9)
        self.assertAlmostEqual(r.A[0, 2], 0.0, delta=1e-6 * r.A[0, 0])    # balanced -> A16 = 0
        self.assertGreater(abs(r.D[0, 2]), 1e-3 * r.D[0, 0])              # D16 != 0 (bend-twist)

    def test_quasi_isotropic_in_plane_isotropy(self):
        layup = [{"theta": a, "t": 0.125e-3, "mat": 0} for a in (0, 45, -45, 90, 90, -45, 45, 0)]
        A = assemble_laminate_stiffness(layup, [GR]).A
        self.assertAlmostEqual(A[0, 0] / A[1, 1], 1.0, places=10)
        self.assertAlmostEqual(A[2, 2], (A[0, 0] - A[0, 1]) / 2, delta=1e-6 * A[0, 0])


class FailureCriterionTests(unittest.TestCase):
    def test_tsai_wu_is_one_at_each_uniaxial_strength(self):
        for s in ([1500e6, 0, 0], [-1500e6, 0, 0], [0, 40e6, 0], [0, -246e6, 0], [0, 0, 68e6], [0, 0, -68e6]):
            self.assertAlmostEqual(evaluate_failure(np.array(s), STR).tsai_wu_index, 1.0, places=12)

    def test_compression_branch_of_maximum_stress(self):
        r = evaluate_failure(np.array([-750e6, -123e6, 0.0]), STR)
        self.assertAlmostEqual(r.maximum_stress_utilization, 0.5)
        self.assertIn("compression", r.maximum_stress_mode.lower())

    def test_fi_is_not_proportional_to_load(self):
        s = np.array([600e6, 20e6, 10e6])
        fi = evaluate_failure(s, STR).tsai_wu_index
        half = evaluate_failure(0.5 * s, STR).tsai_wu_index
        self.assertNotAlmostEqual(half, 0.5 * fi, places=3)               # FI scales quadratically + linearly
        self.assertAlmostEqual(evaluate_failure(s * tsai_wu_load_factor(s, STR), STR).tsai_wu_index, 1.0, places=12)


if __name__ == "__main__":
    unittest.main()
