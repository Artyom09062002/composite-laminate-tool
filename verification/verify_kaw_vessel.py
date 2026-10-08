"""Reproduce the sourced checks; run from repository root. No fitted parameters.

Printed numbers retain their original strings. Computed values use float repr,
without decimal formatting/rounding. Source transcription includes image tables.
"""
from pathlib import Path
import math
import sys
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.laminate import assemble_laminate_stiffness
from core.lamina import compute_Q_matrix
from core.response import recover_ply_surfaces, ply_force_resultants
from core.transformations import transform_stress_strain
from core.vessel import NETTING_ANGLE_DEG, cylinder_resultants
from core.failure import StrengthAllowables
from core.progressive import progressive_failure
from materials import DEFAULT_MATERIALS
from workflow import angle_ply_wall, parse_layup, screen_cylinder


def number(value):
    return repr(float(value))


def hand_qbar(q, theta):
    """Independent scalar textbook polynomial, with engineering shear."""
    c, s = math.cos(math.radians(theta)), math.sin(math.radians(theta))
    a, b, d, g = q[0, 0], q[0, 1], q[1, 1], q[2, 2]
    xx = a*c**4 + 2*(b+2*g)*s*s*c*c + d*s**4
    yy = a*s**4 + 2*(b+2*g)*s*s*c*c + d*c**4
    xy = (a+d-4*g)*s*s*c*c + b*(s**4+c**4)
    xs = (a-b-2*g)*c**3*s - (d-b-2*g)*c*s**3
    ys = (a-b-2*g)*c*s**3 - (d-b-2*g)*c**3*s
    ss = (a+d-2*b-2*g)*s*s*c*c + g*(s**4+c**4)
    return np.array([[xx, xy, xs], [xy, yy, ys], [xs, ys, ss]])


def printed(value):
    value = value.replace('−', '-').replace(' ', '').replace('×', '*')
    value = value.replace('(10^', '*10^').replace(')', '')
    if '*10^' in value:
        mantissa, exponent = value.split('*10^')
        scale = 10.**int(exponent)
    else:
        mantissa, scale = value, 1.
    decimals = len(mantissa.split('.')[1]) if '.' in mantissa else 0
    return float(mantissa)*scale, .5*10.**(-decimals)*scale


