"""Wiring of the Pressure vessel tab (C3): first-ply vs last-ply comparison with the netting estimate kept visible.

Runs the Streamlit app headlessly with streamlit.testing; skipped when streamlit is not installed.
"""
import importlib.util
import pathlib
import unittest

APP = pathlib.Path(__file__).resolve().parents[1] / "app.py"


@unittest.skipUnless(importlib.util.find_spec("streamlit"), "streamlit is not installed")
class PressureVesselTabTests(unittest.TestCase):
    @staticmethod
    def metrics(at):
        return {m.label: m.value for m in at.metric}

    @classmethod
    def setUpClass(cls):
        from streamlit.testing.v1 import AppTest
        cls.AppTest = AppTest

    def run_app(self):
        at = self.AppTest.from_file(str(APP), default_timeout=120)
        at.run()
        self.assertEqual([e.value for e in at.exception], [])
        return at

    def test_first_ply_last_ply_and_netting_are_all_shown(self):
        metrics = self.metrics(self.run_app())
        for label in ("First-ply failure pressure [MPa]", "First-ply, Hashin [MPa]", "Last-ply (model stop) [MPa]",
                      "Last-ply / first-ply", "Netting burst estimate [MPa]"):
            self.assertIn(label, metrics)
        self.assertGreaterEqual(float(metrics["Last-ply (model stop) [MPa]"]), float(metrics["First-ply, Hashin [MPa]"]))
        self.assertGreater(float(metrics["Netting burst estimate [MPa]"]), 0.0)

    def test_degradation_factors_are_editable_and_change_the_last_ply_value(self):
        at = self.run_app()
        base = float(self.metrics(at)["Last-ply (model stop) [MPa]"])
        at.number_input(key="deg_e2").set_value(0.3).run()
        at.number_input(key="deg_g12").set_value(0.3).run()
        self.assertEqual([e.value for e in at.exception], [])
        changed = float(self.metrics(at)["Last-ply (model stop) [MPa]"])
        self.assertNotEqual(base, changed)
        self.assertEqual(self.metrics(at)["First-ply, Hashin [MPa]"], self.metrics(self.run_app())["First-ply, Hashin [MPa]"])

    def test_dome_headline_skips_flagged_stations_and_handles_no_valid_station(self):
        at = self.run_app()
        self.assertIn("Weakest valid dome station, first-ply [MPa]", self.metrics(at))
        at.number_input(key="dome_r0_ratio").set_value(0.9).run()
        self.assertEqual([e.value for e in at.exception], [])
        self.assertEqual(self.metrics(at)["Weakest valid dome station, first-ply [MPa]"], "n/a")


if __name__ == "__main__":
    unittest.main()
