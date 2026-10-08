"""Display a fixed sourced CLT case beside fresh core calculations."""
from decimal import Decimal
import json
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
from core.laminate import assemble_laminate_stiffness
from core.lamina import compute_Q_matrix
from core.response import recover_ply_surfaces, ply_force_resultants

ROOT = Path(__file__).resolve().parent


def kaw_comparison():
    """Return source strings and fresh predictions; sidebar inputs are excluded."""
    source = json.loads((ROOT/'verification/kaw_reference.json').read_text(encoding='utf-8'))
    materials = [source['material']]
    layup = [dict(theta=a, t=source['thickness_m'], mat=0) for a in source['angles']]
    stiffness = assemble_laminate_stiffness(layup, materials)
    response = recover_ply_surfaces(stiffness, layup, materials, source['loads'])
    points = []
    # In-ply strain/stress is linear: midpoint recovery equals the average of
    # its surface values and preserves each ply's own material axes.
    for i, ply in enumerate(layup):
        bottom, top = response.ply_surfaces[2*i:2*i+2]
        for position, z, strain, stress in (
            ('Bottom', bottom.z, bottom.local_strain, bottom.local_stress),
            ('Middle', (bottom.z+top.z)/2, (bottom.local_strain+top.local_strain)/2,
             (bottom.local_stress+top.local_stress)/2),
            ('Top', top.z, top.local_strain, top.local_stress)):
            points.append(dict(ply=i+1, angle=ply['theta'], face=position, z=z,
                               strain=strain, stress=stress))
    return source, stiffness, response, points, ply_force_resultants(stiffness, layup, materials, source['loads'])


def comparison_row(quantity, source, calculated, unit, provenance, scale=1., tolerance=None):
    """Half-last-printed-unit check, with absolute floating noise at exact zero."""
    decimal = Decimal(source)
    reference = float(decimal)*scale
    printed_half_unit = float(Decimal('0.5')*Decimal(10)**decimal.as_tuple().exponent)*scale
    absolute_tolerance = tolerance if tolerance is not None else (1e-9 if reference == 0 else printed_half_unit)
    difference = float(calculated)-reference
    return {'Quantity':quantity, 'Source printed':source, 'App':repr(float(calculated)), 'Units':unit,
            'Δ absolute':repr(abs(difference)),
            'Δ [%]':'n/a' if reference == 0 else repr(100*difference/abs(reference)),
            'Tolerance absolute':repr(absolute_tolerance),
            'Check':'Within source precision' if abs(difference) <= absolute_tolerance else 'Outside source precision',
            'Source location':provenance}


def matrix_pair(label, source, calculated, labels, provenance, unit):
    st.markdown(f'**{label} [{unit}]**')
    left, right = st.columns(2)
    left.caption(f'Source — {provenance}')
    right.caption('App — calculated from fixed reference inputs')
    left.dataframe(pd.DataFrame(source, index=labels, columns=labels), width='stretch',
                   alt=f'{label} printed source matrix')
    right.dataframe(pd.DataFrame([[repr(float(x)) for x in row] for row in calculated], index=labels, columns=labels),
                    width='stretch', alt=f'{label} calculated matrix')


def show_comparisons(rows, name):
    st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch', alt=name)


