"""Laminate engineering constants, pressure-vessel screening and the PDF report."""
import math
import unittest

import numpy as np

from core import StrengthAllowables, assemble_laminate_stiffness, engineering_constants, recover_ply_surfaces
from core.vessel import NETTING_ANGLE_DEG, cylinder_resultants, netting_bound, netting_pressure
from materials import DEFAULT_MATERIALS
from workflow import angle_ply_wall, first_ply_limit, parse_layup, screen_cylinder

RECORD = next(iter(DEFAULT_MATERIALS.values()))
GR = RECORD.as_core_material()
SGR = StrengthAllowables(**RECORD.as_strengths())


class EngineeringConstantTests(unittest.TestCase):
    def test_unidirectional_laminate_recovers_ply_constants(self):
        stiffness = assemble_laminate_stiffness(parse_layup("[0,0]s", 0.125e-3), [GR])
        c = engineering_constants(stiffness)
        self.assertAlmostEqual(c.Ex / GR["E1"], 1.0, places=10)
        self.assertAlmostEqual(c.Ey / GR["E2"], 1.0, places=10)
        self.assertAlmostEqual(c.Gxy / GR["G12"], 1.0, places=10)
        self.assertAlmostEqual(c.nu_xy, GR["v12"], places=10)
        self.assertAlmostEqual(c.Ex_flex / GR["E1"], 1.0, places=10)

    def test_quasi_isotropic_membrane_constants_are_isotropic(self):
        stiffness = assemble_laminate_stiffness(parse_layup("[0,45,-45,90]s", 0.125e-3), [GR])
        c = engineering_constants(stiffness)
        self.assertAlmostEqual(c.Ex / c.Ey, 1.0, places=10)
        self.assertAlmostEqual(c.Gxy / (c.Ex / (2 * (1 + c.nu_xy))), 1.0, places=10)
        # Flexural stiffness is not isotropic: the outer 0 deg plies dominate D11.
        self.assertGreater(c.Ex_flex / c.Ey_flex, 3.0)

    def test_symmetric_membrane_constants_match_a_inverse(self):
        stiffness = assemble_laminate_stiffness(parse_layup("[0,30,-60]s", 0.125e-3), [GR])
        a = np.linalg.inv(stiffness.A)
        h = stiffness.z[-1] - stiffness.z[0]
        self.assertAlmostEqual(engineering_constants(stiffness).Ex * h * a[0, 0], 1.0, places=9)


class PressureVesselTests(unittest.TestCase):
    def test_resultants_and_netting_angle(self):
        np.testing.assert_allclose(cylinder_resultants(2e6, 0.1), [1e5, 2e5, 0, 0, 0, 0])
        self.assertAlmostEqual(math.tan(math.radians(NETTING_ANGLE_DEG)) ** 2, 2.0, places=12)

    def test_netting_pressure_closed_forms(self):
        wall = angle_ply_wall(NETTING_ANGLE_DEG, 16, 0.125e-3)
        h, radius = 16 * 0.125e-3, 0.1
        x = [SGR.Xt] * len(wall)
        self.assertAlmostEqual(netting_pressure(wall, x, radius) / (2 * SGR.Xt * h / (3 * radius)), 1.0, places=9)
        # Hoop plus helical net, solved exactly: pR = 2.4 X t for [90,30,-30]s (t = one ply).
        net = parse_layup("[90,30,-30]s", 0.125e-3)
        self.assertAlmostEqual(netting_pressure(net, [SGR.Xt] * 6, radius) / (2.4 * SGR.Xt * 0.125e-3 / radius), 1.0, places=9)
        self.assertGreater(netting_bound(net, [SGR.Xt] * 6, radius), netting_pressure(net, [SGR.Xt] * 6, radius))
        # A single +/-45 wind cannot balance Ny = 2 Nx with fibres alone.
        self.assertEqual(netting_pressure(angle_ply_wall(45.0, 8, 0.125e-3), [SGR.Xt] * 8, radius), 0.0)
        # Pure hoop winding carries no axial load in netting theory.
        hoop = [{"theta": 90.0, "t": 0.125e-3, "mat": 0}] * 4
        self.assertAlmostEqual(netting_pressure(hoop, [SGR.Xt] * 4, radius), 0.0, places=6)

    def test_first_ply_pressure_is_linear_load_factor(self):
        wall = angle_ply_wall(55.0, 8, 0.125e-3)
        result = screen_cylinder(wall, [GR], [SGR], 0.1)
        stiffness = assemble_laminate_stiffness(wall, [GR])
        loads = cylinder_resultants(result.first_ply_pressure_pa, 0.1)
        response = recover_ply_surfaces(stiffness, wall, [GR], loads)
        _, factor, _ = first_ply_limit(response.ply_surfaces, SGR)
        self.assertAlmostEqual(factor, 1.0, places=6)

    def test_first_ply_pressure_peaks_near_netting_angle_for_graphite(self):
        pressures = {theta: screen_cylinder(angle_ply_wall(theta, 16, 0.125e-3), [GR], [SGR], 0.1).first_ply_pressure_pa
                     for theta in range(30, 81)}
        best = max(pressures, key=pressures.get)
        self.assertLessEqual(abs(best - NETTING_ANGLE_DEG), 2.0)

    def test_wall_requires_multiple_of_four_plies(self):
        with self.assertRaises(ValueError):
            angle_ply_wall(55.0, 6, 0.125e-3)


class ReportTests(unittest.TestCase):
    def test_pdf_report_is_generated(self):
        try:
            from report import build_pdf_report
        except ImportError:
            self.skipTest("reportlab is not installed")
        layup = parse_layup("[0,90]", 0.125e-3)
        stiffness = assemble_laminate_stiffness(layup, [GR])
        loads = np.array([1e5, 0, 0, 0, 0, 0], dtype=float)
        response = recover_ply_surfaces(stiffness, layup, [GR], loads)
        strengths = [SGR] * len(response.ply_surfaces)
        pdf = build_pdf_report(material_name=RECORD.name, material=GR, strengths=SGR, layup=layup,
                               material_names=["Sidebar material"], loads=loads, stiffness=stiffness,
                               constants=engineering_constants(stiffness), response=response,
                               surface_strengths=strengths, first_ply=first_ply_limit(response.ply_surfaces, strengths))
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 5000)


if __name__ == "__main__":
    unittest.main()
