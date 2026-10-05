"""Behavioral checks for the editable teaching workflow and failure screening."""

import math
import unittest

import numpy as np

from core import (
    StrengthAllowables, assemble_laminate_stiffness, evaluate_failure,
    recover_ply_surfaces, tsai_wu_load_factor,
)
from materials import DEFAULT_MATERIALS
from workflow import assess_design, editor_to_layup, is_balanced, is_symmetric, parse_layup


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        record = DEFAULT_MATERIALS["Graphite/Epoxy (T300/5208)"]
        self.material = record.as_core_material()
        self.strengths = StrengthAllowables(**record.as_strengths())

    def test_layup_parser_and_balance(self):
        layup = parse_layup("[0/45/-45/90]s", 0.125e-3)
        self.assertEqual([p["theta"] for p in layup], [0, 45, -45, 90, 90, -45, 45, 0])
        self.assertTrue(is_symmetric(layup))
        self.assertTrue(is_balanced(layup))
        self.assertFalse(is_balanced(parse_layup("[0,45,90]s", 0.125e-3)))

    def test_invalid_editor_rows_are_rejected_not_omitted(self):
        rows = [{"Angle [deg]": 0, "Thickness [mm]": 0.125},
                {"Angle [deg]": "bad", "Thickness [mm]": 0.125}]
        with self.assertRaisesRegex(ValueError, "Ply 2"):
            editor_to_layup(rows)
        for text in ("[0,,90]", "[0,90", "[0,nan]"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_layup(text, 0.125e-3)

    def test_reversing_unsymmetric_stack_flips_b_but_not_a_or_d(self):
        layup = parse_layup("[0,90,45]", 0.125e-3)
        forward = assemble_laminate_stiffness(layup, [self.material])
        reversed_stack = assemble_laminate_stiffness(list(reversed(layup)), [self.material])
        self.assertFalse(is_symmetric(layup))
        np.testing.assert_allclose(forward.A, reversed_stack.A, rtol=1e-12, atol=1e-6)
        np.testing.assert_allclose(forward.D, reversed_stack.D, rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(forward.B, -reversed_stack.B, rtol=1e-12, atol=1e-8)

    def test_published_cross_ply_example_with_rounding(self):
        # Worked [0/90]s example, https://mpolyco.com/learn/classical-laminate-theory
        result = assemble_laminate_stiffness(parse_layup("[0,90]s", 0.125e-3), [self.material])
        self.assertAlmostEqual(result.A[0, 0] / 1e6, 48.039, delta=0.001)
        self.assertAlmostEqual(result.D[0, 0], 1.671, delta=0.001)
        np.testing.assert_allclose(result.B, 0, atol=1e-8)

    def test_interface_strain_continuity_and_stress_jump(self):
        layup = parse_layup("[0,90]", 0.125e-3)
        stiffness = assemble_laminate_stiffness(layup, [self.material])
        response = recover_ply_surfaces(stiffness, layup, [self.material], np.array([1e5, 0, 0, 0, 0, 0]))
        lower_top, upper_bottom = response.ply_surfaces[1:3]
        np.testing.assert_allclose(lower_top.global_strain, upper_bottom.global_strain, rtol=1e-12, atol=1e-12)
        self.assertGreater(abs(lower_top.local_stress[0] - upper_bottom.local_stress[0]), 1e6)

    def test_tsai_wu_multiplier_reaches_failure_and_zero_load_is_unbounded(self):
        stress = np.array([120e6, 10e6, 5e6])
        factor = tsai_wu_load_factor(stress, self.strengths)
        self.assertGreater(factor, 0)
        self.assertAlmostEqual(evaluate_failure(stress * factor, self.strengths).tsai_wu_index, 1, places=12)
        self.assertTrue(math.isinf(tsai_wu_load_factor(np.zeros(3), self.strengths)))

    def test_strength_and_load_validation(self):
        with self.assertRaises(ValueError):
            StrengthAllowables(1, 1, 1, 1, math.nan)
        layup = parse_layup("[0,90]s", 0.125e-3)
        stiffness = assemble_laminate_stiffness(layup, [self.material])
        with self.assertRaises(ValueError):
            recover_ply_surfaces(stiffness, layup, [self.material], np.array([math.inf, 0, 0, 0, 0, 0]))

    def test_comparison_uses_shared_loads_and_zero_load_behavior(self):
        nx = np.array([1e5, 0, 0, 0, 0, 0])
        zero = np.zeros(6)
        along = assess_design("along", "[0,0]s", 0.125e-3, self.material, self.strengths, nx)
        across = assess_design("across", "[90,90]s", 0.125e-3, self.material, self.strengths, nx)
        self.assertLess(abs(along.epsilon_x), abs(across.epsilon_x))
        self.assertNotEqual(along.first_ply_load_factor, across.first_ply_load_factor)
        unloaded = assess_design("unloaded", "[0,0]s", 0.125e-3, self.material, self.strengths, zero)
        self.assertTrue(math.isinf(unloaded.first_ply_load_factor))
        self.assertIsNone(unloaded.critical_ply)

    def test_equal_thickness_orientation_study_and_shear_case(self):
        axial = np.array([1e5, 0, 0, 0, 0, 0])
        zero = assess_design("0 deg", "[0,0]s", 0.125e-3, self.material, self.strengths, axial)
        ninety = assess_design("90 deg", "[90,90]s", 0.125e-3, self.material, self.strengths, axial)
        self.assertAlmostEqual(zero.thickness_m, ninety.thickness_m)
        self.assertGreater(zero.A11, ninety.A11)
        self.assertLess(abs(zero.epsilon_x), abs(ninety.epsilon_x))

        shear = np.array([0, 0, 5e4, 0, 0, 0])
        axial_stack = assess_design("0 deg", "[0,0]s", 0.125e-3, self.material, self.strengths, shear)
        angle_stack = assess_design("+-45 deg", "[45,-45]s", 0.125e-3, self.material, self.strengths, shear)
        self.assertAlmostEqual(axial_stack.thickness_m, angle_stack.thickness_m)
        self.assertGreater(angle_stack.A66, axial_stack.A66)
        self.assertLess(abs(angle_stack.gamma_xy), abs(axial_stack.gamma_xy))


if __name__ == "__main__":
    unittest.main()
