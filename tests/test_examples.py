import unittest

from examples.spar_cap import analyze_spar_cap


class SparCapExampleTests(unittest.TestCase):
    def test_unsymmetric_panel_has_coupling_and_shifted_neutral_surface(self):
        layup, stiffness = analyze_spar_cap()
        self.assertEqual(len(layup), 2)
        offset = stiffness.B[0, 0] / stiffness.A[0, 0]
        # The softer triax skin is at the bottom, so the x-direction neutral axis moves up (+z).
        self.assertGreater(offset, 0.0)
        self.assertLess(offset, 0.05 * (stiffness.z[-1] - stiffness.z[0]))


if __name__ == "__main__":
    unittest.main()
