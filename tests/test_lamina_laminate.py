"""Regression checks for the CLT core and the material records."""

import unittest

import numpy as np

from core import assemble_laminate_stiffness, compute_Q_matrix, transform_Q
from materials import DEFAULT_MATERIALS


class LaminaLaminateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.material = DEFAULT_MATERIALS["Graphite/Epoxy (T300/5208)"].as_core_material()

    def test_zero_degree_qbar_equals_q(self) -> None:
        q = compute_Q_matrix(**self.material)
        np.testing.assert_allclose(transform_Q(q, 0.0), q, rtol=0.0, atol=1.0)

    def test_symmetric_laminate_has_negligible_b(self) -> None:
        angles = [0.0, 45.0, -45.0, 90.0, 90.0, -45.0, 45.0, 0.0]
        layup = [{"theta": angle, "t": 0.125e-3, "mat": 0} for angle in angles]
        result = assemble_laminate_stiffness(layup, [self.material])
        np.testing.assert_allclose(result.B, 0.0, atol=1e-9)

    def test_all_zero_laminate_matches_closed_form(self) -> None:
        thickness = 1.0e-3
        q = compute_Q_matrix(**self.material)
        layup = [{"theta": 0.0, "t": thickness / 4.0, "mat": 0} for _ in range(4)]
        result = assemble_laminate_stiffness(layup, [self.material])
        np.testing.assert_allclose(result.A, q * thickness, rtol=1e-12, atol=1e-6)
        np.testing.assert_allclose(result.D, q * thickness**3 / 12.0, rtol=1e-12, atol=1e-12)

    def test_reference_materials_are_physically_admissible(self) -> None:
        for record in DEFAULT_MATERIALS.values():
            self.assertGreater(record.E1, 0)
            self.assertGreater(record.E2, 0)
            self.assertGreater(record.G12, 0)
            self.assertGreater(1 - record.v12**2 * record.E2 / record.E1, 0)


if __name__ == "__main__":
    unittest.main()
