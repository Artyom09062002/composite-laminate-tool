"""C4: regression tests for the confirmed review comments on Hashin and progressive failure (verification/REVIEW_C4.md)."""
import math
import unittest

import numpy as np

from core import StrengthAllowables, compute_Q_matrix
from core.failure import (hashin, hashin_fibre_tension_is_shear_dominated, hashin_transverse_shear_strength,
                          transverse_shear_strength_is_assumed)
from core.progressive import (SHEAR_DOMINATED_MODE, DegradationRules, _plan_step, degraded_material, progressive_failure)
from materials import DEFAULT_MATERIALS
from workflow import parse_layup

RECORDS = list(DEFAULT_MATERIALS.values())
MATERIALS = [r.as_core_material() for r in RECORDS]
STRENGTHS = [StrengthAllowables(**r.as_strengths()) for r in RECORDS]
S0 = STRENGTHS[0]
T = 0.125e-3
NXY = np.array([0, 0, 1.0, 0, 0, 0])
NX = np.array([1.0, 0, 0, 0, 0, 0])
MX = np.array([0, 0, 0, 1.0, 0, 0])


def run(layup, unit, **kwargs):
    return progressive_failure(layup, MATERIALS, STRENGTHS, unit, **kwargs)


class PureShearPolicyTests(unittest.TestCase):
    """Comment 2: with alpha = 1 pure shear gives FT = MT = 1; the progressive model must not break the fibres."""

    def test_indices_tie_at_pure_shear_and_the_fibre_term_is_shear_driven(self):
        stress = np.array([0.0, 0.0, S0.S])
        result = hashin(stress, S0)
        self.assertAlmostEqual(result.fibre_tension, 1.0, places=12)
        self.assertAlmostEqual(result.matrix_tension, 1.0, places=12)
        self.assertEqual(result.mode, "Matrix tension")                       # the declared tie-break
        self.assertTrue(hashin_fibre_tension_is_shear_dominated(stress, S0))

    def test_ud_laminate_in_pure_shear_degrades_the_matrix_only(self):
        result = run(parse_layup("[0,0]s", T), NXY)
        self.assertTrue(result.events)
        self.assertEqual({e.family for e in result.events}, {"matrix"})
        self.assertEqual({e.mode for e in result.events}, {SHEAR_DOMINATED_MODE})
        self.assertTrue(all(step.failed_fibre_plies == 0 for step in result.history))
        self.assertAlmostEqual(result.first_ply_load_factor / (S0.S * 4 * T), 1.0, places=9)    # Nxy = S h: initiation unchanged

    def test_literal_rule_still_available_and_damages_both_families(self):
        result = run(parse_layup("[0,0]s", T), NXY, shear_dominated_fibre="fibre")
        self.assertEqual({e.family for e in result.events}, {"fibre", "matrix"})
        with self.assertRaises(ValueError):
            run(parse_layup("[0]", T), NXY, shear_dominated_fibre="both")

    def test_fibre_dominated_tension_is_untouched(self):
        result = run(parse_layup("[0,0]s", T), NX)
        self.assertEqual({e.mode for e in result.events}, {"Fibre tension"})
        self.assertEqual({e.family for e in result.events}, {"fibre"})

    def test_shear_dominance_boundary_and_alpha_zero(self):
        s1 = 0.5 * S0.Xt
        tau_equal = 0.5 * S0.S                                               # normal term == shear term
        self.assertFalse(hashin_fibre_tension_is_shear_dominated(np.array([s1, 0, tau_equal]), S0))
        self.assertTrue(hashin_fibre_tension_is_shear_dominated(np.array([s1, 0, 1.01 * tau_equal]), S0))
        self.assertFalse(hashin_fibre_tension_is_shear_dominated(np.array([0.0, 0, S0.S]), S0, shear_factor=0.0))
        self.assertFalse(hashin_fibre_tension_is_shear_dominated(np.array([-s1, 0, S0.S]), S0))   # compression: no FT mode


class InitiationUnchangedTests(unittest.TestCase):
    """The shear-dominated policy changes the consequence of a failure, never the first-failure load factor."""

    def test_first_failure_is_the_same_for_both_policies(self):
        for text, unit in (("[0,0]s", NXY), ("[0,90]s", NX), ("[45,-45]s", NXY), ("[0,45,-45,90]s", np.array([1.0, 2.0, 0, 0, 0, 0]))):
            layup = parse_layup(text, T)
            a = run(layup, unit, shear_dominated_fibre="matrix")
            b = run(layup, unit, shear_dominated_fibre="fibre")
            self.assertAlmostEqual(a.first_ply_load_factor, b.first_ply_load_factor, delta=1e-9 * a.first_ply_load_factor)


