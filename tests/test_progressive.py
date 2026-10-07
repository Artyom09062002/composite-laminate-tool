"""Progressive failure (C3): first-ply to last-ply load factor, failure sequence, degradation rules."""
import math
import unittest

import numpy as np

from core import StrengthAllowables, assemble_laminate_stiffness, compute_Q_matrix, recover_ply_surfaces
from core.failure import first_ply_limit, hashin_load_factors
from core.progressive import DegradationRules, degraded_material, progressive_failure
from core.vessel import NETTING_ANGLE_DEG, cylinder_resultants
from materials import DEFAULT_MATERIALS
from workflow import angle_ply_wall, parse_layup, screen_cylinder

RECORDS = list(DEFAULT_MATERIALS.values())
MATERIALS = [r.as_core_material() for r in RECORDS]
STRENGTHS = [StrengthAllowables(**r.as_strengths()) for r in RECORDS]
GR, SGR = MATERIALS[0], STRENGTHS[0]
T = 0.125e-3
NX = np.array([1.0, 0, 0, 0, 0, 0])          # unit axial load [N/m]: load factors are Nx in N/m


def run(layup, unit=NX, **kwargs):
    return progressive_failure(layup, MATERIALS, STRENGTHS, unit, **kwargs)


class UnidirectionalTests(unittest.TestCase):
    def test_ud_ply_under_tension_fails_at_Xt_at_the_last_ply(self):
        for layup in (parse_layup("[0]", T), parse_layup("[0,0]s", T)):
            result = run(layup)
            thickness = sum(ply["t"] for ply in layup)
            self.assertAlmostEqual(result.last_ply_load_factor / (SGR.Xt * thickness), 1.0, places=9)   # Nx = Xt h
            self.assertAlmostEqual(result.first_ply_load_factor, result.last_ply_load_factor, places=6)
            self.assertTrue(all(e.mode == "Fibre tension" and e.family == "fibre" for e in result.events))
            self.assertEqual(sorted(e.ply for e in result.events), list(range(1, len(layup) + 1)))

    def test_ud_glass_ply_fails_at_its_own_Xt(self):
        layup = [{"theta": 0.0, "t": T, "mat": 1} for _ in range(4)]
        self.assertAlmostEqual(run(layup).last_ply_load_factor / (STRENGTHS[1].Xt * 4 * T), 1.0, places=9)

    def test_ud_ply_under_fibre_compression_fails_at_Xc(self):
        layup = parse_layup("[0,0]s", T)
        result = run(layup, -NX)
        self.assertAlmostEqual(result.last_ply_load_factor / (SGR.Xc * 4 * T), 1.0, places=9)
        self.assertEqual({e.mode for e in result.events}, {"Fibre compression"})

    def test_first_ply_of_a_ud_ply_matches_the_maximum_stress_first_ply(self):
        layup = parse_layup("[0,0]s", T)
        stiffness = assemble_laminate_stiffness(layup, MATERIALS)
        surfaces = recover_ply_surfaces(stiffness, layup, MATERIALS, NX).ply_surfaces
        _, factor, criterion = first_ply_limit(surfaces, SGR)
        self.assertEqual(criterion, "Maximum Stress")
        self.assertAlmostEqual(run(layup).first_ply_load_factor / factor, 1.0, places=9)


class CrossPlyTests(unittest.TestCase):
    def test_0_90s_under_uniaxial_load_fails_matrix_first_and_fibre_last(self):
        result = run(parse_layup("[0,90]s", T))
        self.assertEqual(result.events[0].family, "matrix")
        self.assertEqual(result.events[0].mode, "Matrix tension")
        self.assertEqual({e.ply for e in result.events if e.family == "matrix"}, {2, 3})            # the 90 deg plies
        self.assertEqual(result.events[-1].family, "fibre")
        self.assertEqual(result.events[-1].mode, "Fibre tension")
        self.assertEqual({e.ply for e in result.events if e.family == "fibre"}, {1, 4})             # the 0 deg plies
        self.assertGreater(result.last_ply_load_factor, 1.5 * result.first_ply_load_factor)

    def test_0_90s_last_ply_load_is_the_zero_plies_at_Xt_plus_a_little_residual_matrix_load(self):
        result = run(parse_layup("[0,90]s", T))
        zero_plies_at_Xt = 2 * T * SGR.Xt                                    # two 0 deg plies carrying Xt
        self.assertGreaterEqual(result.last_ply_load_factor, zero_plies_at_Xt)
        self.assertLessEqual(result.last_ply_load_factor, zero_plies_at_Xt + 2 * T * SGR.Yt)   # 90 deg plies carry < Yt


