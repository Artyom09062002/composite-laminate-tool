"""Hybrid (multi-material) laminates and the per-ply material column."""
import math
import unittest
import numpy as np
from core import (assemble_laminate_stiffness, recover_ply_surfaces, StrengthAllowables)
from materials import DEFAULT_MATERIALS
from workflow import editor_to_layup, first_ply_limit

NAMES = ["Sidebar material", *DEFAULT_MATERIALS]
GR, GL = (r.as_core_material() for r in DEFAULT_MATERIALS.values())
SGR, SGL = (StrengthAllowables(**r.as_strengths()) for r in DEFAULT_MATERIALS.values())


class HybridTests(unittest.TestCase):
    def test_material_column_maps_names_to_indices(self):
        rows = [{"Angle [deg]": 0, "Thickness [mm]": 0.125, "Material": NAMES[1]},
                {"Angle [deg]": 90, "Thickness [mm]": 0.125, "Material": NAMES[2]},
                {"Angle [deg]": 45, "Thickness [mm]": 0.125}]           # blank -> sidebar material
        self.assertEqual([p["mat"] for p in editor_to_layup(rows, NAMES)], [1, 2, 0])
        with self.assertRaisesRegex(ValueError, "Ply 1"):
            editor_to_layup([{"Angle [deg]": 0, "Thickness [mm]": 0.1, "Material": "nope"}], NAMES)
        self.assertEqual(editor_to_layup(rows[:1])[0]["mat"], 0)       # old call signature unchanged

    def test_symmetric_hybrid_has_zero_b_and_unsymmetric_hybrid_does_not(self):
        t = 0.125e-3
        sym = [{"theta": 0.0, "t": t, "mat": 0}, {"theta": 0.0, "t": t, "mat": 1},
               {"theta": 0.0, "t": t, "mat": 1}, {"theta": 0.0, "t": t, "mat": 0}]
        uns = [{"theta": 0.0, "t": t, "mat": 0}, {"theta": 0.0, "t": t, "mat": 0},
               {"theta": 0.0, "t": t, "mat": 1}, {"theta": 0.0, "t": t, "mat": 1}]
        np.testing.assert_allclose(assemble_laminate_stiffness(sym, [GR, GL]).B, 0.0, atol=1e-6)
        self.assertGreater(np.max(np.abs(assemble_laminate_stiffness(uns, [GR, GL]).B)), 1.0)

    def test_a11_of_hybrid_is_thickness_weighted_average(self):
        t = 0.125e-3
        layup = [{"theta": 0.0, "t": t, "mat": 0}, {"theta": 0.0, "t": t, "mat": 1}]
        a = assemble_laminate_stiffness(layup, [GR, GL]).A[0, 0]
        q11 = lambda m: m["E1"] / (1 - m["v12"] ** 2 * m["E2"] / m["E1"])
        self.assertAlmostEqual(a, (q11(GR) + q11(GL)) * t, delta=1e-9 * a)

    def test_first_ply_limit_uses_each_plys_own_strengths(self):
        t = 0.125e-3
        layup = [{"theta": 0.0, "t": t, "mat": 0}, {"theta": 0.0, "t": t, "mat": 1}]
        mats = [GR, GL]
        resp = recover_ply_surfaces(assemble_laminate_stiffness(layup, mats), layup, mats,
                                    np.array([1e5, 0, 0, 0, 0, 0]))
        per_ply = [SGR if p.ply == 1 else SGL for p in resp.ply_surfaces]
        _, factor_mixed, _ = first_ply_limit(resp.ply_surfaces, per_ply)
        _, factor_wrong, _ = first_ply_limit(resp.ply_surfaces, SGL)      # glass allowables on the graphite ply
        self.assertTrue(math.isfinite(factor_mixed))
        # equal strain -> the stiffer graphite ply carries more stress and governs; its own
        # Xt (1500 MPa) is higher than glass Xt (1062 MPa), so the wrong allowables under-predict
        self.assertLess(factor_wrong, factor_mixed)


if __name__ == "__main__":
    unittest.main()
