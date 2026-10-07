"""C5 thermal CLT acceptance checks.

The compact synthetic material values below are algebraic test fixtures, not
material data or reported engineering results.
"""

import json
import importlib.util
import math
import pathlib
import unittest

import numpy as np

from core import (
    StrengthAllowables,
    assemble_laminate_stiffness,
    compute_thermal_resultants,
    first_ply_mechanical_load_factor,
    recover_ply_surfaces,
    recover_thermal_response,
    temperature_change_from_reference,
    transform_cte,
)
from core.transformations import transform_stress_strain
from core.failure import evaluate_failure
from materials import DEFAULT_MATERIALS
from workflow import parse_layup


# Synthetic constants selected only to exercise the equations and signs.
MATERIAL = {
    "E1": 100e9,
    "E2": 10e9,
    "G12": 5e9,
    "v12": 0.25,
    "alpha1": 1e-6,
    "alpha2": 25e-6,
    "alpha12": 0.0,
}
PLY_T = 0.125e-3


class ThermalMechanicsTests(unittest.TestCase):
    def response(self, angles, delta_temperature=-100.0, loads=None):
        layup = [{"theta": float(angle), "t": PLY_T, "mat": 0} for angle in angles]
        stiffness = assemble_laminate_stiffness(layup, [MATERIAL])
        return layup, stiffness, recover_thermal_response(stiffness, layup, [MATERIAL], delta_temperature, loads)

    def test_unidirectional_ply_recovers_alpha1_and_alpha2(self):
        layup, stiffness, response = self.response([0.0], delta_temperature=1.0)
        np.testing.assert_allclose(response.midplane_strain, [MATERIAL["alpha1"], MATERIAL["alpha2"], 0.0], rtol=1e-12, atol=1e-15)
        np.testing.assert_allclose(response.curvature, 0.0, atol=1e-12)
        for point in response.ply_surfaces:
            np.testing.assert_allclose(point.local_strain, [MATERIAL["alpha1"], MATERIAL["alpha2"], 0.0], rtol=1e-12, atol=1e-15)
            np.testing.assert_allclose(point.local_stress, 0.0, atol=1e-6)
        np.testing.assert_allclose(transform_cte(MATERIAL["alpha1"], MATERIAL["alpha2"], 90.0)[:2],
                                   [MATERIAL["alpha2"], MATERIAL["alpha1"]], rtol=1e-12, atol=1e-15)

    def test_symmetric_laminate_has_zero_thermal_curvature(self):
        _, _, response = self.response([0, 45, -45, 90, 90, -45, 45, 0])
        np.testing.assert_allclose(response.curvature, 0.0, atol=1e-10)

    def test_quasi_isotropic_laminate_expands_equally_in_x_and_y(self):
        _, _, response = self.response([0, 45, -45, 90, 90, -45, 45, 0], delta_temperature=40.0)
        self.assertAlmostEqual(response.midplane_strain[0], response.midplane_strain[1], places=14)
        self.assertAlmostEqual(response.midplane_strain[2], 0.0, places=14)

    def test_cross_ply_cooling_gives_transverse_tension_in_zero_plies_and_zero_net_force(self):
        layup, stiffness, response = self.response([0, 90, 90, 0], delta_temperature=-100.0)
        zero_ply_sigma2 = [point.local_stress[1] for point in response.ply_surfaces if point.angle_deg == 0.0]
        self.assertTrue(all(value > 0.0 for value in zero_ply_sigma2))

        net_force = np.zeros(3)
        for ply_index, ply in enumerate(layup):
            bottom, top = response.ply_surfaces[2 * ply_index:2 * ply_index + 2]
            local_average = 0.5 * (bottom.local_stress + top.local_stress)
            global_average = transform_stress_strain(local_average, -ply["theta"], "stress")
            net_force += global_average * ply["t"]
        np.testing.assert_allclose(net_force, 0.0, atol=1e-8)

        thermal = compute_thermal_resultants(stiffness, layup, [MATERIAL], -100.0)
        np.testing.assert_allclose(stiffness.ABD @ np.concatenate((response.midplane_strain, response.curvature)),
                                   thermal.vector, rtol=1e-12, atol=1e-8)

    def test_mechanical_and_thermal_responses_superpose_and_factor_holds_thermal_preload_fixed(self):
        layup = parse_layup("[0,90]s", PLY_T)
        stiffness = assemble_laminate_stiffness(layup, [MATERIAL])
        loads = np.array([50e3, 0.0, 0.0, 0.0, 0.0, 0.0])
        thermal = recover_thermal_response(stiffness, layup, [MATERIAL], -100.0)
        mechanical = recover_ply_surfaces(stiffness, layup, [MATERIAL], loads)
        combined = recover_thermal_response(stiffness, layup, [MATERIAL], -100.0, loads)
        for t_point, m_point, c_point in zip(thermal.ply_surfaces, mechanical.ply_surfaces, combined.ply_surfaces):
            np.testing.assert_allclose(c_point.local_stress, t_point.local_stress + m_point.local_stress, rtol=1e-12, atol=1e-6)

        strengths = StrengthAllowables(800e6, 600e6, 35e6, 120e6, 50e6)
        _, factor, _ = first_ply_mechanical_load_factor(thermal, mechanical, strengths)
        self.assertTrue(math.isfinite(factor))
        self.assertGreaterEqual(factor, 0.0)
        at_limit = recover_thermal_response(stiffness, layup, [MATERIAL], -100.0, factor * loads)
        governing = max(max(evaluate_failure(point.local_stress, strengths).maximum_stress_utilization,
                            evaluate_failure(point.local_stress, strengths).tsai_wu_index)
                        for point in at_limit.ply_surfaces)
        self.assertAlmostEqual(governing, 1.0, places=10)
        tiny_mechanical = recover_ply_surfaces(stiffness, layup, [MATERIAL], loads * 1e-10)
        _, tiny_factor, _ = first_ply_mechanical_load_factor(thermal, tiny_mechanical, strengths)
        self.assertAlmostEqual(tiny_factor * 1e-10 / factor, 1.0, places=10)

    def test_cryogenic_delta_is_final_minus_reference(self):
        self.assertAlmostEqual(temperature_change_from_reference(121.11111111111111, -196.0), -317.1111111111111)

    def test_cte_matches_independent_tensor_rotation_including_engineering_shear(self):
        alpha = np.array([1e-6, 25e-6, 3e-6])
        tensor_local = np.array([[alpha[0], alpha[2] / 2], [alpha[2] / 2, alpha[1]]])
        for angle in (-73., -45., 0., 31., 45., 90.):
            c, s = np.cos(np.deg2rad(angle)), np.sin(np.deg2rad(angle))
            rotation = np.array([[c, -s], [s, c]])
            tensor = rotation @ tensor_local @ rotation.T
            expected = [tensor[0, 0], tensor[1, 1], 2 * tensor[0, 1]]
            np.testing.assert_allclose(transform_cte(*alpha[:2], angle, alpha[2]), expected, atol=1e-20)
            local_material = {**MATERIAL, "alpha12": alpha[2]}
            layup = [{"theta": angle, "t": PLY_T, "mat": 0}]
            stiffness = assemble_laminate_stiffness(layup, [local_material])
            response = recover_thermal_response(stiffness, layup, [local_material], -100.)
            for point in response.ply_surfaces:
                np.testing.assert_allclose(point.local_stress, 0., atol=1e-6)

    def test_unsymmetric_hybrid_recovers_external_force_and_moment_equilibrium(self):
        materials = [MATERIAL, {**MATERIAL, "E1": 38.6e9, "alpha1": 8.6e-6, "alpha2": 22.1e-6}]
        layup = [{"theta": 31., "t": .00013, "mat": 0},
                 {"theta": -62., "t": .00020, "mat": 1},
                 {"theta": 4., "t": .00017, "mat": 0}]
        stiffness = assemble_laminate_stiffness(layup, materials)
        for loads in (None, np.array([17000., -6000., 2300., .7, -.4, .2])):
            response = recover_thermal_response(stiffness, layup, materials, [-100., -130.], loads)
            force, moment = np.zeros(3), np.zeros(3)
            for index, ply in enumerate(layup):
                a, b = stiffness.z[index:index + 2]
                bottom, top = response.ply_surfaces[2 * index:2 * index + 2]
                sb = transform_stress_strain(bottom.local_stress, -ply["theta"], "stress")
                st = transform_stress_strain(top.local_stress, -ply["theta"], "stress")
                slope = (st - sb) / (b - a)
                intercept = sb - slope * a
                force += intercept * (b - a) + slope * (b**2 - a**2) / 2
                moment += intercept * (b**2 - a**2) / 2 + slope * (b**3 - a**3) / 3
            np.testing.assert_allclose(np.r_[force, moment], np.zeros(6) if loads is None else loads,
                                       rtol=1e-12, atol=2e-8)

    def test_stack_reversal_changes_thermal_curvature_sign(self):
        layup, stiffness, response = self.response([0., 31., -62.])
        reverse = list(reversed(layup))
        reverse_stiffness = assemble_laminate_stiffness(reverse, [MATERIAL])
        reversed_response = recover_thermal_response(reverse_stiffness, reverse, [MATERIAL], -100.)
        self.assertGreater(np.linalg.norm(response.curvature), 1.)
        np.testing.assert_allclose(reversed_response.midplane_strain, response.midplane_strain, atol=1e-16)
        np.testing.assert_allclose(reversed_response.curvature, -response.curvature, atol=1e-12)