def render_kaw_verification():
    source, stiffness, response, points, forces = kaw_comparison()
    provenance = source['provenance']
    st.subheader('Worked verification: Kaw [30/−45/−60] glass/epoxy')
    st.caption('Fixed source inputs, independent of the sidebar. Compare source and app at the same z coordinate. '
               'Source digits are retained; computed values are shown without decimal rounding. Differences below are app minus source.')
    st.write('E₁ = 38.6 GPa; E₂ = 8.27 GPa; G₁₂ = 4.14 GPa; ν₁₂ = 0.26; each ply = 5 mm. '
             'Nx = 1500 N/m, My = 1500 N·m/m (= N); other resultants = 0. Source: PDF pp. 1, 5.')
    st.info('Source z runs downward and its first ply is on top; app z runs upward and its first ply is at −h/2. '
            'For this algebraic reference comparison we keep the printed numeric z and signed loads. '
            'Source Top therefore corresponds to app Bottom. Engineering shear γ₁₂ = 2ε₁₂ throughout.')
    downloads = st.columns(3)
    for target, path, title, mime in (
        (downloads[0], 'verification/sources/Kaw_section4_3_worked_example.pdf', 'Download Kaw source PDF', 'application/pdf'),
        (downloads[1], 'verification/sources/Doc2.docx', 'Download comparison document', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
        (downloads[2], 'verification/VERIFY_KAW_4_3.md', 'Download full Kaw verification', 'text/markdown')):
        file = ROOT/path
        if file.is_file():
            target.download_button(title, file.read_bytes(), file_name=file.name, mime=mime)

    st.markdown('**1 · Rotated ply stiffness Q̄**')
    angle = st.selectbox('Reference ply angle [deg]', source['angles'], key='verification_kaw_angle')
    index = source['angles'].index(angle)
    matrix_pair(f'Q̄ at {angle}°', source['qbars_gpa'][index], stiffness.qbars[index]/1e9,
                ['x','y','xy'], provenance['qbars_gpa'][index], 'GPa')
    with st.expander('Q and component differences'):
        material = source['material']
        q = compute_Q_matrix(material['E1'],material['E2'],material['G12'],material['v12'])
        matrix_pair('Q', source['q_gpa'], q/1e9, ['1','2','12'], provenance['q_gpa'], 'GPa')
        qbar_rows = [comparison_row(f'Q̄{a}{b}', source['qbars_gpa'][index][i][j], stiffness.qbars[index][i,j]/1e9,
                               'GPa',provenance['qbars_gpa'][index])
                for i,a in enumerate((1,2,6)) for j,b in enumerate((1,2,6)) if j>=i]
        show_comparisons(qbar_rows,'Qbar component comparison')

    st.markdown('**2 · Full ABD matrix**')
    blocks = {name:np.array(source[name],dtype=object) for name in ('A','B','D')}
    source_abd = np.block([[blocks['A'],blocks['B']],[blocks['B'],blocks['D']]])
    left, right = st.columns(2)
    left.caption('Source — PDF p. 5')
    right.caption('App — freshly assembled ABD')
    labels = ['εx⁰','εy⁰','γxy⁰','κx','κy','κxy']
    rows = ['Nx','Ny','Nxy','Mx','My','Mxy']
    left.dataframe(pd.DataFrame(source_abd,index=rows,columns=labels),width='stretch',alt='Source full ABD matrix')
    right.dataframe(pd.DataFrame([[repr(float(x)) for x in row] for row in stiffness.ABD],index=rows,columns=labels),
                    width='stretch',alt='Calculated full ABD matrix')
    st.caption('Block units: A [N/m], B [N], D [N·m]. Zero B₁₂/B₆₆ are checked by absolute difference, without percent division.')
    with st.expander('A, B, D component differences'):
        block_rows=[]
        for name,unit in (('A','N/m'),('B','N'),('D','N·m')):
            matrix=getattr(stiffness,name)
            block_rows.extend(comparison_row(f'{name}{a}{b}',source[name][i][j],matrix[i,j],unit,provenance[name])
                              for i,a in enumerate((1,2,6)) for j,b in enumerate((1,2,6)) if j>=i)
        show_comparisons(block_rows,'ABD component comparison')

    st.markdown('**3 · Mid-plane strain and curvature**')
    solution=np.r_[response.midplane_strain,response.curvature]
    midplane_rows=[comparison_row(label,value,actual,'−' if i<3 else '1/m',provenance['solution'])
                   for i,(label,value,actual) in enumerate(zip(labels,source['solution'],solution))]
    show_comparisons(midplane_rows,'Midplane strain and curvature source comparison')

    st.markdown('**4 · Local strains and stresses through each ply**')
    st.caption('Includes each ply midpoint, as in your document. Source Top / Middle / Bottom maps to '
               'app Bottom / Middle / Top at the same numeric z. Local strain: PDF p. 8. '
               'The full local stress table is on PDF p. 9 as an image and is also reproduced in Doc2.docx.')
    display=[]; differences=[]
    for row, point in enumerate(points):
        description={'Ply':point['ply'],'Angle [deg]':point['angle'],'Source position':('Top','Middle','Bottom')[row%3],
                     'App face':point['face'],'z [m]':point['z']}
        entry=dict(description)
        for name,key,values,unit in (('ε₁','local_strain',point['strain'],'−'),('ε₂','local_strain',point['strain'],'−'),
                                    ('γ₁₂','local_strain',point['strain'],'−'),('σ₁','local_stress',point['stress'],'Pa'),
                                    ('σ₂','local_stress',point['stress'],'Pa'),('τ₁₂','local_stress',point['stress'],'Pa')):
            component={'ε₁':0,'ε₂':1,'γ₁₂':2,'σ₁':0,'σ₂':1,'τ₁₂':2}[name]
            entry[f'{name} source [{unit}]']=source[key][row][component]
            entry[f'{name} app [{unit}]']=repr(float(values[component]))
            differences.append({**description,**comparison_row(name,source[key][row][component],values[component],unit,provenance[key])})
        display.append(entry)
    st.dataframe(pd.DataFrame(display),hide_index=True,width='stretch',alt='Source and calculated local ply strains and stresses')
    with st.expander('Strain and stress differences by z coordinate'):
        show_comparisons(differences,'Local ply strain and stress differences')

    st.markdown('**5 · Force carried by each ply**')
    force_rows=[]
    for i,force in enumerate(forces):
        comparison=comparison_row(f'Nx ply {i+1}',source['ply_nx'][i],force[0],'N/m',provenance['ply_nx'],tolerance=2.5)
        force_rows.append({'Ply':i+1,'Angle [deg]':source['angles'][i],**comparison,
                           'Source Nx share [%]':source['ply_share'][i],
                           'App Nx share [%]':repr(float(100*force[0]/source['loads'][0])),
                           'App Ny [N/m]':repr(float(force[1])),'App Nxy [N/m]':repr(float(force[2]))})
    show_comparisons(force_rows,'Per-ply global force and share comparison')
    st.write('Sum of app ply forces [N/m]:', [float(x) for x in forces.sum(axis=0)])
    st.caption('Printed Nx forces use midpoint stresses rounded to 0.001 MPa; their propagated tolerance is '
               '0.0005 MPa × 0.005 m = 2.5 N/m. Ny and Nxy per ply: NOT REPORTED in the source. '
               'Negative shares and shares above 100% are possible; the sum must equal applied N.')
    checks=qbar_rows+block_rows+midplane_rows+differences+force_rows
    if all(row['Check']=='Within source precision' for row in checks):
        st.success('The compared Kaw results agree within the stated source precision. This is a numerical reference check.')
    else:
        st.warning('Some compared values lie outside source precision; inspect the difference tables above.')
    with st.expander('Source notes and what this case verifies'):
        st.write('PDF p. 2 prints ν₂₁ = 0.0557, but Q denominator substitutions show 0.0057. '
                 'The final Q agrees with the reciprocal relation. The expanded A/B/D arithmetic on p. 4 is clipped; '
                 'three plies are needed for the final sum. On p. 7 the numerical γ₁₂ result is labelled γ₁₂/2; '
                 'the p. 8 table and τ₁₂ = G₁₂γ₁₂ confirm engineering shear.')
        st.info('This case verifies mechanical stiffness, strain/stress recovery and ply-force equilibrium. '
                'It does not validate strengths, failure criteria, progressive failure or vessel burst pressure.')