class LoadFactorHistoryTests(unittest.TestCase):
    def check_monotonic(self, result):
        factors = [e.load_factor for e in result.events]
        for before, after in zip(factors, factors[1:]):
            self.assertGreaterEqual(after, before * (1 - 1e-9))
        steps = [h.load_factor for h in result.history]
        self.assertEqual(steps[0], 0.0)
        for before, after in zip(steps, steps[1:]):
            self.assertGreaterEqual(after, before)
        self.assertGreaterEqual(result.last_ply_load_factor, steps[-1])
        self.assertGreaterEqual(result.last_ply_load_factor, result.first_ply_load_factor)
        self.assertEqual(result.first_ply_load_factor, factors[0])
        stiffness = [h.stiffness_ratio for h in result.history]
        self.assertEqual(stiffness[0], 1.0)
        self.assertTrue(all(b <= a * (1 + 1e-9) for a, b in zip(stiffness, stiffness[1:])))     # failure never stiffens
        self.assertTrue(all(s > 0 for s in stiffness))

    def test_load_factor_is_non_decreasing_for_standard_layups_and_loads(self):
        loads = {"Nx": NX, "Ny": np.array([0, 1.0, 0, 0, 0, 0]), "Nxy": np.array([0, 0, 1.0, 0, 0, 0]),
                 "-Nx": -NX, "biaxial": np.array([1.0, 0.5, 0.2, 0, 0, 0]), "bending": np.array([0, 0, 0, 1.0, 0, 0]),
                 "pressure": cylinder_resultants(1.0, 0.1)}
        for text in ("[0,90]s", "[0,45,-45,90]s", "[45,-45]s", "[0,0]s", "[30,-30,90]s", "[0,45,-45,90]"):
            for name, unit in loads.items():
                with self.subTest(layup=text, load=name):
                    self.check_monotonic(run(parse_layup(text, T), unit))

    def test_load_factor_is_non_decreasing_for_random_hybrid_layups(self):
        rng = np.random.default_rng(2024)                                  # fixed seed: deterministic
        for _ in range(150):
            angles = rng.choice([0, 15, 30, 45, 60, 75, 90, -45, -30], size=int(rng.integers(1, 11)))
            layup = [{"theta": float(a), "t": T * float(rng.choice([1, 2])), "mat": int(rng.integers(0, 2))} for a in angles]
            unit = np.concatenate([rng.normal(size=3) * 1e3, rng.normal(size=3) * (rng.random() < 0.3)])
            if np.any(unit):
                self.check_monotonic(run(layup, unit))

    def test_each_family_of_each_ply_fails_at_most_once_and_the_first_event_is_hashin_first_ply(self):
        layup = parse_layup("[0,45,-45,90]s", T)
        result = run(layup)
        keys = [(e.ply, e.family) for e in result.events]
        self.assertEqual(len(keys), len(set(keys)))
        surfaces = recover_ply_surfaces(assemble_laminate_stiffness(layup, MATERIALS), layup, MATERIALS, NX).ply_surfaces
        expected = min(min(hashin_load_factors(p.local_stress, SGR).values()) for p in surfaces)
        self.assertAlmostEqual(result.first_ply_load_factor / expected, 1.0, places=9)

    def test_load_strain_curve_is_piecewise_linear_with_jumps_at_failures(self):
        result = run(parse_layup("[0,90]s", T))
        load, strain = result.load_strain_curve(0)
        self.assertEqual((load[0], strain[0]), (0.0, 0.0))
        self.assertEqual(load[-1], result.last_ply_load_factor)
        self.assertTrue(np.all(np.diff(load) >= 0))
        self.assertAlmostEqual(strain[-1], result.final_strain[0])
        self.assertTrue(np.all(np.diff(strain) >= -1e-15))                  # tension: strain grows, failures add jumps
        first_step = result.history[1]
        self.assertGreater(first_step.strain_after[0], first_step.strain_before[0])           # softening: same load, more strain
        self.assertAlmostEqual(first_step.strain_before[0], result.first_ply_load_factor * np.linalg.solve(
            assemble_laminate_stiffness(parse_layup("[0,90]s", T), MATERIALS).A, NX[:3])[0], places=15)