def kaw_report():
    material = {"E1":38.6e9, "E2":8.27e9, "G12":4.14e9, "v12":.26}
    layup = [{"theta":a, "t":.005, "mat":0} for a in (30,-45,-60)]
    loads = np.array([1500.,0.,0.,0.,1500.,0.])
    stiffness = assemble_laminate_stiffness(layup, [material])
    response = recover_ply_surfaces(stiffness, layup, [material], loads)
    forces = ply_force_resultants(stiffness, layup, [material], loads)
    # Independent hand arithmetic from the printed input constants, not core Q.
    nu21 = material['v12']*material['E2']/material['E1']
    denominator = 1-material['v12']*nu21
    qh = np.array([[material['E1']/denominator, material['v12']*material['E2']/denominator, 0],
                   [material['v12']*material['E2']/denominator, material['E2']/denominator, 0],
                   [0,0,material['G12']]])
    qbars = [hand_qbar(qh, p['theta']) for p in layup]
    z = [-.0075,-.0025,.0025,.0075]
    ah = sum(q*.005 for q in qbars)
    bh = sum(q*(b*b-a*a)/2 for q,a,b in zip(qbars,z[:-1],z[1:]))
    dh = sum(q*(b**3-a**3)/3 for q,a,b in zip(qbars,z[:-1],z[1:]))
    solution = np.linalg.solve(np.block([[ah,bh],[bh,dh]]),loads)
    rows, outside = [], []

    def row(label, source, page, hand, actual, absolute=False, tolerance=None):
        ref, half = printed(source)
        delta = float(actual)-ref
        difference = number(abs(delta))+' absolute' if absolute or ref == 0 else number(100*delta/abs(ref))+' %'
        rows.append(f'| {label} | {source} (p. {page}) | {number(hand)} | {number(actual)} | {difference} |')
        if abs(delta) > (half if tolerance is None else tolerance) and not absolute:
            outside.append(f'{label}: Δ={number(delta)}, half printed unit={number(half)}')

    qa = compute_Q_matrix(**dict(E1=material['E1'],E2=material['E2'],G12=material['G12'],v12=material['v12']))
    row('ν21 [-]', '0.0557', 2, nu21, nu21)
    for i,j,source in ((0,0,'39.17*10^9'),(0,1,'2.182*10^9'),(1,1,'8.392*10^9'),(2,2,'4.14*10^9'),(0,2,'0'),(1,2,'0')):
        row(f'Q{(1,2,6)[i]}{(1,2,6)[j]} [Pa]',source,2,qh[i,j],qa[i,j],source=='0')
    qb_sources = [
        ['26.48*10^9','7.176*10^9','9.546*10^9','11.09*10^9','3.780*10^9','9.134*10^9'],
        ['17.12*10^9','8.841*10^9','-7.694*10^9','17.12*10^9','-7.694*10^9','10.80*10^9'],
        ['11.09*10^9','7.176*10^9','-3.780*10^9','26.48*10^9','-9.546*10^9','9.134*10^9']]
    entries = [(0,0),(0,1),(0,2),(1,1),(1,2),(2,2)]
    for k, sources in enumerate(qb_sources):
        for (i,j),source in zip(entries,sources):
            row(f'Qbar ply {k+1}, {(1,2,6)[i]}{(1,2,6)[j]} [Pa]',source,2 if k<2 else 3,qbars[k][i,j],stiffness.qbars[k][i,j])
    blocks = [
        ('A',ah,stiffness.A,'N/m',['2.735*10^8','1.160*10^8','-9.636*10^6','2.735*10^8','-6.730*10^7','1.453*10^8']),
        ('B',bh,stiffness.B,'N',['-3.847*10^5','0','-3.332*10^5','3.847*10^5','-3.332*10^5','0']),
        ('D',dh,stiffness.D,'N m',['5.266*10^3','2.036*10^3','7.008*10^2','5.266*10^3','-8.611*10^2','2.586*10^3'])]
    for name, hand, actual, unit, sources in blocks:
        for (i,j),source in zip(entries,sources):
            row(f'{name}{(1,2,6)[i]}{(1,2,6)[j]} [{unit}]',source,4,hand[i,j],actual[i,j],source=='0')
    app_solution = np.r_[response.midplane_strain,response.curvature]
    for label,source,hand,actual in zip(['εx0 [-]','εy0 [-]','γxy0 [-]','κx [1/m]','κy [1/m]','κxy [1/m]'],
        ['1.624*10^-4','-3.532*10^-4','4.908*10^-4','-1.403*10^-1','4.210*10^-1','1.536*10^-1'],solution,app_solution):
        row(label,source,5,hand,actual)
    # Source calls this Top: compare explicitly at z=-0.0025, app Bottom.
    point = response.ply_surfaces[2]
    eh = solution[:3]-.0025*solution[3:]
    sh = qbars[1]@eh
    lh = np.array([(eh[0]+eh[1]-eh[2])/2,(eh[0]+eh[1]+eh[2])/2,eh[0]-eh[1]])
    local_sh = qh@lh
    for label,sources,hand,actual,page in (
        ('global strain', ['5.131*10^-4','-1.406*10^-3','1.068*10^-4'],eh,point.global_strain,5),
        ('global stress [Pa]', ['-4.466*10^6','-2.035*10^7','8.022*10^6'],sh,stiffness.qbars[1]@point.global_strain,6),
        ('local engineering strain', ['-4.998*10^-4','-3.930*10^-4','1.919*10^-3'],lh,point.local_strain,7),
        ('local stress [Pa]', ['-2.043*10^7','-4.388*10^6','7.944*10^6'],local_sh,point.local_stress,8)):
        for i,(source,h,a) in enumerate(zip(sources,hand,actual)):
            row(f'ply 2 z=-0.0025 m {label} component {i+1}',source,page,h,a)
    midpoint_printed = [2.584e6,-4.119e6,1.835e6]
    for k,source in enumerate(['12920','-20595','9175']):
        row(f'Nx ply {k+1} [N/m]',source,9,midpoint_printed[k]*.005,forces[k,0],tolerance=.0005e6*.005)
    for k,source in enumerate(['861.33','-1373','611.67']):
        row(f'Nx share ply {k+1} [%]',source,10,midpoint_printed[k]*.005/1500*100,forces[k,0]/1500*100,
            tolerance=(.0005e6*.005)/1500*100+.005)
    main_rows = list(rows)
    rows.clear()
    transcription = (ROOT/'verification/KAW_SOURCE_TRANSCRIPTION.md').read_text(encoding='utf-8')
    # Literal image-table entries are retained in the independent transcription.
    table_sections = [
        ('Top/middle/bottom global strain table',6,'global strain'),
        ('Top/middle/bottom global stress table',7,'global stress'),
        ('Top/middle/bottom local strain table',8,'local strain'),
        ('Top/middle/bottom local stress table',9,'local stress')]
    for heading,page,kind in table_sections:
        part = transcription.split(heading,1)[1].split('\n\nThe ',1)[0].split('\n## ',1)[0]
        for line in part.splitlines():
            fields = [x.strip() for x in line.split('|')[1:-1]]
            if len(fields)!=6 or not fields[0].isdigit():
                continue
            k=int(fields[0])-1
            position=fields[2]
            zp={'Top':z[k],'Middle':(z[k]+z[k+1])/2,'Bottom':z[k+1]}[position]
            e=response.midplane_strain+zp*response.curvature
            he=solution[:3]+zp*solution[3:]
            if kind=='global stress':
                actual=stiffness.qbars[k]@e
                hand=qbars[k]@he
            elif kind=='local strain':
                actual=transform_stress_strain(e,layup[k]['theta'],'strain')
                c,s=math.cos(math.radians(layup[k]['theta'])),math.sin(math.radians(layup[k]['theta']))
                hand=np.array([c*c*he[0]+s*s*he[1]+s*c*he[2],s*s*he[0]+c*c*he[1]-s*c*he[2],
                               -2*s*c*he[0]+2*s*c*he[1]+(c*c-s*s)*he[2]])
            elif kind=='local stress':
                actual=qa@transform_stress_strain(e,layup[k]['theta'],'strain')
                c,s=math.cos(math.radians(layup[k]['theta'])),math.sin(math.radians(layup[k]['theta']))
                local_hand=np.array([c*c*he[0]+s*s*he[1]+s*c*he[2],s*s*he[0]+c*c*he[1]-s*c*he[2],
                                     -2*s*c*he[0]+2*s*c*he[1]+(c*c-s*s)*he[2]])
                hand=qh@local_hand
            else:
                actual=e; hand=he
            for i,source in enumerate(fields[3:]):
                row(f'ply {k+1}, z={number(zp)} m, {kind} component {i+1}',source.strip('`'),page,hand[i],actual[i])
    a_from_printed = (26.48+17.12+11.09)*1e9*.005
    precision_conclusion = ('Some entries exceed a literal half-unit; see the exceptions below. Their exact historical calculation path is NOT REPORTED.'
                            if outside else 'All reported Q, Qbar, A/B/D, midplane solution, point strain/stress and through-thickness table entries agree within half a unit of their last printed digit. No literal half-unit exceptions were found for these quantities.')
    text = '''# Verification: Kaw section 4.3

Source: provided PDF, kept locally at verification/sources/Kaw_section4_3_worked_example.pdf and excluded from Git, copied byte-for-byte from the supplied Downloads file. All 10 pages were read as text; numerical image tables on pp. 6–9 were inspected visually. The expanded A/B/D arithmetic on p. 4 is clipped at the right edge: those missing terms could not be read. Correction: the local stress table is present as an image on p. 9; its initial omission from this report came from text extraction missing that image. Only visible data are used; absent entries are NOT REPORTED.

The PDF identifies its material inputs as Table 2.1 (p. 1). The original book table itself was not supplied/read. No strength data are reported here. See [literal transcription](KAW_SOURCE_TRANSCRIPTION.md) for every visible input, matrix, table and result.

## Inputs and coordinate mapping

E1=38.6 GPa, E2=8.27 GPa, G12=4.14 GPa, ν12=0.26 (p. 1); each ply 5 mm; [30/-45/-60]; [Nx,Ny,Nxy,Mx,My,Mxy]=[1500,0,0,0,1500,0], N in N/m and M in N (pp. 1,5). No fitted values. h=0.015 m and coordinates [-0.0075,-0.0025,0.0025,0.0075] m (p. 3).

The source uses z downward and calls the ply-2 face at z=-0.0025 m Top. In the app the identical numeric coordinate and ply sequence use z upward, so that face is Bottom. This check identifies algebraic coordinates, angles and signed generalized loads with the source; it is not a physical reflection of a fixed specimen. A physical change z_app=-z_Kaw would also reverse ply order and signs of B, M and κ (and any corresponding axis handedness). No app convention is changed. Engineering shear γ12=2ε12 throughout.

## Comparison

Every computed value below uses Python float repr without decimal rounding. Source mantissas retain printed precision. Difference is 100(app-source)/abs(source); zeros use |app-source| with the quantity's units. Symmetric matrices show their six independent entries; A/B/D specify the entire ABD of p. 5. Hand values independently form Q and scalar Qbar polynomials, integrate A/B/D, solve the hand ABD, and transform strains/stresses. They share NumPy's linear solver, but no core stiffness/transformation implementation. Ply-load hand values instead multiply the *printed* midpoint σx by printed thickness.

| Quantity | Source (page) | Hand check | App | Difference % or absolute |
|---|---|---|---|---|
'''+ '\n'.join(main_rows)+'''

Ny_k and Nxy_k: NOT REPORTED in part (e). These app predictions are not source comparisons:

| Ply | Nx_k [N/m] | Ny_k [N/m] | Nxy_k [N/m] |
|---|---|---|---|
'''+ '\n'.join(f'| {k+1} | '+ ' | '.join(number(x) for x in force)+' |' for k,force in enumerate(forces))+f'''

Sum of app ply forces [N/m]: {list(map(float,forces.sum(axis=0)))}. Applied N: [1500,0,0] N/m. Residual [N/m]: {list(map(float,forces.sum(axis=0)-loads[:3]))}.

## All printed through-thickness tables

z, not the source's Top/Bottom words, selects each point. Strain units are dimensionless; global stresses are Pa.

| Quantity | Source (page) | Hand check | App | Difference % or absolute |
|---|---|---|---|---|
'''+ '\n'.join(rows)+f'''

## Printed inconsistencies and precision

* p. 2: reciprocal relation gives ν21={number(nu21)}. Printed 0.0557 is consistent with that precision; denominator substitutions print 0.0057. Using that erroneous substitution gives Q11={number(38.6e9/(1-.0057*.26))} Pa, incompatible with printed 39.17*10^9 Pa. The final Q is consistent with the reciprocal relation, not that substitution.
* p. 4: the visible A expansion shows two terms and a trailing continuation clipped at the right edge. The complete three-ply A11 sum from printed Qbars is {number(a_from_printed)} N/m, agreeing with printed 2.735*10^8 N/m. A third term is required; the visible two-term expression alone does not equal the result. It cannot be established whether the clipped original was complete. B/D expansions have the same clipping.
* p. 7: multiplying the displayed tensor-strain T by the printed vector gives the third component {number((5.131e-4-(-1.406e-3))/2)}. That is γ12/2. Doubling gives {number(5.131e-4-(-1.406e-3))}, consistent with printed 1.919*10^-3 and the γ12 header on p. 8. Conclusion: the p. 7 numerical result's third entry is engineering γ12 mislabelled as γ12/2. App γ12={number(point.local_strain[2])}; G12γ12={number(point.local_stress[2])} Pa agrees with p. 8 τ12. Changing the app convention would create a factor-of-two error.
* p. 9 uses rounded midpoint stresses before multiplying by thickness. Therefore printed integer forces and p. 10 percentages do not have independent integer/last-decimal precision. Tests use the propagated half-unit from 0.001 MPa midpoint precision: 0.0005 MPa times 0.005 m = 2.5 N/m. No parameter is tuned.
* {precision_conclusion} Zero B12/B66 agree by absolute floating-point residual. Nx for plies 2 and 3 differs by more than half of the integer unit printed in part (e), but agrees within 2.5 N/m from the actual precision of the source midpoint stresses. Their literal integer digits are not an independent accuracy claim.

Literal half-unit exceptions (excluding ply-load propagated tolerances):

'''+ ('\n'.join('* '+x for x in outside) if outside else 'None for stiffness/strain/stress; per-ply loads use propagated source precision as explained above.')+'''

## Scope and rerun

This case checks linear mechanical stiffness assembly, extension–bending coupling, engineering-shear transforms, global/local stress recovery at known coordinates, and exact integrated ply-force equilibrium. It does not validate strength allowables, any failure criterion, progressive failure, pressure vessels or burst strength.

Run `python verification/verify_kaw_vessel.py` and `python -m unittest discover -s tests -q`. Focused tests cover printed ABD and per-ply Nx within source-digit tolerances, mixed-material equilibrium with membrane/moment/combined loading, and exact midpoint integration. Printed detailed strain/stress comparisons are reported above, not silently fitted or forced to pass.
'''
    (ROOT/'verification/VERIFY_KAW_4_3.md').write_text(text,encoding='utf-8')
    return {'force_sum':forces.sum(axis=0).tolist(),'forces':forces.tolist(),'solution':app_solution.tolist(),
            'literal_precision_exceptions':outside}


