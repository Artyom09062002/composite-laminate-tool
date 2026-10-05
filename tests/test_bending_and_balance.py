"""Pure-moment loading and material-aware balance checks."""
import math
import unittest

import numpy as np

from core import StrengthAllowables, assemble_laminate_stiffness, recover_ply_surfaces, tsai_wu_load_factor
from materials import DEFAULT_MATERIALS
from workflow import first_ply_limit, is_balanced, parse_layup

GR, GL = (r.as_core_material() for r in DEFAULT_MATERIALS.values())
SGR = StrengthAllowables(**next(iter(DEFAULT_MATERIALS.values())).as_strengths())


class PureMomentTests(unittest.TestCase):
    def test_pure_moments_give_finite_first_ply_factor(self):
        # The mid-plane face of a symmetric stack carries only round-off stress under
        # pure bending; the strength ratio must not fail there.
        for text in ("[0,45,-45,90]s", "[0,90]s", "[0,0]s", "[45,-45]s"):
            layup = parse_layup(text, 0.125e-3)
            stiffness = assemble_laminate_stiffness(layup, [GR])
            for moment in ([0, 0, 0, 50, 0, 0], [0, 0, 0, 0, 50, 0], [0, 0, 0, 0, 0, 50]):
                with self.subTest(layup=text, load=moment):
                    response = recover_ply_surfaces(stiffness, layup, [GR], np.array(moment, float))
                    _, factor, _ = first_ply_limit(response.ply_surfaces, SGR)
                    self.assertTrue(math.isfinite(factor) and factor > 0)

    def test_strength_ratio_handles_round_off_stress(self):
        self.assertTrue(tsai_wu_load_factor(np.array([1e-9, -1e-9, 0.0]), SGR) > 1e6)

    def test_strength_ratio_reaches_failure_under_bending(self):
        layup = parse_layup("[0,90]s", 0.125e-3)
        stiffness = assemble_laminate_stiffness(layup, [GR])
        response = recover_ply_surfaces(stiffness, layup, [GR], np.array([0, 0, 0, 50, 0, 0], float))
        index, factor, criterion = first_ply_limit(response.ply_surfaces, SGR)
        scaled = recover_ply_surfaces(stiffness, layup, [GR], factor * np.array([0, 0, 0, 50, 0, 0], float))
        point = scaled.ply_surfaces[index]
        from core import evaluate_failure
        check = evaluate_failure(point.local_stress, SGR)
        reached = check.tsai_wu_index if criterion == "Tsai–Wu" else check.maximum_stress_utilization
        self.assertAlmostEqual(reached, 1.0, places=6)


class BalanceTests(unittest.TestCase):
    def test_balance_requires_same_material_for_plus_and_minus_plies(self):
        same = [{"theta": a, "t": 0.125e-3, "mat": 1} for a in (45, -45, -45, 45)]
        mixed = [{"theta": 45, "t": 0.125e-3, "mat": 1}, {"theta": -45, "t": 0.125e-3, "mat": 2},
                 {"theta": -45, "t": 0.125e-3, "mat": 2}, {"theta": 45, "t": 0.125e-3, "mat": 1}]
        self.assertTrue(is_balanced(same))
        self.assertFalse(is_balanced(mixed))
        stiffness = assemble_laminate_stiffness(mixed, [GR, GR, GL])
        self.assertGreater(abs(stiffness.A[0, 2]) / stiffness.A[0, 0], 0.1)


if __name__ == "__main__":
    unittest.main()
