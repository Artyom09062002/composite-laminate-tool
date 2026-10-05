import unittest
import numpy as np
from core import assemble_laminate_stiffness, recover_ply_surfaces, StrengthAllowables, evaluate_failure

M = {"E1": 181e9, "E2": 10.3e9, "G12": 7.17e9, "v12": 0.28}

class ResponseFailureTests(unittest.TestCase):
    def test_all_zero_membrane_response_matches_a_inverse(self):
        layup = [{"theta": 0., "t": .125e-3, "mat": 0} for _ in range(8)]
        stiffness = assemble_laminate_stiffness(layup, [M])
        loads = np.array([1e5, 0, 0, 0, 0, 0])
        response = recover_ply_surfaces(stiffness, layup, [M], loads)
        np.testing.assert_allclose(response.midplane_strain, np.linalg.solve(stiffness.A, loads[:3]), rtol=1e-12)
        np.testing.assert_allclose(response.curvature, 0, atol=1e-12)

    def test_zero_stress_is_safe(self):
        strength = StrengthAllowables(1500e6, 1500e6, 40e6, 246e6, 68e6)
        result = evaluate_failure(np.zeros(3), strength)
        self.assertEqual(result.maximum_stress_utilization, 0)
        self.assertEqual(result.tsai_wu_index, 0)

    def test_fibre_tensile_allowable_has_unity_max_stress(self):
        strength = StrengthAllowables(1500e6, 1500e6, 40e6, 246e6, 68e6)
        result = evaluate_failure(np.array([1500e6, 0, 0]), strength)
        self.assertAlmostEqual(result.maximum_stress_utilization, 1.0)

if __name__ == '__main__': unittest.main()
