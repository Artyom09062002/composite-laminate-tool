"""Compact, button-run Pressure vessel optimiser and stale-result protection."""
import importlib.util
import pathlib
import unittest

APP = pathlib.Path(__file__).resolve().parents[1] / "app.py"


@unittest.skipUnless(importlib.util.find_spec("streamlit"), "streamlit is not installed")
class OptimiserAppTests(unittest.TestCase):
    def run_app(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(APP), default_timeout=120).run()
        self.assertEqual([e.value for e in at.exception], [])
        return at

    def table(self, at):
        return next(frame.value for frame in at.dataframe if "Last / netting ideal" in frame.value.columns)

    def test_button_runs_top_five_and_ranking_can_change_without_research(self):
        at = self.run_app()
        self.assertFalse(any("Last / netting ideal" in frame.value.columns for frame in at.dataframe))
        at.number_input(key="optimiser_budget").set_value(32)
        at.button(key="optimiser_run").click().run()
        self.assertEqual([e.value for e in at.exception], [])
        table = self.table(at)
        self.assertEqual(len(table), 5)
        self.assertEqual(list(table["Rank"]), [1, 2, 3, 4, 5])
        self.assertTrue(table["First-ply [MPa]"].is_monotonic_decreasing)
        self.assertTrue(any(m.label == "Optimiser netting ideal [MPa]" for m in at.metric))
        self.assertTrue(any("Screening tool, not a design" in c.value for c in at.caption))
        at.selectbox(key="optimiser_objective").set_value("Last-ply model stop").run()
        self.assertEqual([e.value for e in at.exception], [])
        self.assertTrue(self.table(at)["Last-ply model stop [MPa]"].is_monotonic_decreasing)
        at.number_input(key="vessel_radius").set_value(200.).run()
        self.assertFalse(any("Last / netting ideal" in frame.value.columns for frame in at.dataframe))
        self.assertTrue(any("Search inputs changed" in info.value for info in at.info))

    def test_single_angle_and_empty_angle_set(self):
        at = self.run_app()
        at.multiselect(key="optimiser_angles").set_value([30.])
        at.button(key="optimiser_run").click().run()
        self.assertEqual([e.value for e in at.exception], [])
        table = self.table(at)
        self.assertEqual(len(table), 1)
        self.assertIn("30.00", table.iloc[0]["Layup (half-stack)s"])
        self.assertTrue(any("Top 1" in c.value for c in at.caption))
        at.multiselect(key="optimiser_angles").set_value([])
        at.button(key="optimiser_run").click().run()
        self.assertEqual([e.value for e in at.exception], [])
        self.assertTrue(any("allowed_angles" in e.value for e in at.error))
        self.assertFalse(any("Last / netting ideal" in frame.value.columns for frame in at.dataframe))


if __name__ == "__main__":
    unittest.main()
