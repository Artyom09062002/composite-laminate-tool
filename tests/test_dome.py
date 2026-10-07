"""Geodesic dome winding (C2): Clairaut angle, thickness build-up, membrane resultants, first-ply pressure."""
import math
import unittest

import numpy as np

from core import StrengthAllowables, assemble_laminate_stiffness, recover_ply_surfaces
from core.dome import (bending_zone_length_m, clairaut_angle_deg, cylinder_winding_angle_deg, dome_resultants, dome_stations,
                       dome_wall, ellipsoid_dome_geometry, meridian_arc_length_m, thickness_factor)
from core.failure import first_ply_limit
from core.vessel import cylinder_resultants, first_ply_under_unit_load
from materials import DEFAULT_MATERIALS
from workflow import angle_ply_wall, screen_cylinder

RECORD = next(iter(DEFAULT_MATERIALS.values()))
GR = RECORD.as_core_material()
SGR = StrengthAllowables(**RECORD.as_strengths())

R, R0, PLY_T, PLIES = 0.1, 0.05, 0.125e-3, 8      # r0/R = 0.5 -> alpha0 = 30 deg
ALPHA0 = cylinder_winding_angle_deg(R0, R)
WALL = angle_ply_wall(ALPHA0, PLIES, PLY_T)


def stations(aspect_ratio=1.0, **kwargs):
    return dome_stations(WALL, [GR], [SGR], R0, R, aspect_ratio=aspect_ratio, **kwargs)


class GeodesicAngleTests(unittest.TestCase):
    def test_angle_is_90_degrees_at_the_polar_opening(self):
        self.assertEqual(clairaut_angle_deg(R0, R0), 90.0)

    def test_angle_at_the_cylinder_is_asin_r0_over_R(self):
        self.assertAlmostEqual(ALPHA0, math.degrees(math.asin(0.5)), places=12)
        self.assertAlmostEqual(ALPHA0, 30.0, places=10)
        self.assertEqual(stations().alpha_deg[0], ALPHA0)

    def test_clairaut_invariant_and_monotonic_angle_along_the_dome(self):
        s = stations()
        np.testing.assert_allclose(s.radius_m * np.sin(np.radians(s.alpha_deg)), R0, rtol=1e-12)
        self.assertTrue(np.all(np.diff(s.alpha_deg) > 0))
        self.assertLess(s.alpha_deg[-1], 90.0)

    def test_radius_inside_the_opening_is_rejected(self):
        with self.assertRaises(ValueError):
            clairaut_angle_deg(0.99 * R0, R0)
        with self.assertRaises(ValueError):
            thickness_factor(0.5 * R0, R0, R)
        with self.assertRaises(ValueError):
            thickness_factor(1.01 * R, R0, R)
        with self.assertRaises(ValueError):
            ellipsoid_dome_geometry(1.01 * R, R, 1.0)

    def test_invalid_opening_radius_is_rejected(self):
        for bad in (0.0, -0.01, R, 1.5 * R, math.nan):
            with self.assertRaises(ValueError):
                cylinder_winding_angle_deg(bad, R)

    def test_layup_must_match_the_geodesic_angle(self):
        with self.assertRaises(ValueError):
            dome_stations(angle_ply_wall(45.0, 8, PLY_T), [GR], [SGR], R0, R)


class ThicknessTests(unittest.TestCase):
    def test_thickness_grows_monotonically_toward_the_pole(self):
        s = stations()
        self.assertTrue(np.all(np.diff(s.thickness_m) > 0))

    def test_thickness_at_the_cylinder_is_the_cylinder_wall(self):
        s = stations()
        self.assertEqual(s.thickness_ratio[0], 1.0)
        self.assertAlmostEqual(s.thickness_m[0], PLIES * PLY_T, places=15)

    def test_thickness_matches_closed_form_and_constant_band_volume(self):
        s = stations()
        np.testing.assert_allclose(s.thickness_ratio, np.sqrt((R**2 - R0**2) / (s.radius_m**2 - R0**2)), rtol=1e-12)
        cos_a = np.cos(np.radians(s.alpha_deg))
        # t r cos(alpha) is the fibre band volume per unit meridian length: constant along the dome.
        np.testing.assert_allclose(s.thickness_m * s.radius_m * cos_a, PLIES * PLY_T * R * math.cos(math.radians(ALPHA0)), rtol=1e-12)

    def test_thickness_is_singular_at_the_opening(self):
        self.assertTrue(math.isinf(thickness_factor(R0, R0, R)))