class ThermalSourceTests(unittest.TestCase):
    def test_built_in_thermal_values_are_sourced_in_validation_data(self):
        path = pathlib.Path(__file__).resolve().parents[1] / "validation" / "data.json"
        data = json.loads(path.read_text(encoding="utf-8"))["thermal_materials"]
        self.assertEqual(data["T300_5208"]["status"], "SOURCED")
        self.assertEqual(data["SCOTCHPLY_1002"]["status"], "SOURCED")
        graphite, glass = DEFAULT_MATERIALS.values()
        self.assertAlmostEqual(graphite.alpha1 * 1e6, data["T300_5208"]["alpha1"]["value"])
        self.assertAlmostEqual(graphite.alpha2 * 1e6, data["T300_5208"]["alpha2"]["value"])
        self.assertAlmostEqual(glass.alpha1 * 1e6, data["SCOTCHPLY_1002"]["alpha1"]["value"])
        self.assertAlmostEqual(glass.alpha2 * 1e6, data["SCOTCHPLY_1002"]["alpha2"]["value"])
        self.assertIn("approximation", graphite.thermal_reference_basis)
        self.assertNotIn("Measured stress-free", graphite.thermal_reference_basis)
        self.assertIn("assumed", data["SCOTCHPLY_1002"]["reference_temperature"]["note"])