class DegradationTests(unittest.TestCase):
    def test_rules_scale_the_documented_properties_and_keep_S12(self):
        rules = DegradationRules(fibre_E1_factor=0.02, matrix_E2_factor=0.2, matrix_G12_factor=0.05)
        fibre = degraded_material(GR, rules, True, False)
        self.assertAlmostEqual(fibre["E1"] / GR["E1"], 0.02)
        self.assertEqual((fibre["E2"], fibre["G12"]), (GR["E2"], GR["G12"]))
        matrix = degraded_material(GR, rules, False, True)
        self.assertEqual(matrix["E1"], GR["E1"])
        self.assertAlmostEqual(matrix["E2"] / GR["E2"], 0.2)
        self.assertAlmostEqual(matrix["G12"] / GR["G12"], 0.05)
        both = degraded_material(GR, rules, True, True)
        for material in (fibre, matrix, both):
            self.assertAlmostEqual(material["v12"] / material["E1"], GR["v12"] / GR["E1"], places=24)   # S12 unchanged
        self.assertEqual(degraded_material(GR, rules, False, False), GR)

    def test_a_failure_never_stiffens_the_ply_in_any_direction_and_q_stays_positive_definite(self):
        for rules in (DegradationRules(), DegradationRules(0.001, 0.01, 0.01), DegradationRules(0.5, 0.5, 0.5)):
            for base in MATERIALS:
                q_old = compute_Q_matrix(base["E1"], base["E2"], base["G12"], base["v12"])
                for fibre, matrix in ((True, False), (False, True), (True, True)):
                    m = degraded_material(base, rules, fibre, matrix)
                    q_new = compute_Q_matrix(m["E1"], m["E2"], m["G12"], m["v12"])
                    self.assertGreater(np.linalg.eigvalsh(q_new).min(), 0.0)
                    self.assertGreaterEqual(np.linalg.eigvalsh(q_old - q_new).min(), -1e-6 * q_old.max())

    def test_invalid_rules_and_loads_are_rejected(self):
        for kwargs in ({"fibre_E1_factor": 0.0}, {"matrix_E2_factor": 1.5}, {"matrix_G12_factor": math.nan}):
            with self.assertRaises(ValueError):
                DegradationRules(**kwargs)
        layup = parse_layup("[0,90]s", T)
        for bad in (np.zeros(6), np.ones(3), np.array([math.inf, 0, 0, 0, 0, 0])):
            with self.assertRaises(ValueError):
                run(layup, bad)

    def test_assumptions_are_stated_in_the_result(self):
        result = run(parse_layup("[0,90]s", T))
        self.assertIn("model assumptions", result.assumptions)
        self.assertIn("E1 x 0.01", result.assumptions)
        self.assertEqual(result.rules, DegradationRules())

    def test_softer_residual_factors_do_not_raise_the_last_ply_load_of_a_cross_ply(self):
        layup = parse_layup("[0,90]s", T)
        soft = run(layup, rules=DegradationRules(fibre_E1_factor=0.01, matrix_E2_factor=0.01, matrix_G12_factor=0.01))
        stiff = run(layup, rules=DegradationRules(fibre_E1_factor=0.01, matrix_E2_factor=0.3, matrix_G12_factor=0.3))
        self.assertLessEqual(soft.last_ply_load_factor, stiff.last_ply_load_factor * (1 + 1e-9))
        self.assertEqual(soft.first_ply_load_factor, stiff.first_ply_load_factor)          # first ply is pristine: rules-free

    def test_residual_strength_cap_escalates_a_cracked_ply_without_ending_the_analysis_early(self):
        # With E2 = G12 = 0.5 the cracked 90 deg plies reach Yt again (at 0.78 % strain) before the 0 deg fibres fail
        # (0.83 %). That is an escalation of the 90 deg plies, not the end of the laminate: the 0 deg plies still carry
        # 2 t Xt, so the last-ply load must not fall below it.
        layup = parse_layup("[0,90]s", T)
        result = run(layup, rules=DegradationRules(fibre_E1_factor=0.01, matrix_E2_factor=0.5, matrix_G12_factor=0.5))
        kinds = [h.kind for h in result.history[1:]]
        self.assertIn("escalation", kinds)
        self.assertLess(kinds.index("escalation"), len(kinds) - 1)                         # a failure step follows it
        self.assertGreaterEqual(result.last_ply_load_factor, 2 * T * SGR.Xt)
        self.assertEqual(result.events[-1].mode, "Fibre tension")
        escalated = {item for h in result.history for item in h.escalations}
        self.assertEqual(escalated, {(2, "matrix"), (3, "matrix")})
        self.assertEqual([e.step for e in result.events], sorted(e.step for e in result.events))


class PressureVesselTests(unittest.TestCase):
    def test_pressure_load_factor_is_the_burst_pressure_and_last_ply_exceeds_first_ply(self):
        wall = angle_ply_wall(55.0, 16, T)
        result = run(wall, cylinder_resultants(1.0, 0.1))
        self.assertGreater(result.last_ply_load_factor, 1.5 * result.first_ply_load_factor)
        self.assertEqual(result.events[0].family, "matrix")
        self.assertEqual(result.events[-1].family, "fibre")

    def test_at_the_netting_angle_the_last_ply_pressure_is_close_to_the_netting_burst_pressure(self):
        # Fibres alone carry netting loads; the residual matrix stiffness adds a little, so the last-ply pressure sits
        # marginally above the fibre-only estimate (a consistency check of the model, not a validation).
        radius = 0.1
        wall = angle_ply_wall(NETTING_ANGLE_DEG, 16, T)
        netting = screen_cylinder(wall, MATERIALS, STRENGTHS, radius).netting_pressure_pa
        last = run(wall, cylinder_resultants(1.0, radius)).last_ply_load_factor
        self.assertGreater(netting, 0.0)
        self.assertLess(abs(last / netting - 1.0), 0.03)


if __name__ == "__main__":
    unittest.main()