class MembraneTests(unittest.TestCase):
    def test_hemisphere_has_equal_resultants_pR_over_2(self):
        p = 2e6
        s = stations(1.0, pressure_pa=p)
        np.testing.assert_allclose(s.n_phi, p * R / 2, rtol=1e-12)
        np.testing.assert_allclose(s.n_theta, p * R / 2, rtol=1e-12)

    def test_cylinder_limit_of_the_dome_resultants(self):
        np.testing.assert_allclose(dome_resultants(2e6, math.inf, R), cylinder_resultants(2e6, R))

    def test_ellipsoid_radii_match_the_curvature_of_z_of_r(self):
        for k in (0.5, 0.8, 1.3):
            b = k * R
            for rho in (0.3, 0.6, 0.9):
                r = rho * R
                dz = -(b / R) * rho / math.sqrt(1 - rho**2)               # dz/dr of z = b sqrt(1 - (r/R)^2)
                d2z = -(b / R**2) / (1 - rho**2) ** 1.5
                r1 = (1 + dz**2) ** 1.5 / abs(d2z)                          # meridional curvature radius
                r2 = r * math.sqrt(1 + dz**2) / (-dz)                       # normal length to the axis
                _, r1_code, r2_code = ellipsoid_dome_geometry(r, R, k)
                self.assertAlmostEqual(r1_code / r1, 1.0, places=12)
                self.assertAlmostEqual(r2_code / r2, 1.0, places=12)

    def test_ellipsoid_equator_and_pole_closed_forms(self):
        p, k = 1e6, 0.5                                                    # 2:1 head, b = R/2
        b = k * R
        _, r1, r2 = ellipsoid_dome_geometry(R, R, k)
        self.assertAlmostEqual(r1, b**2 / R, places=15)
        self.assertAlmostEqual(r2, R, places=15)
        n_phi, n_theta = dome_resultants(p, r1, r2)[:2]
        self.assertAlmostEqual(n_theta / (p * R * (1 - R**2 / (2 * b**2))), 1.0, places=12)
        self.assertAlmostEqual(n_theta / (-p * R), 1.0, places=12)         # hoop compression at the equator of a 2:1 head
        _, r1_pole, r2_pole = ellipsoid_dome_geometry(1e-9 * R, R, k)
        self.assertAlmostEqual(r1_pole / (R**2 / b), 1.0, places=9)
        self.assertAlmostEqual(r2_pole / (R**2 / b), 1.0, places=9)


class CylinderConsistencyTests(unittest.TestCase):
    def test_dome_start_recovers_cylinder_angle_thickness_and_axial_resultant(self):
        p = 3e6
        s = stations(0.5, pressure_pa=p)
        self.assertEqual(s.radius_m[0], R)
        self.assertEqual(s.alpha_deg[0], ALPHA0)
        self.assertAlmostEqual(s.thickness_m[0], sum(ply["t"] for ply in WALL), places=15)
        self.assertAlmostEqual(s.n_phi[0] / cylinder_resultants(p, R)[0], 1.0, places=12)   # N_phi = N_x = pR/2

    def test_hoop_resultant_jumps_at_the_junction_unless_the_meridian_is_straight(self):
        s = stations(1.0, pressure_pa=1.0)
        self.assertAlmostEqual(s.n_theta[0] / cylinder_resultants(1.0, R)[1], 0.5, places=12)   # pR/2 against pR

    def test_cylinder_limit_reproduces_screen_cylinder_first_ply_pressure(self):
        # Same wall, same code path, straight meridian (r1 -> infinity): the cylinder first-ply pressure.
        direct = first_ply_under_unit_load(WALL, [GR], [SGR], dome_resultants(1.0, math.inf, R))
        reference = screen_cylinder(WALL, [GR], [SGR], R)
        self.assertEqual(direct.pressure_pa, reference.first_ply_pressure_pa)
        self.assertEqual((direct.ply, direct.surface, direct.criterion, direct.mode),
                         (reference.first_ply_ply, reference.first_ply_surface, reference.first_ply_criterion,
                          reference.first_ply_mode))

    def test_station_first_ply_pressure_brings_the_governing_criterion_to_one(self):
        s = stations(0.7)
        for i in (0, 10, 25, len(s.radius_m) - 1):
            wall = dome_wall(WALL, s.alpha_deg[i], s.thickness_ratio[i])
            loads = dome_resultants(s.first_ply_pressure_pa[i], s.r1_m[i], s.r2_m[i])
            response = recover_ply_surfaces(assemble_laminate_stiffness(wall, [GR]), wall, [GR], loads)
            _, factor, _ = first_ply_limit(response.ply_surfaces, SGR)
            self.assertAlmostEqual(factor, 1.0, places=6)

    def test_first_ply_pressure_is_finite_and_positive_along_the_dome(self):
        for k in (0.5, 1.0):
            p = stations(k).first_ply_pressure_pa
            self.assertTrue(np.all(np.isfinite(p)) and np.all(p > 0))


