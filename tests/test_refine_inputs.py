"""Robustness of the UI-to-SI input boundary; mechanics remain unchanged."""
import math
import unittest

import numpy as np

from core import assemble_laminate_stiffness
from materials import DEFAULT_MATERIALS
from workflow import angle_ply_wall, editor_to_layup, parse_layup


class RefineInputTests(unittest.TestCase):
    def row(self, **overrides):
        return {"Angle [deg]": 0, "Thickness [mm]": 0.125, **overrides}

    def test_invalid_thickness_rejected(self):
        for value in (0, -1, math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_layup("[0]", value)
                with self.assertRaises(ValueError):
                    editor_to_layup([self.row(**{"Thickness [mm]": value})])
                with self.assertRaises(ValueError):
                    angle_ply_wall(45, 4, value)

    def test_empty_and_over_limit_stacks(self):
        for text in ("", "[]", "s", "[0,]", ",".join(["0"] * 101), "[" + ",".join(["0"] * 51) + "]s"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_layup(text, 0.125e-3)
        for rows in ([], [self.row()] * 101):
            with self.assertRaises(ValueError):
                editor_to_layup(rows)
        self.assertEqual(len(parse_layup(",".join(["0"] * 100), 0.125e-3)), 100)
        self.assertEqual(len(editor_to_layup([self.row()] * 100)), 100)

    def test_one_ply_recovers_finite_stiffness(self):
        record = DEFAULT_MATERIALS["Graphite/Epoxy (T300/5208)"]
        layup = parse_layup("[45]", 0.125e-3)
        result = assemble_laminate_stiffness(layup, [record.as_core_material()])
        self.assertEqual(len(layup), 1)
        self.assertTrue(np.isfinite(result.ABD).all())

    def test_nonfinite_and_missing_angle_cells(self):
        for value in (math.nan, math.inf, -math.inf, None, ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                editor_to_layup([self.row(**{"Angle [deg]": value})])
        with self.assertRaisesRegex(ValueError, "Ply 1"):
            editor_to_layup([{"Angle [deg]": 45}])
        for value in ("nan", "inf", "-inf"):
            with self.assertRaises(ValueError):
                parse_layup(value, 0.125e-3)
            with self.assertRaises(ValueError):
                angle_ply_wall(float(value), 4, 0.125e-3)

    def test_missing_material_defaults_and_malformed_selection_rejected(self):
        for value in (None, "", "  ", math.nan):
            self.assertEqual(editor_to_layup([self.row(Material=value)], ["A", "B"])[0]["mat"], 0)
        self.assertEqual(editor_to_layup([self.row()], ["A"])[0]["mat"], 0)
        self.assertEqual(editor_to_layup([self.row(Material="B")], ["A", "B"])[0]["mat"], 1)
        for value in ("unknown", 1, math.inf, [], True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                editor_to_layup([self.row(Material=value)], ["A", "B"])
        with self.assertRaises(ValueError):
            editor_to_layup([self.row()], [])

    def test_extreme_angles_reduce_before_mechanics(self):
        material = DEFAULT_MATERIALS["Graphite/Epoxy (T300/5208)"].as_core_material()
        for angle in (1080 + 45, -1080 - 45, 1e20, -1e20, 1e308):
            expected = angle % 180
            if expected >= 90:
                expected -= 180
            parsed = parse_layup(str(angle), 0.125e-3)
            edited = editor_to_layup([self.row(**{"Angle [deg]": angle})])
            self.assertEqual(parsed[0]["theta"], expected)
            self.assertEqual(edited[0]["theta"], expected)
            actual = assemble_laminate_stiffness(parsed, [material])
            reference = assemble_laminate_stiffness(parse_layup(str(expected), 0.125e-3), [material])
            np.testing.assert_allclose(actual.ABD, reference.ABD, rtol=1e-12, atol=1e-12)
        self.assertEqual([p["theta"] for p in parse_layup("[0/45/-45/90]s", 0.125e-3)],
                         [0, 45, -45, 90, 90, -45, 45, 0])

    def test_angle_wall_count_validation_and_large_shared_helper(self):
        for count in (0, 1, -4, 6, 4.0, True):
            with self.subTest(count=count), self.assertRaises(ValueError):
                angle_ply_wall(45, count, 0.125e-3)
        # This helper also supports core dome studies; the editor's 100-ply cap is separate.
        self.assertEqual(len(angle_ply_wall(45, 200, 0.125e-3)), 200)

    def test_mm_to_m_underflow_rejected(self):
        with self.assertRaisesRegex(ValueError, "too small"):
            editor_to_layup([self.row(**{"Thickness [mm]": 5e-324})])


if __name__ == "__main__":
    unittest.main()