class StepPlanningTests(unittest.TestCase):
    """Comment 10: a terminating exceedance and new failures at the same load factor are handled as one batch."""

    @staticmethod
    def cand(ratio, ply=0, family="fibre"):
        return (ratio, ply, "Bottom", "Fibre tension" if family == "fibre" else "Matrix tension", family)

    def test_new_failure_at_the_terminal_load_factor_is_returned_with_the_termination(self):
        by_level = {0: [self.cand(10.0, 1)], 1: [], 2: [self.cand(10.0, 0, "matrix")]}
        plan = _plan_step(by_level, 5.0)
        self.assertEqual(plan.action, "terminate")
        self.assertEqual([c[1] for c in plan.candidates], [1])
        self.assertEqual(plan.load_factor, 10.0)

    def test_new_failure_within_batch_tolerance_of_the_terminal_one_is_also_recorded(self):
        by_level = {0: [self.cand(10.0 * (1 + 5e-10), 1)], 1: [], 2: [self.cand(10.0, 0, "matrix")]}
        self.assertEqual(len(_plan_step(by_level, 5.0).candidates), 1)

    def test_clearly_later_new_failure_is_not_recorded_by_the_termination(self):
        by_level = {0: [self.cand(10.5, 1)], 1: [], 2: [self.cand(10.0, 0, "matrix")]}
        plan = _plan_step(by_level, 5.0)
        self.assertEqual((plan.action, plan.candidates), ("terminate", ()))

    def test_earlier_new_failure_goes_first(self):
        by_level = {0: [self.cand(9.0, 1)], 1: [], 2: [self.cand(10.0, 0, "matrix")]}
        self.assertEqual(_plan_step(by_level, 5.0).action, "fail")

    def test_escalation_batch_and_exhaustion(self):
        by_level = {0: [self.cand(12.0, 1)], 1: [self.cand(10.0, 0, "matrix")], 2: []}
        plan = _plan_step(by_level, 5.0)
        self.assertEqual((plan.action, plan.load_factor), ("escalate", 10.0))
        self.assertEqual(_plan_step({0: [], 1: [], 2: []}, 5.0).action, "exhausted")

    def test_load_factor_never_decreases_and_a_held_step_is_flagged(self):
        plan = _plan_step({0: [self.cand(4.0, 1)], 1: [], 2: []}, 5.0)
        self.assertEqual((plan.action, plan.load_factor, plan.cascade), ("fail", 5.0, True))
        self.assertFalse(_plan_step({0: [self.cand(6.0, 1)], 1: [], 2: []}, 5.0).cascade)


class HistoryTests(unittest.TestCase):
    """Comment 9: the history is non-decreasing by construction; held (cascade) steps are visible."""

    def test_cross_ply_history_is_monotone_and_reports_held_steps(self):
        result = run(parse_layup("[0,90]s", T), NX)
        loads = [step.load_factor for step in result.history]
        self.assertEqual(loads, sorted(loads))
        self.assertGreaterEqual(result.cascade_steps, 1)
        self.assertIn("not a stability analysis", result.assumptions)


class AssumptionStatementTests(unittest.TestCase):
    """Comments 3, 4, 5, 7, 8: the claims the model makes are labelled as what they are."""

    def test_assumed_transverse_shear_is_reported(self):
        layup = parse_layup("[0,90]s", T)
        self.assertIn("ASSUMED", run(layup, NX).assumptions)
        measured = [StrengthAllowables(S0.Xt, S0.Xc, S0.Yt, S0.Yc, S0.S, St=50e6)]
        result = progressive_failure(layup, MATERIALS[:1], measured, NX)
        self.assertIn("as supplied", result.assumptions)
        self.assertTrue(transverse_shear_strength_is_assumed(S0))
        self.assertFalse(transverse_shear_strength_is_assumed(measured[0]))

    def test_termination_rule_is_not_called_a_strength_cap_or_an_ultimate_load(self):
        text = run(parse_layup("[0,90]s", T), NX).assumptions
        self.assertIn("two-level residual-stiffness termination rule", text)
        self.assertIn("not a validated ultimate or burst load", text)
        self.assertNotIn("cap", text.lower().replace("capacity", ""))

    def test_matrix_compression_equals_one_at_minus_yc_for_any_transverse_shear_strength(self):
        # Equal to 1 for every St: the check does not validate the assumed 53 degree value.
        for st in (0.2 * S0.Yc, 0.377 * S0.Yc, 0.8 * S0.Yc):
            strengths = StrengthAllowables(S0.Xt, S0.Xc, S0.Yt, S0.Yc, S0.S, St=st)
            self.assertAlmostEqual(hashin(np.array([0.0, -S0.Yc, 0.0]), strengths).matrix_compression, 1.0, places=12)

    def test_default_transverse_shear_strength_is_the_mohr_coulomb_cohesion_for_53_degrees(self):
        # Brute-force the Mohr-Coulomb envelope tau = c - sigma_n tan(phi) under uniaxial compression: Yc/c = 2 tan(theta_fp)
        theta_fp = math.radians(53.0)
        phi = 2.0 * (theta_fp - math.pi / 4.0)
        best = min(1.0 / (math.sin(t) * math.cos(t) - math.cos(t) ** 2 * math.tan(phi))
                   for t in np.radians(np.arange(46.0, 80.0, 0.01)))
        self.assertAlmostEqual(best, 2.0 * math.tan(theta_fp), places=4)
        self.assertAlmostEqual(hashin_transverse_shear_strength(S0), S0.Yc / best, delta=1e-4 * S0.Yc)