class ValidityZoneTests(unittest.TestCase):
    """Review C3 items 3, 7, 10: junction and turnaround stations are not strength predictions."""

    def test_bending_zone_length_closed_form(self):
        r, h, nu = 0.1, 2e-3, 0.3
        beta = (3 * (1 - nu**2)) ** 0.25 / math.sqrt(r * h)
        self.assertAlmostEqual(bending_zone_length_m(r, h, nu), math.pi / beta, places=15)
        self.assertGreater(bending_zone_length_m(r, 4 * h), bending_zone_length_m(r, h))   # grows as sqrt(R h)
        for bad in ((0.0, h, nu), (r, -h, nu), (r, h, 1.0)):
            with self.assertRaises(ValueError):
                bending_zone_length_m(*bad)

    def test_arc_length_hemisphere_and_ellipsoid(self):
        radii = np.array([R, 0.8 * R, 0.5 * R])
        np.testing.assert_allclose(meridian_arc_length_m(radii, R, 1.0), R * np.arccos(radii / R), rtol=1e-7)
        k, b = 0.5, 0.5 * R
        t = np.linspace(0.0, math.acos(0.5), 400001)
        speed = np.sqrt(R**2 * np.sin(t) ** 2 + b**2 * np.cos(t) ** 2)
        reference = float(np.sum(0.5 * (speed[1:] + speed[:-1]) * np.diff(t)))             # independent dense quadrature
        self.assertAlmostEqual(float(meridian_arc_length_m(0.5 * R, R, k)[0]) / reference, 1.0, places=7)
        self.assertEqual(float(meridian_arc_length_m(R, R, k)[0]), 0.0)

    def test_junction_and_opening_stations_are_flagged_and_the_middle_is_valid(self):
        for k in (0.5, 1.0):
            s = stations(k)
            self.assertFalse(s.membrane_valid[0])
            self.assertFalse(s.membrane_valid[-1])
            valid = s.arc_m[s.membrane_valid]
            total = float(meridian_arc_length_m(R0, R, k)[0])
            self.assertTrue(np.all(valid >= s.bending_zone_m) and np.all(total - valid >= s.bending_zone_m))

    def test_headline_weakest_station_is_never_a_flagged_one(self):
        # Hemisphere and 2:1 head: the global minimum sits at the junction (membrane jump), which must not be quoted.
        for k in (0.5, 1.0):
            s = stations(k)
            self.assertEqual(int(np.argmin(s.first_ply_pressure_pa)), 0)
            index = s.weakest_valid_index()
            self.assertTrue(s.membrane_valid[index])
            self.assertGreater(s.first_ply_pressure_pa[index], s.first_ply_pressure_pa[0])
        # k = 0.7: the global minimum lies in the turnaround zone near the opening.
        s = stations(0.7)
        self.assertFalse(s.membrane_valid[int(np.argmin(s.first_ply_pressure_pa))])
        self.assertTrue(s.membrane_valid[s.weakest_valid_index()])

    def test_no_valid_station_when_the_wall_is_too_thick_for_membrane_theory(self):
        thick = dome_stations(angle_ply_wall(ALPHA0, 200, PLY_T), [GR], [SGR], R0, R)
        self.assertFalse(thick.membrane_valid.any())
        self.assertIsNone(thick.weakest_valid_index())

    def test_membrane_values_themselves_are_unchanged(self):
        s = stations(1.0)
        np.testing.assert_allclose(s.n_phi, 0.5 * R, rtol=1e-12)   # flagging does not alter the equations


if __name__ == "__main__":
    unittest.main()
