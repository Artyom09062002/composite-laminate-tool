"""Mechanical equilibrium and the printed Kaw section 4.3 example."""
import unittest
import numpy as np
from core.laminate import assemble_laminate_stiffness
from core.response import ply_force_resultants, solve_laminate_response, recover_ply_surfaces


KAW_MATERIAL = [{"E1": 38.6e9, "E2": 8.27e9, "G12": 4.14e9, "v12": 0.26}]
KAW_LAYUP = [{"theta": angle, "t": 0.005, "mat": 0} for angle in (30, -45, -60)]
KAW_LOADS = np.array([1500., 0., 0., 0., 1500., 0.])


class PlyForceTests(unittest.TestCase):
    def test_equilibrium_membrane_moment_and_combined(self):
        materials = KAW_MATERIAL + [{"E1": 181e9, "E2": 10.3e9, "G12": 7.17e9, "v12": .28}]
        for angles in ((0,), (0, 45, -45, 90, 90, -45, 45, 0), (30, -45, -60), (15, 90, -30, 0)):
            layup = [{"theta": a, "t": (i + 1) * .000125, "mat": i % 2} for i, a in enumerate(angles)]
            stiffness = assemble_laminate_stiffness(layup, materials)
            for loads in ([1500, -3000, 700, 0, 0, 0], [0, 0, 0, 10, -15, 4], [1500, -3000, 700, 10, -15, 4]):
                with self.subTest(angles=angles, loads=loads):
                    forces = ply_force_resultants(stiffness, layup, materials, loads)
                    # Floating-point cancellation under pure bending: bound by
                    # the sum of absolute integrated forces, not a relative zero.
                    atol = 100 * np.finfo(float).eps * np.abs(forces).sum()
                    np.testing.assert_allclose(forces.sum(axis=0), loads[:3], rtol=1e-12, atol=atol)

    def test_midpoint_integral_is_exact_for_linear_stress(self):
        stiffness = assemble_laminate_stiffness(KAW_LAYUP, KAW_MATERIAL)
        response = solve_laminate_response(stiffness, KAW_LOADS)
        midpoint = np.array([q @ (response.midplane_strain + (a+b)/2 * response.curvature) * (b-a)
                             for q, a, b in zip(stiffness.qbars, stiffness.z[:-1], stiffness.z[1:])])
        np.testing.assert_allclose(ply_force_resultants(stiffness, KAW_LAYUP, KAW_MATERIAL, KAW_LOADS), midpoint,
                                   rtol=1e-14, atol=1e-10)

    def test_kaw_printed_ply_loads(self):
        stiffness = assemble_laminate_stiffness(KAW_LAYUP, KAW_MATERIAL)
        actual = ply_force_resultants(stiffness, KAW_LAYUP, KAW_MATERIAL, KAW_LOADS)[:, 0]
        # PDF p.9: loads obtained from p.7 midpoint stresses, each printed
        # to 0.001 MPa. Half a printed unit times 0.005 m = 2.5 N/m.
        np.testing.assert_allclose(actual, [12920, -20595, 9175], rtol=0, atol=0.0005e6 * .005)

    def test_kaw_printed_abd(self):
        s = assemble_laminate_stiffness(KAW_LAYUP, KAW_MATERIAL)
        # PDF p.4. Each entry has its own half-unit-of-last-printed-digit tolerance.
        for actual, reference, tolerance in (
            (s.A, [[2.735e8,1.160e8,-9.636e6],[1.160e8,2.735e8,-6.730e7],[-9.636e6,-6.730e7,1.453e8]],
             [[5e4,5e4,5e2],[5e4,5e4,5e3],[5e2,5e3,5e4]]),
            (s.B, [[-3.847e5,0,-3.332e5],[0,3.847e5,-3.332e5],[-3.332e5,-3.332e5,0]],
             [[50,1e-9,50],[1e-9,50,50],[50,50,1e-9]]),
            (s.D, [[5.266e3,2.036e3,7.008e2],[2.036e3,5.266e3,-8.611e2],[7.008e2,-8.611e2,2.586e3]],
             [[.5,.5,.05],[.5,.5,.05],[.05,.05,.5]])):
            self.assertTrue(np.all(np.abs(actual - reference) <= tolerance))

    def test_invalid_loads_and_mismatched_layup(self):
        s = assemble_laminate_stiffness(KAW_LAYUP, KAW_MATERIAL)
        for loads in ([0]*5, [float("nan")]*6):
            with self.assertRaises(ValueError):
                ply_force_resultants(s, KAW_LAYUP, KAW_MATERIAL, loads)
        with self.assertRaises(ValueError):
            ply_force_resultants(s, KAW_LAYUP[:2], KAW_MATERIAL, KAW_LOADS)

    def test_kaw_point_strain_and_stress_by_coordinate(self):
        s = assemble_laminate_stiffness(KAW_LAYUP, KAW_MATERIAL)
        p = recover_ply_surfaces(s, KAW_LAYUP, KAW_MATERIAL, KAW_LOADS).ply_surfaces[2]
        self.assertEqual(p.surface, "Bottom")  # source Top, p.5, same z
        self.assertAlmostEqual(p.z, -.0025, places=15)
        for actual, reference, tolerance in (
            (p.global_strain,[5.131e-4,-1.406e-3,1.068e-4],[5e-8,5e-7,5e-8]),
            (s.qbars[1] @ p.global_strain,[-4.466e6,-2.035e7,8.022e6],[500,5000,500]),
            (p.local_strain,[-4.998e-4,-3.930e-4,1.919e-3],[5e-8,5e-8,5e-7]),
            (p.local_stress,[-2.043e7,-4.388e6,7.944e6],[5000,500,500])):
            # PDF pp.5–8, half the last printed decimal unit per component.
            self.assertTrue(np.all(np.abs(actual-reference) <= tolerance))


if __name__ == "__main__":
    unittest.main()