def vessel_report():
    # Defaults read from app.py and materials/database.py, not external allowables.
    record=DEFAULT_MATERIALS['Graphite/Epoxy (T300/5208)']
    materials=[record.as_core_material()]
    strengths=[StrengthAllowables(**record.as_strengths())]
    radius=.1; pressure=10e6; thickness=record.ply_thickness
    study=angle_ply_wall(NETTING_ANGLE_DEG,16,thickness)
    current=parse_layup('[0,45,-45,90]s',.125e-3)
    study_result=screen_cylinder(study,materials,strengths,radius)
    current_result=screen_cylinder(current,materials,strengths,radius)
    progressive=progressive_failure(current,materials,strengths,cylinder_resultants(1.,radius))
    sweep=[(screen_cylinder(angle_ply_wall(theta,16,thickness),materials,strengths,radius).first_ply_pressure_pa,theta)
           for theta in range(91)]
    best=max(sweep,key=lambda x:x[0])
    angle_hand=math.atan(math.sqrt(2))*180/math.pi
    doc=f'''# Цилиндрический сосуд: как читать вкладку Pressure vessel

Это учебные оценки netting и CLT, без проверки по испытаниям на разрыв. Ось x направлена вдоль цилиндра, y — по окружности; угол слоя отсчитывается от x. Ниже формулы относятся к прямому участку тонкостенного цилиндра с закрытыми торцами и равномерным избыточным давлением; R [м], p [Па], h [м], напряжения [Па], усилия на единицу ширины N [Н/м], моменты M [Н·м/м = Н], деформации и доли безразмерны, кривизна [1/м].

## 1. Из давления получить нагрузки для CLT

Поперечный разрез: давление на торец даёт pπR² [Н]. Стенка передаёт 2πR Nx [Н]. Из pπR²=2πR Nx следует **Nx=pR/2 [Н/м]**. Продольный разрез длиной L [м]: проекция давления равна p·2R·L [Н], две стороны стенки передают 2NyL [Н]. Поэтому **Ny=pR [Н/м]**. Для этой мембранной идеализации Nxy=0 [Н/м], Mx=My=Mxy=0 [Н]. Это нагрузки для плоской CLT-модели стенки, а не напряжения одного слоя. Вывод также показан в [Roylance, Pressure Vessels](https://web.mit.edu/course/3/3.11/www/modules/pv.pdf), с. 3, уравнения (2),(3).

## 2. Откуда угол 54.74°

В сбалансированной паре ±θ силы волокон по касательной создают **Nx=σf h cos²θ**, **Ny=σf h sin²θ** [Н/м]; здесь h — суммарная несущая толщина пары, σf [Па] — напряжение вдоль волокон. Сдвиговые составляющие пары взаимно компенсируются. Деление уравнений даёт **tan²θ=Ny/Nx=2 [-]**. Тогда **θ=atan(√2) [рад]**, а перевод в градусы выполняется множителем 180/π [град/рад]. Код возвращает {number(NETTING_ANGLE_DEG)}°, подпись 54.74° — существующее представление угла в интерфейсе. Ручная формула, вычисленная скриптом, даёт {number(angle_hand)}°. В опубликованном разобранном Example 1 Roylance (с. 4, рис. 6) напечатано **54.7°**: сравнение по точности этой записи согласуется. R, p, h, прочность и давление разрушения в этом примере: **NOT REPORTED**. Проверяется только равновесный угол, а не прочность стенки.

## 3. Что предполагает netting

Нагрузку несут только волокна в растяжении; вклад матрицы отсутствует. Приложение ищет напряжения каждого слоя между нулём и Xt [Па], чтобы **Σσk tk cos²θk=pR/2** и **Σσk tk sin²θk=pR** [Н/м]. Совместность деформаций не навязывается. Сдвиговое равновесие этим решателем тоже не проверяется, поэтому для несбалансированной укладки результат нельзя считать допустимой стенкой. Для единственной пары ±θ вдали от равновесного угла положительное давление может быть невозможно.

При единственном равновесном ±θ и одинаковом Xt: **p_net=2Xt h/(3R) [Па]**, или **h_req=3pR/(2Xt) [м]**. Это модель волокон, не экспериментальная burst strength. На графике `Fibre-limit projection bound` показано **min(2ΣXt,k tk cos²θk, ΣXt,k tk sin²θk)/R [Па]**: вне равновесия направлений это только проекционная верхняя оценка, которая может быть положительной при нулевом netting pressure.

## 4. Что делает CLT и что означает разрушение

CLT решает **[ε0,κ]ᵀ=ABD⁻¹[N,M]ᵀ** (единицы блоков A [Н/м], B [Н], D [Н·м]), затем **ε(z)=ε0+zκ [-]**, **σ12=Qε12 [Па]**. Здесь ε12 — вектор [ε1,ε2,γ12], инженерный сдвиг γ12=2ε12_tensor. Слои идут снизу вверх: z=-h/2…+h/2 [м]. Первая граница слоя Bottom, вторая Top.

`First-ply failure pressure` — минимум давлений по Maximum Stress и Tsai–Wu; подпись критерия показывает, что ограничило результат. Указанный режим относится к наиболее нагруженной компоненте Maximum Stress в выбранной точке, даже если ограничил Tsai–Wu; это не разложение Tsai–Wu по механизмам. Это начало повреждения в модели. В отдельном progressive-блоке `First-ply, Hashin` использует Hashin; значения могут различаться, потому что выбираются разные критерии.

`Last-ply (model stop)` — давление остановки существующего алгоритма деградации, а не доказанное разрушение последнего физического слоя. После событий снижаются жёсткости, ABD собирается снова, напряжения перераспределяются. Повторное превышение после двух уровней деградации прекращает расчёт; остаточные жёсткости положительны. Коэффициенты сохранения E1/E2/G12 — модельные предположения, не измеренные свойства. `Last-ply / first-ply` — безразмерное отношение двух давлений этой модели, не запас сертифицированного сосуда. Ступени/анимация показывают нагрузку, режим, слой и перераспределение; совпадающие давления могут означать каскад, устойчивость пути не проверяется.

## 5. Порядок чтения чисел

Сначала выберите материал, радиус и working pressure. `Wall plies` и default ply thickness задают стенку исследования ±θ: **h=n t [м]**. `Netting angle` — равновесный угол волокон; `Netting estimate` относится к нему. `Best first-ply pressure` — максимум CLT среди углов целочисленной сетки, не непрерывная оптимизация. Кривые показывают first-ply, остановку Hashin и проекционную оценку волокон в [МПа]. **p[МПа]=p[Па]/10⁶**.

Ниже `Current layup` использует отдельную таблицу слоёв, а не `Wall plies`. `First-ply failure pressure` и `Fibre-only netting reference` относятся к этой текущей укладке. `Netting / working pressure=p_net/p_work [-]` сравнивает только два давления; из этого отношения не следует безопасность по CLT. Рабочее давление не заменяет боковые механические нагрузки других вкладок. Все шесть боковых нагрузок теперь вводятся в СИ: Nx, Ny, Nxy [Н/м], Mx, My, Mxy [Н·м/м = Н]. Это моменты на единицу ширины, поэтому метр сокращается. Правило чтения: сравнить p_work с first-ply; затем рассмотреть режим, место и ограничения, а progressive/netting читать отдельно.

Во вкладке уже есть дополнительные блоки: optimiser ранжирует варианты с фиксированными числом слоёв и толщиной по показанным метрикам; число кандидатов и углы ограничивают поиск, это не доказательство глобального оптимума. Dome — отдельный идеализированный мембранный расчёт станций купола: координата, радиус, угол намотки, толщина и first-ply относятся к выбранной станции; предупреждения исключают ненадёжные станции из минимума. Он не моделирует локальный переход цилиндр–купол, бобышку, межслойные напряжения и краевые эффекты. Эти блоки не расширялись и не проверялись этим заданием.

## 6. Числовой пример из запуска кода с defaults

Источник входных чисел — текущие `app.py` и `materials/database.py`, а не новый эксперимент: T300/5208; R=100.0 мм, p_work=10.0 МПа, исследование 16 слоёв, t={number(thickness)} м. E1={number(record.E1)} Па, E2={number(record.E2)} Па, G12={number(record.G12)} Па, ν12={number(record.v12)}; Xt={number(record.Xt)} Па, Xc={number(record.Xc)} Па, Yt={number(record.Yt)} Па, Yc={number(record.Yc)} Па, S={number(record.S)} Па. Это существующий учебный dataset; первичный источник прочностей в данном задании не перечитывался, их квалификация не подтверждается. Все результаты ниже получены вызовами core/workflow и сохранены в `verification/kaw_vessel_results.json`, без округления.

`cylinder_resultants(10e6,0.1)` даёт Nx={number(cylinder_resultants(pressure,radius)[0])} Н/м, Ny={number(cylinder_resultants(pressure,radius)[1])} Н/м; остальные компоненты нулевые. Подстановка pR/2 и pR даёт те же значения, выполнена скриптом. Для стенки исследования h={number(16*thickness)} м, при равновесном ±θ код даёт p_net={number(study_result.netting_pressure_pa)} Па; ручная формула 2Xt h/(3R), вычисленная скриптом, даёт {number(2*record.Xt*16*thickness/(3*radius))} Па. CLT first-ply при этом угле: {number(study_result.first_ply_pressure_pa)} Па ({study_result.first_ply_criterion}). Максимум first-ply по углам от 0 до 90° с шагом 1°: {number(best[0])} Па при {best[1]}°; он отличается от максимума netting, поскольку CLT учитывает поперечные/сдвиговые напряжения и выбранные критерии.

Текущая начальная укладка [0,45,-45,90]s: 8 слоёв, h={number(8*.125e-3)} м. Её first-ply={number(current_result.first_ply_pressure_pa)} Па, критерий {current_result.first_ply_criterion}, режим {current_result.first_ply_mode}, слой {current_result.first_ply_ply}, поверхность {current_result.first_ply_surface}. Hashin first-ply={number(progressive.first_ply_load_factor)} Па; model stop={number(progressive.last_ply_load_factor)} Па; отношение={number(progressive.last_ply_load_factor/progressive.first_ply_load_factor)} [-]. Netting={number(current_result.netting_pressure_pa)} Па; netting/working={number(current_result.netting_pressure_pa/pressure)} [-]. Рабочее давление выше first-ply в этой модели: показывать этот пример как подтверждённую работоспособность сосуда нельзя.

## 7. Чего модель не учитывает

Несущую работу и контакт лайнера; реальные торцы, бобышки и локальные краевые эффекты; разброс свойств и дефекты; влажность, усталость и утечки; нелинейность, расслоение и устойчивость. Купольный блок — лишь отдельная идеализация, не устранение этих ограничений. Thermal включается отдельно в Failure; включение того блока не добавляет тепловые напряжения к цилиндрическому/progressive расчёту. В текущей вкладке Pressure vessel thermal отключён из механики полностью. Остальные числа — оценки модели, не результаты испытаний на разрыв.

## 8. Пять вопросов преподавателя

1. **Почему окружная нагрузка вдвое больше осевой?** Разные разрезы равновесия: закрытый торец и продольный разрез дают pR/2 и pR [Н/м].
2. **Всегда ли 54.74° лучший угол?** Это равновесный угол одной волоконной ±θ системы; лучший first-ply CLT зависит от материала, укладки и критерия.
3. **Почему netting выше first-ply?** Netting не ограничивает матрицу и сдвиг; CLT-критерии могут достичь порога раньше волокон.
4. **Last-ply означает burst?** Нет: это остановка алгоритма с заданными остаточными жёсткостями, без критерия утечки/устойчивости и без корреляции с испытаниями.
5. **Что проверено источниками?** Kaw — механическая жёсткость и восстановление напряжений плоского ламината; Roylance — равновесный угол. Сосудная прочность и progressive failure не валидированы.
'''
    (ROOT/'docs/PRESSURE_VESSEL_EXPLAINED_RU.md').write_text(doc,encoding='utf-8')
    verification=f'''# Verification: published filament-wound vessel examples

## Sources read and available comparisons

1. David Roylance, *Pressure Vessels*, MIT, August 23, 2001: [official PDF](https://web.mit.edu/course/3/3.11/www/modules/pv.pdf), local copy `sources/Roylance_pressure_vessels.pdf`. All 10 pages read as extracted text; Example 1 p. 4 / Figure 6 is the worked filament-winding angle derivation. Printed input is the closed-cylinder hoop/axial equilibrium relationship, with symbolic p,r,b,n,T. Printed answer: tan²α=2, α=54.7°. Numerical radius, pressure, thickness, fibre strength, netting failure pressure: NOT REPORTED in Example 1. Other numerical examples concern isotropic/compound cylinders, so they are not used to check composite netting strength.
2. David K. Roylance, *Netting Analysis for Filament-Wound Pressure Vessels*, AMMRC TN 76-3, August 1976: [official PDF](https://web.mit.edu/roylance/www/netting.pdf), local copy `sources/Roylance_netting.pdf`. This is an image-only scan; all 9 PDF pages visually inspected. Printed pp. 5–6 (PDF pp. 6–7) show a worked Kevlar bottle with measured burst and predicted strains/stresses. The faint calculator output on printed p. 6 is not fully legible and has not been used to extract extra numbers; no exact data are inferred from graphs.

## Like-for-like check: Example 1, angle

Independent hand equilibrium: for balanced ±θ, Nx=σf h cos²θ and Ny=σf h sin²θ [N/m]. Closed-end pressure gives Ny/Nx=2 [-], hence atan(sqrt(2)) in radians, converted to degrees. No material, radius or thickness can change that ratio within these assumptions.

| Quantity | Source | Hand (computed, unrounded) | App core (unrounded) | Difference |
|---|---|---|---|---|
| Ny/Nx [-] | 2, p. 3 eqs. (2),(3); p. 4 Example 1 | 2 | {number(cylinder_resultants(1.,1.)[1]/cylinder_resultants(1.,1.)[0])} | 0 absolute |
| tan²α [-] | 2, p. 4 Example 1 | 2 | {number(math.tan(math.radians(NETTING_ANGLE_DEG))**2)} | {number(abs(math.tan(math.radians(NETTING_ANGLE_DEG))**2-2))} absolute |
| α [deg] | 54.7, p. 4 Example 1 / Figure 6 | {number(angle_hand)} | {number(NETTING_ANGLE_DEG)} | {number(NETTING_ANGLE_DEG-54.7)} deg; {number((NETTING_ANGLE_DEG-54.7)/54.7*100)} % |
| Nx, Ny [N/m] numerical | NOT REPORTED in Example 1 | NOT REPORTED | NOT COMPARABLE | n/a |
| Required thickness [m] | NOT REPORTED in Example 1 | NOT REPORTED | NOT COMPARABLE | n/a |
| Netting pressure [Pa] | NOT REPORTED in Example 1 | NOT REPORTED | NOT COMPARABLE | n/a |

Angle agrees within half of the source's last printed unit (0.05 degree). `(p,R)=(1 Pa,1 m)` in the ratio check is an explicitly chosen algebraic test of `cylinder_resultants`, not an input attributed to Roylance.

## Why the second published worked example is not an app strength validation

Printed pp. 5–6 use diameter 6 inch, length 14 inch, ±25° helical winding plus hoops, Ah=0.0232 in²/in, Aα1=0.0155 in²/in, Aα2=0, and measured burst 3042 psig. The p. 6 table prints netting hoop/axial strains 1.84%/1.89%, hoop/helical fibre stresses 351/358 ksi; gauge-derived values are 1.25%/0.69% and 238/160 ksi. These are not fitted inputs for this app.

That note obtains fibre stress and strain through a common fibre modulus and strain compatibility, equations (2)–(4),(9)–(15). The app's `netting_pressure` maximizes pressure subject to axial/hoop force equilibrium and supplied fibre strength limits; it does not predict those strains or implement the note's compatibility solution. Fibre area per width is not composite wall thickness without fibre volume fraction. No qualified Xt or fully specified CLT material/layup is supplied by the read example for this implementation. Treating measured burst as Xt, converting its fibre areas into laminate thickness, or using the source's predicted stresses as fitted strengths would manufacture a validation. No such conversion/tuning was made.

Thus a published worked filament-winding angle example is reproduced. Among the inspected sources, no fully specified numerical worked pressure/thickness answer was found that can be compared to the app's netting pressure like for like. The numeric bottle example is documented but not forced into a comparison. No external pressure, CLT failure pressure, progressive/model-stop pressure, liner or dome validation is claimed.

## Internal default-input arithmetic (not external validation)

See [Russian guide](../docs/PRESSURE_VESSEL_EXPLAINED_RU.md), including the independent hand formulas and the default example. The reproducible script `verify_kaw_vessel.py` runs existing core/workflow methods:

| Quantity | Source of inputs | Hand (computed) | App | Difference |
|---|---|---|---|---|
| Nx [N/m] | app defaults p=10.0 MPa, R=100.0 mm | {number(pressure*radius/2)} | {number(cylinder_resultants(pressure,radius)[0])} | 0 absolute |
| Ny [N/m] | same defaults | {number(pressure*radius)} | {number(cylinder_resultants(pressure,radius)[1])} | 0 absolute |
| Netting p at balanced optimal ±θ [Pa] | 16 default plies; t={number(thickness)} m; existing dataset Xt={number(record.Xt)} Pa | {number(2*record.Xt*16*thickness/(3*radius))} | {number(study_result.netting_pressure_pa)} | {number(study_result.netting_pressure_pa-2*record.Xt*16*thickness/(3*radius))} Pa |

Run `python verification/verify_kaw_vessel.py`. Computed values are serialized without decimal formatting in `kaw_vessel_results.json`. The source PDFs and this note distinguish printed evidence from app-default predictions.
'''
    (ROOT/'verification/VERIFY_VESSEL_EXAMPLE.md').write_text(verification,encoding='utf-8')
    return {'default_material':record.name,'radius_m':radius,'working_pressure_pa':pressure,
            'loads':cylinder_resultants(pressure,radius).tolist(),'netting_angle_deg':NETTING_ANGLE_DEG,
            'study_thickness_m':16*thickness,'study_netting_pressure_pa':float(study_result.netting_pressure_pa),
            'study_first_ply_pressure_pa':float(study_result.first_ply_pressure_pa),'best_first_ply_pressure_pa':float(best[0]),
            'best_angle_deg':best[1],'current_first_ply_pressure_pa':float(current_result.first_ply_pressure_pa),
            'current_netting_pressure_pa':float(current_result.netting_pressure_pa),
            'current_hashin_first_pressure_pa':float(progressive.first_ply_load_factor),
            'current_model_stop_pressure_pa':float(progressive.last_ply_load_factor)}


if __name__=='__main__':
    result={'kaw':kaw_report(),'vessel':vessel_report()}
    (ROOT/'verification/kaw_vessel_results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result,indent=2,ensure_ascii=False))
