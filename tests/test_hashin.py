"""Hashin 2D failure criterion (C3): four modes, shear contribution, strength ratios, agreement with Max Stress."""
import math
import unittest

import numpy as np

from core import StrengthAllowables, evaluate_failure, hashin
from core.failure import (HASHIN_MODES, _hashin_indices, hashin_load_factors, hashin_transverse_shear_strength,
                          maximum_stress)

S = StrengthAllowables(Xt=1500e6, Xc=1500e6, Yt=40e6, Yc=246e6, S=68e6)
S_ASYM = StrengthAllowables(Xt=1062e6, Xc=610e6, Yt=31e6, Yc=118e6, S=72e6)


class HashinModeTests(unittest.TestCase):
    def test_each_mode_reaches_one_at_its_pure_strength(self):
        for allow in (S, S_ASYM):
            cases = {"Fibre tension": [allow.Xt, 0, 0], "Fibre compression": [-allow.Xc, 0, 0],
                     "Matrix tension": [0, allow.Yt, 0], "Matrix compression": [0, -allow.Yc, 0]}
            for mode, stress in cases.items():
                result = hashin(np.array(stress, dtype=float), allow)
                self.assertAlmostEqual(result.index, 1.0, places=12, msg=mode)
                self.assertEqual(result.mode, mode)
                self.assertAlmostEqual(result.load_factor, 1.0, places=12, msg=mode)
                self.assertAlmostEqual(result.indices[mode], 1.0, places=12)

    def test_only_the_mode_matching_the_stress_sign_is_active(self):
        r = hashin(np.array([-500e6, 20e6, 0.0]), S)
        self.assertEqual(r.fibre_tension, 0.0)
        self.assertEqual(r.matrix_compression, 0.0)
        self.assertGreater(r.fibre_compression, 0.0)
        self.assertGreater(r.matrix_tension, 0.0)
        self.assertEqual(r.mode, "Matrix tension")                       # 0.25 against 0.111

    def test_shear_contribution(self):
        shear = np.array([0.0, 0.0, S.S])
        both = hashin(shear, S)                                          # alpha = 1: FT = MT = 1; matrix wins the tie
        self.assertAlmostEqual(both.fibre_tension, 1.0)
        self.assertAlmostEqual(both.matrix_tension, 1.0)
        self.assertEqual(both.mode, "Matrix tension")
        rotem = hashin(shear, S, shear_factor=0.0)                       # Hashin-Rotem: no shear in the fibre mode
        self.assertEqual(rotem.fibre_tension, 0.0)
        self.assertAlmostEqual(rotem.matrix_tension, 1.0)
        mixed = hashin(np.array([0.6 * S.Xt, 0.0, 0.8 * S.S]), S)        # 0.36 + 0.64 = 1: fibre tension with shear
        self.assertAlmostEqual(mixed.fibre_tension, 1.0)
        self.assertEqual(mixed.mode, "Fibre tension")
        self.assertAlmostEqual(hashin(np.array([-0.6 * S.Xc, 0.0, 0.8 * S.S]), S).fibre_compression, 0.36)   # no shear in FC
        self.assertEqual(hashin(np.array([0.0, 0.0, -S.S]), S).matrix_tension, hashin(shear, S).matrix_tension)   # sign of tau is irrelevant

    def test_matrix_compression_formula_and_default_transverse_shear(self):
        st = hashin_transverse_shear_strength(S)
        self.assertAlmostEqual(st, S.Yc / (2 * math.tan(math.radians(53.0))), places=3)
        s2, tau = -150e6, 30e6
        expected = (s2 / (2 * st)) ** 2 + ((S.Yc / (2 * st)) ** 2 - 1) * s2 / S.Yc + (tau / S.S) ** 2
        self.assertAlmostEqual(hashin(np.array([0.0, s2, tau]), S).matrix_compression, expected, places=12)
        given = StrengthAllowables(1500e6, 1500e6, 40e6, 246e6, 68e6, St=90e6)
        self.assertEqual(hashin_transverse_shear_strength(given), 90e6)
        self.assertAlmostEqual(hashin(np.array([0.0, -given.Yc, 0.0]), given).matrix_compression, 1.0, places=12)
        with self.assertRaises(ValueError):
            StrengthAllowables(1.0, 1.0, 1.0, 1.0, 1.0, St=-1.0)

    def test_zero_stress_and_invalid_input(self):
        r = hashin(np.zeros(3), S)
        self.assertEqual((r.index, r.mode, r.load_factor), (0.0, "No load", math.inf))
        with self.assertRaises(ValueError):
            hashin(np.array([1.0, 2.0]), S)
        with self.assertRaises(ValueError):
            hashin(np.array([1.0, 2.0, 3.0]), S, shear_factor=1.5)


class HashinLoadFactorTests(unittest.TestCase):
    def test_load_factor_brings_the_active_index_to_one(self):
        rng = np.random.default_rng(7)                                    # fixed seed: deterministic
        for allow in (S, S_ASYM):
            for _ in range(300):
                sigma = rng.normal(size=3) * np.array([800e6, 60e6, 40e6])
                for alpha in (0.0, 1.0):
                    ratios = hashin_load_factors(sigma, allow, alpha)
                    result = hashin(sigma, allow, alpha)
                    self.assertAlmostEqual(result.load_factor, min(ratios.values()), places=9)
                    scaled = _hashin_indices(sigma * result.load_factor, allow, alpha)
                    self.assertAlmostEqual(max(scaled.values()), 1.0, places=9)
                    below = _hashin_indices(sigma * result.load_factor * 0.999, allow, alpha)
                    self.assertLess(max(below.values()), 1.0)

    def test_index_is_quadratic_so_strength_ratio_is_not_one_over_index(self):
        r = hashin(np.array([0.5 * S.Xt, 0.0, 0.0]), S)
        self.assertAlmostEqual(r.index, 0.25)
        self.assertAlmostEqual(r.load_factor, 2.0)


class HashinAgreesWithMaximumStressTests(unittest.TestCase):
    def test_pure_fibre_tension_and_compression_agree_with_max_stress(self):
        for allow in (S, S_ASYM):
            for fraction in (0.25, 0.5, 1.0, 1.3):
                for sign, xs, name in ((1, allow.Xt, "Fibre tension"), (-1, allow.Xc, "Fibre compression")):
                    sigma = np.array([sign * fraction * xs, 0.0, 0.0])
                    utilization, ms_mode = maximum_stress(sigma, allow)
                    h = hashin(sigma, allow)
                    self.assertEqual(ms_mode, name)
                    self.assertEqual(h.mode, name)
                    self.assertAlmostEqual(h.load_factor, 1.0 / utilization, places=12)       # same strength ratio
                    self.assertAlmostEqual(math.sqrt(h.index), utilization, places=12)         # index = utilisation^2

    def test_evaluate_failure_reports_hashin_next_to_max_stress_and_tsai_wu(self):
        result = evaluate_failure(np.array([S.Xt, 0.0, 0.0]), S)
        self.assertAlmostEqual(result.maximum_stress_utilization, 1.0)
        self.assertAlmostEqual(result.tsai_wu_index, 1.0)
        self.assertAlmostEqual(result.hashin_index, 1.0)
        self.assertEqual(result.hashin_mode, "Fibre tension")
        self.assertIn(result.hashin_mode, HASHIN_MODES)
        zero = evaluate_failure(np.zeros(3), S)
        self.assertEqual((zero.hashin_index, zero.hashin_mode), (0.0, "No load"))


if __name__ == "__main__":
    unittest.main()
