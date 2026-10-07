"""Fixed-mass, reproducible cylinder count search and independent netting oracle."""
import itertools
import math
import unittest

from core import StrengthAllowables
from core.optimise import DEFAULT_ANGLES, optimise_cylinder
from core.progressive import DegradationRules, progressive_failure
from core.vessel import NETTING_ANGLE_DEG, cylinder_resultants, first_ply_under_unit_load
from materials import DEFAULT_MATERIALS

RECORD = next(iter(DEFAULT_MATERIALS.values()))
MATERIAL = RECORD.as_core_material()
STRENGTHS = StrengthAllowables(**RECORD.as_strengths())
THICKNESS = RECORD.ply_thickness


class OptimiseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seeded = optimise_cylinder(.1, 8, THICKNESS, MATERIAL, STRENGTHS, max_candidates=48)

    def search(self, angles, n=8, **kwargs):
        return optimise_cylinder(.1, n, THICKNESS, MATERIAL, STRENGTHS, angles, **kwargs)

    def test_single_allowed_angle_returns_that_angle_even_for_odd_counts(self):
        for angle in (37., -90.):
            result = self.search([angle], n=5)
            self.assertEqual(len(result.top_layups), 1)
            self.assertEqual(result.top_layups[0].angles_deg, (angle,) * 5)
            self.assertTrue(result.exhaustive)
            self.assertIsNone(result.netting_reference)

    def test_fibre_bound_optimum_is_at_the_netting_angle_for_t300(self):
        theta = NETTING_ANGLE_DEG
        result = self.search([-60., -theta, -45., 45., theta, 60.],
                             objective="fibre_limit", max_candidates=200)
        best = result.top_layups[0]
        self.assertTrue(all(abs(abs(a) - theta) < 1e-10 for a in best.angles_deg))
        # Independent closed-cylinder equilibrium at balanced fibre rupture:
        # pR = Xt*h*sin²(theta) = 2*Xt*h/3.
        exact = 2 * STRENGTHS.Xt * 8 * THICKNESS / (.1 * 3)
        self.assertAlmostEqual(best.fibre_limit_pressure_pa / exact, 1., places=12)
        self.assertAlmostEqual(best.netting_pressure_pa / exact, 1., places=12)
        self.assertAlmostEqual(result.netting_optimum_pressure_pa / exact, 1., places=12)

    def test_seeded_results_are_deterministic_and_ignore_angle_input_order(self):
        repeat = self.search(tuple(reversed(DEFAULT_ANGLES)), max_candidates=48, seed=2026)
        self.assertEqual(self.seeded, repeat)
        self.assertFalse(repeat.exhaustive)
        self.assertEqual(repeat.evaluated_count, 48)
        self.assertEqual(len(repeat.top_layups), 5)

    def test_seed_controls_the_sample_and_does_not_modify_global_random_state(self):
        import random
        random.seed(31)
        before = random.getstate()
        changed = self.search(DEFAULT_ANGLES, max_candidates=48, seed=2027)
        self.assertEqual(before, random.getstate())
        self.assertNotEqual({c.angles_deg for c in changed.ranked},
                            {c.angles_deg for c in self.seeded.ranked})

    def test_fixed_mass_allowed_angles_symmetry_counts_and_unique_candidates(self):
        for candidate in self.seeded.ranked:
            self.assertEqual(len(candidate.angles_deg), 8)
            self.assertEqual(candidate.angles_deg, candidate.angles_deg[::-1])
            self.assertTrue(set(candidate.angles_deg) <= set(DEFAULT_ANGLES))
            self.assertEqual(sum(count for _, count in candidate.counts), 8)
            self.assertAlmostEqual(8 * self.seeded.ply_thickness_m, 8 * THICKNESS)
            self.assertGreaterEqual(candidate.last_ply_pressure_pa, candidate.hashin_first_ply_pressure_pa)
            if not candidate.balanced:
                self.assertIsNone(candidate.netting_pressure_pa)
        self.assertEqual(len({c.angles_deg for c in self.seeded.ranked}), self.seeded.evaluated_count)

    def test_small_space_is_exhausted_and_each_objective_is_ranked(self):
        result = self.search([0., 90.], n=4)
        expected = {half + half[::-1] for half in itertools.combinations_with_replacement((0., 90.), 2)}
        self.assertEqual({c.angles_deg for c in result.ranked}, expected)
        self.assertEqual(result.total_count_vectors, 3)
        self.assertTrue(result.exhaustive)
        for objective, field in (("first_ply", "first_ply_pressure_pa"),
                                 ("last_ply", "last_ply_pressure_pa"),
                                 ("fibre_limit", "fibre_limit_pressure_pa")):
            values = [getattr(c, field) for c in result.top_for(objective)]
            self.assertEqual(values, sorted(values, reverse=True))

    def test_continuous_reference_remains_separate_from_allowed_grid(self):
        result = self.search([0., 90.])
        self.assertTrue(all(set(c.angles_deg) <= {0., 90.} for c in result.ranked))
        self.assertEqual(set(result.netting_reference.angles_deg), {-NETTING_ANGLE_DEG, NETTING_ANGLE_DEG})

    def test_metrics_reuse_existing_models_and_respect_supplied_discount_rules(self):
        rules = DegradationRules(matrix_E2_factor=.3, matrix_G12_factor=.3)
        result = self.search([54.74], rules=rules)
        candidate = result.top_layups[0]
        layup = [{"theta": a, "t": THICKNESS, "mat": 0} for a in candidate.angles_deg]
        unit = cylinder_resultants(1., .1)
        first = first_ply_under_unit_load(layup, [MATERIAL], [STRENGTHS], unit)
        progressive = progressive_failure(layup, [MATERIAL], [STRENGTHS], unit, rules)
        self.assertEqual(candidate.first_ply_pressure_pa, first.pressure_pa)
        self.assertEqual(candidate.last_ply_pressure_pa, progressive.last_ply_load_factor)
        self.assertIn("E2 x 0.3", result.progressive_assumptions)

    def test_pressure_scales_with_inverse_radius_at_fixed_wall_mass(self):
        one = self.search([54.74]).top_layups[0]
        two = optimise_cylinder(.2, 8, THICKNESS, MATERIAL, STRENGTHS, [54.74]).top_layups[0]
        for field in ("first_ply_pressure_pa", "last_ply_pressure_pa", "fibre_limit_pressure_pa"):
            self.assertAlmostEqual(getattr(one, field) / getattr(two, field), 2., places=11)

    def test_invalid_search_parameters_are_rejected(self):
        for kwargs in ({"radius_m": 0}, {"n_plies": 0}, {"n_plies": 3.5},
                       {"ply_thickness_m": math.nan}, {"allowed_angles": []},
                       {"allowed_angles": [91]}, {"seed": 1.5}, {"max_candidates": 0},
                       {"objective": "burst"}, {"max_candidates": 1}):
            params = dict(radius_m=.1, n_plies=8, ply_thickness_m=THICKNESS,
                          material=MATERIAL, strengths=STRENGTHS)
            params.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                optimise_cylinder(**params)


if __name__ == "__main__":
    unittest.main()
