"""Reference data precision, coordinate pairing and verification UI wiring."""
import unittest
from pathlib import Path
import numpy as np
from verification_view import kaw_comparison, comparison_row


class KawComparisonTests(unittest.TestCase):
    def test_all_printed_local_values_match_by_numeric_z(self):
        source, stiffness, response, points, forces = kaw_comparison()
        self.assertEqual(len(points),9)
        self.assertEqual([p['face'] for p in points[:3]],['Bottom','Middle','Top'])
        np.testing.assert_allclose([p['z'] for p in points[:3]],[-.0075,-.005,-.0025],atol=1e-16)
        for key,prediction,unit in [('local_strain','strain','−'),('local_stress','stress','Pa')]:
            for i,point in enumerate(points):
                for j,value in enumerate(point[prediction]):
                    with self.subTest(key=key,i=i,j=j):
                        row=comparison_row('value',source[key][i][j],value,unit,source['provenance'][key])
                        self.assertEqual(row['Check'],'Within source precision')
        self.assertGreater(points[3]['stress'][2],0)  # -45 ply, z=-0.0025
        self.assertIn('Doc2.docx',source['provenance']['local_stress'])
        self.assertIn('PDF p. 9',source['provenance']['local_stress'])

    def test_source_decimal_precision_and_exact_zero(self):
        self.assertEqual(comparison_row('x','3.780',3.78049,'GPa','p.2')['Check'],'Within source precision')
        self.assertEqual(comparison_row('x','3.780',3.78051,'GPa','p.2')['Check'],'Outside source precision')
        zero=comparison_row('B12','0',5.8e-11,'N','p.4')
        self.assertEqual(zero['Δ [%]'],'n/a')
        self.assertEqual(zero['Check'],'Within source precision')

    def test_ply_forces_use_propagated_midpoint_precision(self):
        source,_,_,_,forces=kaw_comparison()
        for i,value in enumerate(forces[:,0]):
            self.assertEqual(comparison_row('Nx',source['ply_nx'][i],value,'N/m','p.9',tolerance=2.5)['Check'],
                             'Within source precision')
        np.testing.assert_allclose(forces.sum(axis=0),source['loads'][:3],atol=1e-9,rtol=1e-12)


class VerificationUITests(unittest.TestCase):
    def test_reference_page_angles_midpoints_and_sidebar_independence(self):
        from streamlit.testing.v1 import AppTest
        at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=120).run()
        self.assertEqual([e.value for e in at.exception],[])
        tab=at.tabs[10]
        table=next(d.value for d in tab.dataframe if 'Source position' in d.value.columns and 'τ₁₂ app [Pa]' in d.value.columns)
        self.assertEqual(len(table),9)
        self.assertEqual(table.iloc[3]['Source position'],'Top')
        self.assertEqual(table.iloc[3]['App face'],'Bottom')
        self.assertGreater(float(table.iloc[3]['τ₁₂ app [Pa]']),0)
        solution=next(d.value for d in tab.dataframe if 'Quantity' in d.value.columns and 'κxy' in d.value['Quantity'].values)
        before=list(solution['App'])
        at.selectbox(key='verification_kaw_angle').select(-45).run()
        self.assertEqual([e.value for e in at.exception],[])
        qbar_tables=[d.value for d in at.tabs[10].dataframe if list(d.value.columns)==['x','y','xy']]
        self.assertEqual(len(qbar_tables),2)
        self.assertLess(float(qbar_tables[1].iloc[0,2]),0)
        at.number_input(key='load_nx').set_value(9999).run()
        self.assertEqual([e.value for e in at.exception],[])
        after=next(d.value for d in at.tabs[10].dataframe if 'Quantity' in d.value.columns and 'κxy' in d.value['Quantity'].values)
        self.assertEqual(before,list(after['App']))


if __name__=='__main__':
    unittest.main()
