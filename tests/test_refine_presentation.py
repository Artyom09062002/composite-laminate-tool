"""Trace chart coordinates and compact PDF values to solver outputs."""
import io
import re
import unittest
import numpy as np
from core import StrengthAllowables, assemble_laminate_stiffness, engineering_constants, recover_ply_surfaces
from core.progressive import progressive_failure, DegradationRules
from core.vessel import cylinder_resultants
from materials import DEFAULT_MATERIALS
from presentation import progressive_frames, dome_edge_bands, validation_status
from report import build_pdf_report, pressure_strain_drawing
from workflow import parse_layup, screen_cylinder, first_ply_limit

class PresentationTests(unittest.TestCase):
    def analysis(self, count, unbalanced=False):
        record = next(iter(DEFAULT_MATERIALS.values()))
        mat = record.as_core_material()
        allow = StrengthAllowables(**record.as_strengths())
        angles = ['54.735610317245346']*count if unbalanced else ['0','45','-45','90']*(count//4)
        layup = parse_layup('[' + ','.join(angles) + ']', record.ply_thickness)
        stiffness = assemble_laminate_stiffness(layup, [mat])
        response = recover_ply_surfaces(stiffness, layup, [mat], [1e5,0,0,0,0,0])
        prog = progressive_failure(layup, [mat], [allow], cylinder_resultants(1,.1))
        screen = screen_cylinder(layup,[mat],[allow],.1)
        return layup,mat,allow,stiffness,response,prog,screen

    def test_curve_and_event_points_are_solver_states(self):
        *_, prog, screen = self.analysis(16)
        curve, events = progressive_frames(prog)
        p,e = prog.load_strain_curve(1)
        np.testing.assert_array_equal(curve.pressure, p/1e6)
        np.testing.assert_array_equal(curve.strain, e*100)
        self.assertEqual(len(events),len(prog.events))
        for row,event in zip(events.itertuples(),sorted(prog.events,key=lambda e:(e.step,e.ply,e.mode))):
            step = next(s for s in prog.history if s.step == event.step)
            self.assertEqual(row.pressure,event.load_factor/1e6)
            self.assertEqual(row.strain,step.strain_before[1]*100)
        drawing = pressure_strain_drawing(prog,'Helvetica')
        circles = [x for x in drawing.contents if type(x).__name__ == 'Circle']
        self.assertEqual(len(circles),len(events))

    def test_dome_shading_uses_flagged_station_cells_only(self):
        import pandas as pd
        frame = pd.DataFrame({'r':[100,80,60,50], 'valid':[False,True,True,False]})
        bands = dome_edge_bands(frame)
        np.testing.assert_array_equal(bands,[[100,90],[55,50]])

    def test_validation_badge_preserves_unscored_status(self):
        self.assertIn('No like-for-like comparison',validation_status())
        self.assertIn('Not validated against experiment',validation_status())

    def test_pdf_one_page_and_cylinder_values_for_4_16_40_plies(self):
        for count, unbalanced in ((4,False),(16,False),(40,False),(4,True)):
            with self.subTest(plies=count,unbalanced=unbalanced):
                layup,mat,allow,stiffness,response,prog,screen = self.analysis(count,unbalanced)
                allows = [allow]*len(response.ply_surfaces)
                pdf = build_pdf_report(material_name='T300/5208',material=mat,strengths=allow,layup=layup,
                      material_names=['Sidebar material'],loads=[1e5,0,0,0,0,0],stiffness=stiffness,
                      constants=engineering_constants(stiffness),response=response,surface_strengths=allows,
                      first_ply=first_ply_limit(response.ply_surfaces,allows),
                      vessel={'screen':screen,'progressive':prog,'rules':DegradationRules(),'radius_m':.1,'working_mpa':10})
                self.assertEqual(len(re.findall(rb'/Type /Page\b',pdf)),1)
                for value in (screen.first_ply_pressure_pa,prog.first_ply_load_factor,prog.last_ply_load_factor,screen.netting_pressure_pa):
                    self.assertIn(f'{value/1e6:.4f}'.encode(),pdf)
                self.assertIn(b'not an ultimate or burst load',pdf)
                self.assertIn(b'E1=181',pdf)
                self.assertIn(b'Xt=1500',pdf)
                self.assertIn(b'linear-model extrapolation',pdf)
                if unbalanced:
                    self.assertIn(b'not shear equilibrium',pdf)

if __name__ == '__main__':
    unittest.main()
