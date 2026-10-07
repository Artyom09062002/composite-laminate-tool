"""Every existing tab is eagerly rendered; exercise all major input presets."""
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

class RefineGridTests(unittest.TestCase):
    def clean(self, app):
        self.assertEqual([e.value for e in app.exception], [])
        self.assertEqual(len(app.tabs),11)

    def test_all_material_load_and_layup_presets_render_every_tab(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=120).run()
        self.clean(app)
        for option in app.selectbox(key='material_choice').options:
            with self.subTest(material=option):
                app.selectbox(key='material_choice').select(option).run()
                self.clean(app)
        app.selectbox(key='material_choice').select('Graphite/Epoxy (T300/5208)').run()
        for option in app.selectbox(key='load_preset').options:
            with self.subTest(load=option):
                app.selectbox(key='load_preset').select(option).run()
                self.clean(app)
        for label in ('Unidirectional [0]₄','Cross-ply [0/90]s','Quasi-isotropic [0/45/-45/90]s','Angle-ply [+45/-45]s'):
            with self.subTest(layup=label):
                next(b for b in app.button if b.label == label).click().run()
                self.clean(app)
        text = '\n'.join(e.value for e in app.warning)
        self.assertIn('No like-for-like comparison',text)

    def test_app_loads_with_cached_core_package_missing_thermal_exports(self):
        import core
        names = ('engineering_constants', 'first_ply_mechanical_load_factor', 'recover_thermal_response', 'temperature_change_from_reference')
        saved = {name: getattr(core, name) for name in names}
        try:
            for name in names:
                delattr(core, name)
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=120).run()
            self.clean(app)
        finally:
            for name, value in saved.items():
                setattr(core, name, value)

    def test_single_ply_zero_pressure_and_missing_cte_are_clear(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=120).run()
        app.session_state['plies'] = [{'theta':0.,'t':.000125,'mat':0}]
        app.run()
        self.clean(app)
        app.number_input(key='vessel_working').set_value(0).run()
        self.clean(app)
        app.selectbox(key='material_choice').select('Custom material').run()
        self.clean(app)
        self.assertTrue(any('UNSOURCED' in e.value for e in app.warning))

if __name__ == '__main__':
    unittest.main()