class FibreFailureResidualTests(unittest.TestCase):
    """Comment 6: optional loss of E2 and G12 after fibre failure (default unchanged)."""

    def test_default_keeps_e2_and_g12_after_fibre_failure(self):
        degraded = degraded_material(MATERIALS[0], DegradationRules(), 1, 0)
        self.assertEqual((degraded["E2"], degraded["G12"]), (MATERIALS[0]["E2"], MATERIALS[0]["G12"]))
        self.assertAlmostEqual(degraded["E1"], 0.01 * MATERIALS[0]["E1"])

    def test_optional_factors_reduce_e2_and_g12_and_q_stays_positive_definite(self):
        rules = DegradationRules(0.01, 0.1, 0.1, fibre_E2_factor=0.2, fibre_G12_factor=0.3)
        for fibre, matrix in ((1, 0), (1, 1), (2, 2)):
            material = degraded_material(MATERIALS[0], rules, fibre, matrix)
            self.assertAlmostEqual(material["E2"], MATERIALS[0]["E2"] * 0.1 ** matrix * 0.2 ** fibre)
            self.assertAlmostEqual(material["G12"], MATERIALS[0]["G12"] * 0.1 ** matrix * 0.3 ** fibre)
            q = np.asarray(compute_Q_matrix(material["E1"], material["E2"], material["G12"], material["v12"]), dtype=float)
            self.assertTrue(np.all(np.linalg.eigvalsh((q + q.T) / 2) > 0))
        self.assertIn("E2 x 0.2", rules.statement())
        with self.assertRaises(ValueError):
            DegradationRules(fibre_E2_factor=0.0)

    def test_variant_runs_and_keeps_the_first_failure(self):
        layup = parse_layup("[0,45,-45,90]s", T)
        base = run(layup, NX)
        variant = run(layup, NX, rules=DegradationRules(fibre_E2_factor=0.1, fibre_G12_factor=0.1))
        self.assertAlmostEqual(base.first_ply_load_factor, variant.first_ply_load_factor, places=9)
        self.assertTrue(math.isfinite(variant.last_ply_load_factor))


class SubplySplittingTests(unittest.TestCase):
    """Comment 11: documented behaviour, not mesh objectivity."""

    def test_load_factors_do_not_change_when_a_physical_ply_is_split_but_the_event_count_does(self):
        whole = run(parse_layup("[0,90]s", T), NX)
        split = run(parse_layup("[0,0,90,90]s", T / 2), NX)
        self.assertAlmostEqual(whole.first_ply_load_factor, split.first_ply_load_factor, delta=1e-9 * whole.first_ply_load_factor)
        self.assertAlmostEqual(whole.last_ply_load_factor, split.last_ply_load_factor, delta=1e-9 * whole.last_ply_load_factor)
        self.assertEqual(len(split.events), 2 * len(whole.events))

    def test_unsymmetric_and_bending_cases_tried_keep_the_load_factors(self):
        for layup, unit in ((parse_layup("[0,90]", T), NX), ([{"theta": 0.0, "t": 4 * T, "mat": 0}], MX)):
            n = len(layup)
            split = [{**ply, "t": ply["t"] / 4} for ply in layup for _ in range(4)]
            a, b = run(layup, unit), run(split, unit)
            self.assertAlmostEqual(a.last_ply_load_factor, b.last_ply_load_factor, delta=1e-9 * a.last_ply_load_factor)


if __name__ == "__main__":
    unittest.main()
