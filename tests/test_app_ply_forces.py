"""Check that the mechanical ply-force table and zero-load shares reach the UI."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np


@unittest.skipUnless(importlib.util.find_spec("streamlit"), "streamlit is not installed")
class PlyForceTableTests(unittest.TestCase):
    def test_default_force_table_equilibrium_and_na_shares(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=120).run()
        self.assertEqual([e.value for e in at.exception], [])
        tables = [d.value for d in at.dataframe if "Nx_k [N/m]" in d.value.columns]
        self.assertEqual(len(tables), 1)
        table = tables[0]
        self.assertEqual(len(table), len(at.session_state.plies))
        np.testing.assert_allclose(table[["Nx_k [N/m]","Ny_k [N/m]","Nxy_k [N/m]"]].sum(),
                                   [at.session_state.load_nx,at.session_state.load_ny,
                                    at.session_state.load_nxy], rtol=1e-12, atol=1e-8)
        self.assertEqual(at.number_input(key="load_nx").label, "Nx [N/m]")
        self.assertEqual(at.number_input(key="load_nx").value, 100000.)
        self.assertTrue((table["Ny share [%]"]=="n/a").all())
        self.assertTrue((table["Nxy share [%]"]=="n/a").all())
        self.assertAlmostEqual(table["Nx share [%]"].astype(float).sum(), 100)
        captions = [c.value for c in at.caption]
        self.assertTrue(any("Shares can exceed 100%" in c for c in captions))
        self.assertIn("netting and CLT estimates only; not validated against burst tests", captions)

    def test_existing_session_units_and_presets_preserve_physical_loads(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=120)
        at.session_state["load_nx"] = 123.25  # legacy kN/m input
        at.session_state["load_preset"] = "Custom - type your own values below"
        at.run()
        self.assertEqual([e.value for e in at.exception], [])
        self.assertEqual(at.number_input(key="load_nx").value, 123250.)
        at.run()  # conversion must not repeat on rerun
        self.assertEqual(at.number_input(key="load_nx").value, 123250.)
        at.selectbox(key="load_preset").select("In-plane shear (Nxy = 50000 N/m)").run()
        table = next(d.value for d in at.dataframe if "Nx_k [N/m]" in d.value.columns)
        np.testing.assert_allclose(table[["Nx_k [N/m]","Ny_k [N/m]","Nxy_k [N/m]"]].sum(),
                                   [0,0,50000],rtol=1e-12,atol=1e-8)
        at.selectbox(key="load_preset").select("Bending (Mx = 50 N·m/m)").run()
        self.assertEqual([e.value for e in at.exception], [])
        self.assertEqual(at.number_input(key="load_mx").value,50.)
        self.assertEqual(at.number_input(key="load_nxy").value,0.)


if __name__=="__main__":
    unittest.main()