@unittest.skipUnless(importlib.util.find_spec("streamlit"), "streamlit is not installed")
class ThermalFailureTabTests(unittest.TestCase):
    def test_failure_tab_exposes_sourced_thermal_case_and_cryogenic_delta(self):
        from streamlit.testing.v1 import AppTest

        app = pathlib.Path(__file__).resolve().parents[1] / "app.py"
        at = AppTest.from_file(str(app), default_timeout=120).run()
        self.assertEqual([error.value for error in at.exception], [])
        metrics = {metric.label: metric.value for metric in at.metric}
        self.assertIn("Active ΔT [°C]", metrics)
        self.assertIn("Max residual |σ₂| [MPa]", metrics)
        self.assertIn("First-ply factor with thermal preload", metrics)
        self.assertIsNotNone(at.number_input(key="thermal_delta_t"))
        self.assertIsNotNone(at.number_input(key="thermal_final_temperature"))
        self.assertTrue(any("Moisture, creep, and temperature-dependent properties are not modelled" in item.value
                            for item in at.caption))
        self.assertTrue(any("Residual σ₂ [MPa]" in frame.value.columns for frame in at.dataframe))

        at.selectbox(key="thermal_case").set_value("Cool from reference to final temperature").run()
        self.assertEqual([error.value for error in at.exception], [])
        metrics = {metric.label: metric.value for metric in at.metric}
        self.assertAlmostEqual(float(metrics["Active ΔT [°C]"]), -317.1, places=1)

    def test_reference_cooling_uses_the_explicit_common_stress_free_temperature(self):
        from streamlit.testing.v1 import AppTest
        app = pathlib.Path(__file__).resolve().parents[1] / "app.py"
        at = AppTest.from_file(str(app), default_timeout=120).run()
        at.selectbox(key="thermal_case").set_value("Cool from reference to final temperature")
        at.number_input(key="thermal_common_reference").set_value(200.)
        at.number_input(key="thermal_final_temperature").set_value(20.).run()
        self.assertEqual([error.value for error in at.exception], [])
        metrics = {metric.label: metric.value for metric in at.metric}
        self.assertEqual(float(metrics["Active ΔT [°C]"]), -180.)
        self.assertTrue(any("user-assumed common" in item.value for item in at.caption))


if __name__ == "__main__":
    unittest.main()
