"""Interactive Classical Lamination Theory teaching and design screening app."""

from __future__ import annotations

import math

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from core import (
    StrengthAllowables, assemble_laminate_stiffness, compute_Q_matrix, engineering_constants,
    evaluate_failure, first_ply_mechanical_load_factor, hashin, recover_ply_surfaces,
    recover_thermal_response, temperature_change_from_reference, transform_Q, tsai_wu_load_factor,
)
from core.dome import cylinder_winding_angle_deg, dome_stations
from core.progressive import DegradationRules, progressive_failure
from core.vessel import NETTING_ANGLE_DEG, cylinder_resultants
from examples.spar_cap import MATERIAL_SOURCE, analyze_spar_cap
from materials import DEFAULT_MATERIALS
from workflow import (first_ply_limit, angle_ply_wall, assess_design, editor_to_layup, is_balanced, is_symmetric,
                      parse_layup, screen_cylinder)

try:
    from report import build_pdf_report
except ImportError:  # reportlab not installed: the app still runs without the PDF export
    build_pdf_report = None

st.set_page_config(page_title="Composite Laminate Design & Analysis Tool", page_icon="🧭", layout="wide")
st.markdown("""
<style>
  .block-container {max-width: 1360px; padding-top: 1.45rem; padding-bottom: 3rem;}
  .hero {background: linear-gradient(120deg, #102a43, #075f70); color: white;
    padding: 1.8rem 2rem; border-radius: 1.1rem; margin-bottom: 1.3rem;}
  .hero .eyebrow {font-size: .76rem; letter-spacing: .15em; font-weight: 700;
    color: #9fe1e7; margin-bottom: .55rem;}
  .hero h1 {color: white; font-size: clamp(2rem, 3.4vw, 3rem); line-height: 1.08;
    margin: 0 0 .7rem 0;}
  .hero p {color: #e5f3f5; font-size: 1.04rem; max-width: 66rem; margin: 0;}
  [data-testid="stMetric"] {background: white; border: 1px solid #dce9ee;
    border-radius: .9rem; padding: .85rem 1rem; box-shadow: 0 5px 18px #102a4309;}
  .stTabs [data-baseweb="tab-list"] {gap: .35rem; padding-bottom: .4rem;}
  .stTabs [data-baseweb="tab"] {border-radius: .65rem .65rem 0 0; padding: .65rem .8rem;}
  [data-testid="stSidebar"] {min-width: 330px;}
</style>
""", unsafe_allow_html=True)

DEFAULT_NAME = "Graphite/Epoxy (T300/5208)"
INPUT_KEYS = ("material_e1", "material_e2", "material_g12", "material_v12", "material_thickness",
              "strength_xt", "strength_xc", "strength_yt", "strength_yc", "strength_s")


def load_reference_properties() -> None:
    record = DEFAULT_MATERIALS.get(st.session_state.material_choice)
    if record is None:
        return
    values = (record.E1 / 1e9, record.E2 / 1e9, record.G12 / 1e9, record.v12,
              record.ply_thickness * 1e3, record.Xt / 1e6, record.Xc / 1e6,
              record.Yt / 1e6, record.Yc / 1e6, record.S / 1e6)
    st.session_state.update(zip(INPUT_KEYS, values))


if "material_choice" not in st.session_state:
    st.session_state.material_choice = DEFAULT_NAME
if "material_e1" not in st.session_state:
    load_reference_properties()
if "plies" not in st.session_state:
    st.session_state.plies = parse_layup("[0,45,-45,90]s", 0.125e-3)
if "editor_version" not in st.session_state:
    st.session_state.editor_version = 0

LOAD_KEYS = ("load_nx", "load_ny", "load_nxy", "load_mx", "load_my", "load_mxy")
LOAD_PRESETS = {
    "Axial tension (Nx = 100 kN/m)": (100.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    "In-plane shear (Nxy = 50 kN/m)": (0.0, 0.0, 50.0, 0.0, 0.0, 0.0),
    "Biaxial tension (Nx = Ny = 50 kN/m)": (50.0, 50.0, 0.0, 0.0, 0.0, 0.0),
    "Bending (Mx = 50 N·m/m)": (0.0, 0.0, 0.0, 50.0, 0.0, 0.0),
    "Custom - type your own values below": None,
}
for _key, _value in zip(LOAD_KEYS, LOAD_PRESETS["Axial tension (Nx = 100 kN/m)"]):
    st.session_state.setdefault(_key, _value)


def apply_load_preset() -> None:
    values = LOAD_PRESETS[st.session_state.load_preset]
    if values is not None:
        st.session_state.update(zip(LOAD_KEYS, values))


LAYUP_PRESETS = {"Unidirectional [0]₄": "[0,0]s", "Cross-ply [0/90]s": "[0,90]s",
                 "Quasi-isotropic [0/45/-45/90]s": "[0,45,-45,90]s", "Angle-ply [+45/-45]s": "[45,-45]s"}


def tidy(frame: pd.DataFrame) -> pd.DataFrame:
    """Hide floating-point noise (1e-16) and negative zeros in displayed tables."""
    numeric = frame.select_dtypes("number").columns
    frame[numeric] = frame[numeric].round(6) + 0.0
    return frame


def matrix_frame(matrix: np.ndarray, scale: float, labels: list[str]) -> pd.DataFrame:
    return tidy(pd.DataFrame(matrix / scale, index=labels, columns=labels))


def fmt(frame: pd.DataFrame, pattern: str, columns=None) -> dict:
    """Column formats for st.dataframe so tables show engineering precision, not raw floats."""
    names = columns if columns is not None else frame.select_dtypes("number").columns
    return {str(c): st.column_config.NumberColumn(str(c), format=pattern) for c in names}


def show_matrix(target, matrix: np.ndarray, scale: float, labels: list[str], pattern: str) -> None:
    frame = matrix_frame(matrix, scale, labels)
    target.dataframe(frame, width="stretch", column_config=fmt(frame, pattern))


def near_zero(value: float, scale: float) -> bool:
    return abs(value) <= max(1e-8 * scale, 1e-10)


def stack_plot(z: np.ndarray, layup: list[dict], names: list[str] | None = None) -> alt.Chart:
    hybrid = names is not None and len({ply["mat"] for ply in layup}) > 1
    short = lambda ply: names[ply["mat"]].split(" — ")[0].split("/")[0] if names else ""
    data = pd.DataFrame([{"Ply": i + 1, "z0": z[i] * 1e3, "z1": z[i + 1] * 1e3,
                          "Angle": f"{ply['theta']:g}°",
                          "Material": names[ply["mat"]] if names else "",
                          "Label": f"Ply {i+1}: {ply['theta']:g}°" + (f" · {short(ply)}" if hybrid else "")}
                         for i, ply in enumerate(layup)])
    data["x0"], data["x1"] = 0.0, 1.0
    data["mid"] = (data["z0"] + data["z1"]) / 2
    base = alt.Chart(data).encode(
        x=alt.X("x0:Q", scale=alt.Scale(domain=[0, 1]), axis=None),
        x2="x1:Q", y=alt.Y("z0:Q", title="z from mid-plane [mm]"), y2="z1:Q",
        color=alt.Color("Angle:N", scale=alt.Scale(scheme="pastel1"), legend=alt.Legend(title="Fibre angle")),
        tooltip=["Ply", "Angle", "Material", alt.Tooltip("z0:Q", title="Bottom z [mm]"),
                 alt.Tooltip("z1:Q", title="Top z [mm]")],
    )
    rectangles = base.mark_rect(stroke="white", strokeWidth=2)
    labels = alt.Chart(data).mark_text(color="black", fontSize=13).encode(
        x=alt.value(150), y=alt.Y("mid:Q", axis=None), text="Label:N")
    return (rectangles + labels).properties(height=max(260, min(560, 38 * len(layup))))


COMPONENTS = {"stress": ("σ₁", "σ₂", "τ₁₂"), "strain": ("εx", "εy", "γxy")}


def table_height(rows: int) -> int:
    """Show every row of a table up to ~20 rows without an inner scroll bar."""
    return min(35 * (rows + 1) + 3, 738)


def through_thickness_plot(response, kind: str) -> alt.Chart:
    rows = []
    for point in response.ply_surfaces:
        values = point.local_stress / 1e6 if kind == "stress" else point.global_strain * 1e6
        names = COMPONENTS[kind]
        for name, value in zip(names, values):
            rows.append({"ply": str(point.ply), "z_mm": point.z * 1e3,
                         "component": name, "value": float(value), "surface": point.surface})
    unit = "MPa" if kind == "stress" else "µε"
    return alt.Chart(pd.DataFrame(rows)).mark_line(point=True).encode(
        x=alt.X("value:Q", title=f"{kind.capitalize()} [{unit}]"),
        y=alt.Y("z_mm:Q", title="z from mid-plane [mm]"),
        color=alt.Color("component:N", title="Component",
                        scale=alt.Scale(domain=list(COMPONENTS[kind]), range=["#1f77b4", "#e07b22", "#2a9d5c"])),
        detail="ply:N",
        tooltip=[alt.Tooltip("ply:N", title="Ply"), alt.Tooltip("surface:N", title="Surface"),
                 alt.Tooltip("component:N", title="Component"),
                 alt.Tooltip("value:Q", title=f"Value [{unit}]", format=".4g"),
                 alt.Tooltip("z_mm:Q", title="z [mm]", format=".3f")],
    ).properties(height=370)


st.markdown("""
<div class="hero">
  <div class="eyebrow">CLASSICAL LAMINATION THEORY · BY ARTYOM</div>
  <h1>Composite Laminate Design &amp; Analysis</h1>
  <p>Predict a response, change the fibres or loads, and trace the result from material properties to laminate stiffness and first-ply screening.</p>
</div>
""", unsafe_allow_html=True)
st.caption("Educational CLT tool · editable inputs · cited reference data · first-ply screening, not certified design")

with st.sidebar:
    st.header("Model inputs")
    st.caption("Edit once; the mechanics tabs use the same inputs. Defaults give a working example, so you can start by just looking at the tabs.")
    with st.expander("1 · Material and ply", expanded=True):
        st.selectbox("Material dataset", [*DEFAULT_MATERIALS, "Custom material"],
                     key="material_choice", on_change=load_reference_properties)
        selected = DEFAULT_MATERIALS.get(st.session_state.material_choice)
        if selected and st.button("Reset to cited values"):
            load_reference_properties()
        e1 = st.number_input("E₁ [GPa]", min_value=0.001, key="material_e1",
                             help="Stiffness along the fibres (direction 1). Large for carbon fibre.")
        e2 = st.number_input("E₂ [GPa]", min_value=0.001, key="material_e2",
                             help="Stiffness across the fibres (direction 2). Dominated by the resin.")
        g12 = st.number_input("G₁₂ [GPa]", min_value=0.001, key="material_g12",
                              help="In-plane shear stiffness of one ply.")
        v12 = st.number_input("ν₁₂ [–]", min_value=0.0, key="material_v12",
                              help="Major Poisson ratio: contraction in direction 2 when stretched along the fibres.")
        thickness_mm = st.number_input("Default ply thickness [mm]", min_value=0.001, format="%.3f", key="material_thickness",
                                       help="Thickness of one ply. Each ply can still be changed in the Layup tab.")
    with st.expander("2 · Applied loads", expanded=True):
        st.caption("Forces and moments per unit width of the laminate. Pick a preset or type your own values.")
        st.selectbox("Load preset", list(LOAD_PRESETS), key="load_preset", on_change=apply_load_preset)
        nx = st.number_input("Nx [kN/m]", key="load_nx", help="Force along x per unit width. Positive = tension.")
        ny = st.number_input("Ny [kN/m]", key="load_ny", help="Force along y per unit width. Positive = tension.")
        nxy = st.number_input("Nxy [kN/m]", key="load_nxy", help="In-plane shear force per unit width.")
        mx = st.number_input("Mx [N·m/m]", key="load_mx", help="Bending moment per unit width. Positive Mx gives positive curvature κx (top face in tension).")
        my = st.number_input("My [N·m/m]", key="load_my", help="Bending moment per unit width that bends the plate in the y-direction.")
        mxy = st.number_input("Mxy [N·m/m]", key="load_mxy", help="Twisting moment per unit width.")
    with st.expander("3 · Strength inputs", expanded=False):
        st.caption("Literature reference strengths. Xt/Xc: along the fibres (tension/compression); Yt/Yc: across the fibres; S: in-plane shear.")
        xt = st.number_input("Xt [MPa]", min_value=0.001, key="strength_xt")
        xc = st.number_input("Xc [MPa]", min_value=0.001, key="strength_xc")
        yt = st.number_input("Yt [MPa]", min_value=0.001, key="strength_yt")
        yc = st.number_input("Yc [MPa]", min_value=0.001, key="strength_yc")
        shear = st.number_input("S [MPa]", min_value=0.001, key="strength_s")

material = {"E1": e1 * 1e9, "E2": e2 * 1e9, "G12": g12 * 1e9, "v12": v12}
if selected is not None:
    material.update(alpha1=selected.alpha1, alpha2=selected.alpha2, alpha12=0.0)
strengths = StrengthAllowables(*(value * 1e6 for value in (xt, xc, yt, yc, shear)))
loads = np.array([nx * 1e3, ny * 1e3, nxy * 1e3, mx, my, mxy], dtype=float)
ply_thickness_m = thickness_mm * 1e-3

# Per-ply materials: index 0 is the sidebar material, the others are the cited datasets.
MATERIAL_NAMES = ["Sidebar material", *DEFAULT_MATERIALS]
materials_list = [material] + [record.as_thermal_core_material() for record in DEFAULT_MATERIALS.values()]
strengths_list = [strengths] + [StrengthAllowables(**record.as_strengths()) for record in DEFAULT_MATERIALS.values()]
thermal_records = [selected, *DEFAULT_MATERIALS.values()]

values_edited = False
if selected:
    entered = np.array([e1, e2, g12, v12, xt, xc, yt, yc, shear])
    cited = np.array([selected.E1 / 1e9, selected.E2 / 1e9, selected.G12 / 1e9,
                      selected.v12, selected.Xt / 1e6, selected.Xc / 1e6,
                      selected.Yt / 1e6, selected.Yc / 1e6, selected.S / 1e6])
    values_edited = not np.allclose(entered, cited, rtol=1e-9, atol=1e-9)
    if values_edited:
        st.info("Some values differ from the cited material dataset. Current calculations use your edited inputs.")

if v12**2 * e2 / e1 >= 1:
    st.error("Inadmissible ply: ν₁₂² must be below E₁/E₂. Reduce ν₁₂ or E₂ in the sidebar.")
    st.stop()

try:
    stiffness = assemble_laminate_stiffness(st.session_state.plies, materials_list)
    response = recover_ply_surfaces(stiffness, st.session_state.plies, materials_list, loads)
    surface_strengths = [strengths_list[st.session_state.plies[point.ply - 1]["mat"]]
                         for point in response.ply_surfaces]
except (ValueError, np.linalg.LinAlgError) as error:
    stiffness = response = surface_strengths = None
    st.error(f"Current inputs cannot be analysed: {error}")

if stiffness is not None:
    checks = [evaluate_failure(point.local_stress, allow)
              for point, allow in zip(response.ply_surfaces, surface_strengths)]
    worst_r = min(tsai_wu_load_factor(point.local_stress, allow)
                  for point, allow in zip(response.ply_surfaces, surface_strengths))
    worst_util = max(check.maximum_stress_utilization for check in checks)
    summary_top = st.columns(3)
    summary_top[0].metric("Plies", len(st.session_state.plies))
    summary_top[1].metric("Thickness [mm]", f"{(stiffness.z[-1] - stiffness.z[0]) * 1e3:.3f}")
    summary_top[2].metric("Symmetric", "Yes" if is_symmetric(st.session_state.plies) else "No")
    summary_bottom = st.columns(2)
    summary_bottom[0].metric("Max Stress index", f"{worst_util:.3f}",
                             help="Largest stress/strength value over all plies and faces. 1.0 means a ply is at its limit.")
    summary_bottom[1].metric("Min Tsai–Wu strength ratio R", "No load" if math.isinf(worst_r) else f"{worst_r:.3f}",
                             help="R is the factor by which the entered loads can be scaled before Tsai–Wu reaches 1. R < 1 means the screening limit is already exceeded.")

    verdict_i, verdict_factor, verdict_criterion = first_ply_limit(response.ply_surfaces, surface_strengths)
    if math.isinf(verdict_factor):
        st.info("**Result in plain words:** no load is applied, so nothing is stressed. Choose a load preset in the sidebar.")
    else:
        vp = response.ply_surfaces[verdict_i]
        where = f"Ply {vp.ply} ({vp.angle_deg:g}°, {vp.surface.lower()} face)"
        if verdict_factor >= 1:
            st.success(f"**Result in plain words:** below the screening limit. You could multiply the loads by about "
                       f"**{verdict_factor:.2f}** before the first ply reaches its limit: {where}, according to the {verdict_criterion} criterion.")
        else:
            st.error(f"**Result in plain words:** already beyond the screening limit. At these loads {where} exceeds it according to the "
                     f"{verdict_criterion} criterion; the loads must be reduced to **{verdict_factor:.2f}×** the entered values to stay below it.")

    if build_pdf_report is not None:
        report_bytes = build_pdf_report(
            material_name=st.session_state.material_choice + (" (edited values)" if values_edited else ""), material=material, strengths=strengths,
            layup=st.session_state.plies, material_names=MATERIAL_NAMES, loads=loads, stiffness=stiffness,
            constants=engineering_constants(stiffness), response=response, surface_strengths=surface_strengths,
            first_ply=(verdict_i, verdict_factor, verdict_criterion))
        st.download_button("Download a PDF report of this analysis", report_bytes, file_name="laminate_analysis_report.pdf",
                           mime="application/pdf", help="Inputs, layup, A/B/D, engineering constants, mid-plane response and ply-by-ply failure screening.")

with st.container(border=True):
    st.markdown("**How to use this tool: four steps, left to right**")
    how_cols = st.columns(4)
    how_cols[0].markdown("**① Material**  \nPick or edit the fibre/resin data in the sidebar. See Q in the *1 · Material* tab.")
    how_cols[1].markdown("**② Layup**  \nBuild the stack in the *2 · Layup* tab: angle, thickness and material of every ply.")
    how_cols[2].markdown("**③ Load**  \nChoose a load preset in the sidebar (or type forces and moments).")
    how_cols[3].markdown("**④ Read the result**  \nStiffness in *3 · ABD*, strains and stresses in *4 · Response*, the first-ply check in *5 · Failure*. The coloured box above sums it up; the PDF button saves a report.")

tabs = st.tabs(["Start here", "1 · Material & Q", "2 · Layup & Q̄", "3 · ABD", "4 · Response",
                "5 · Failure", "Compare", "Pressure vessel", "Manufacturing", "Applications", "Verification"])

with tabs[0]:
    st.subheader("A small experiment before the matrices")
    st.write("The 1-axis follows the fibres. Before opening the detailed results, predict what happens when all four plies rotate away from a fixed x-direction tensile load.")
    prediction = st.radio("From 0° to 90°, will x-direction extensional stiffness A₁₁…",
                          ["Increase", "Decrease", "Stay the same"], index=None, horizontal=True)
    if st.button("Check my prediction"):
        if prediction is None:
            st.info("Choose a prediction first.")
        elif prediction == "Decrease":
            st.success("Correct. At 90°, the weaker transverse ply direction carries the x-load.")
        else:
            st.warning("Try the angle slider: x-aligned fibres resist x-tension much more strongly than transverse fibres for these materials.")
    study_angle = st.slider("Rotate every ply [deg]", 0, 90, 0, 5, key="study_angle")
    study_load = np.array([100e3, 0, 0, 0, 0, 0], dtype=float)
    study = [assess_design(f"{a}°", f"[{a},{a}]s", ply_thickness_m, material, strengths, study_load)
             for a in range(0, 91, 10)]
    current_study = assess_design(f"{study_angle}°", f"[{study_angle},{study_angle}]s",
                                  ply_thickness_m, material, strengths, study_load)
    st.caption("Controlled comparison: four plies of equal thickness, the selected material, and fixed Nx = 100 kN/m. Sidebar loads do not change this teaching experiment.")
    study_cards = st.columns(3)
    study_cards[0].metric("A₁₁ [MN/m]", f"{current_study.A11 / 1e6:.2f}")
    study_cards[1].metric("x strain [µε]", f"{current_study.epsilon_x * 1e6:,.0f}")
    study_cards[2].metric("Max Stress index", f"{current_study.max_utilization:.3f}")
    study_data = pd.DataFrame([{"angle_deg": int(d.name[:-1]), "a11_mn_per_m": d.A11 / 1e6,
                                "ex_microstrain": d.epsilon_x * 1e6} for d in study])
    graph_left, graph_right = st.columns(2)
    graph_left.altair_chart(alt.Chart(study_data).mark_line(point=True, strokeWidth=3, color="#087f8c").encode(
        x=alt.X("angle_deg:Q", title="Fibre angle [deg]", scale=alt.Scale(domain=[0, 90])),
        y=alt.Y("a11_mn_per_m:Q", title="A₁₁ [MN/m]", scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("angle_deg:Q", title="Angle [deg]"),
                 alt.Tooltip("a11_mn_per_m:Q", title="A₁₁ [MN/m]", format=".2f")]
    ).properties(height=270), width="stretch")
    graph_right.altair_chart(alt.Chart(study_data).mark_line(point=True, strokeWidth=3, color="#cf7b22").encode(
        x=alt.X("angle_deg:Q", title="Fibre angle [deg]", scale=alt.Scale(domain=[0, 90])),
        y=alt.Y("ex_microstrain:Q", title="εx⁰ [µε]", scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("angle_deg:Q", title="Angle [deg]"),
                 alt.Tooltip("ex_microstrain:Q", title="εx⁰ [µε]", format=".0f")]
    ).properties(height=270), width="stretch")
    st.markdown("**Trace the cause:** fibre direction → Q̄ of each ply → laminate A → compliance a = A⁻¹ → εx = a₁₁·Nx. "
                "In the off-axis stacks [θ,θ]s every ply has the same +θ, so the laminate also shears under Nx (A₁₆ ≠ 0) "
                "and εx grows faster than 1/A₁₁ alone suggests.")

with tabs[1]:
    st.subheader("Material → reduced stiffness Q")
    st.info("**Step 1 · What to do:** nothing is required. Look at Q for the sidebar material, then change E₁ or E₂ in the sidebar and watch Q follow. "
            "Plies can use other datasets too (see the Layup tab); this tab shows the sidebar material only.")
    if selected:
        st.markdown(f"**Source for elastic and strength inputs:** [{selected.reference}]({selected.source_url})")
        st.caption(selected.reference_note)
    else:
        st.warning("Custom values have no recorded source. Cite your data before making engineering claims from them.")
    nu21 = v12 * material["E2"] / material["E1"]
    q = compute_Q_matrix(material["E1"], material["E2"], material["G12"], material["v12"])
    st.metric("Minor Poisson ratio ν₂₁", f"{nu21:.5f}")
    st.caption("Q in GPa, material axes 1–2:")
    show_matrix(st, q, 1e9, ["1", "2", "12"], "%.2f")
    with st.expander("Explain each term of Q", expanded=True):
        st.latex(r"\nu_{21}=\nu_{12}E_2/E_1,\qquad \Delta=1-\nu_{12}\nu_{21}")
        st.latex(r"Q_{11}=E_1/\Delta,\quad Q_{22}=E_2/\Delta,\quad Q_{12}=\nu_{12}E_2/\Delta,\quad Q_{66}=G_{12}")
        st.write("Q links local plane stress [σ₁, σ₂, τ₁₂] to local strain [ε₁, ε₂, γ₁₂]. γ₁₂ is engineering shear strain.")
    st.write("Prediction: raising E₁ increases Q₁₁ most strongly. It does not automatically increase bending stiffness equally for every layup because ply position also matters.")

with tabs[2]:
    st.subheader("Orientation and laminate builder")
    st.info("**Step 2 · What to do:** (a) click a ready-made layup below, or type your own; (b) fine-tune any ply in the table: angle, thickness and **Material** "
            "(mixing materials gives a hybrid laminate); (c) check the picture of the stack. Use the **+** under the table to add a ply, or select a row and press Delete to remove one.")
    st.write("A positive angle rotates the fibre 1-axis counter-clockwise from global x. The stack list runs from z = −h/2 to +h/2.")
    angle = st.slider("Inspect one ply angle [deg]", -90, 90, 45)
    show_matrix(st, transform_Q(q, angle), 1e9, ["x", "y", "xy"], "%.2f")
    st.caption("Q̄ is shown in GPa. At 0°, Q̄=Q; off-axis plies can have nonzero Q̄₁₆ and Q̄₂₆.")
    orientation = pd.DataFrame([{"Angle": f"{a}°", "Q̄11 [GPa]": transform_Q(q, a)[0, 0] / 1e9,
                                 "Q̄22 [GPa]": transform_Q(q, a)[1, 1] / 1e9} for a in (0, 45, 90)])
    st.dataframe(orientation, width="stretch", hide_index=True, column_config=fmt(orientation, "%.2f"))
    st.write("Prediction: Q̄₁₁ falls as fibres rotate from 0° toward 90° for these reference materials.")
    st.markdown("**Ready-made layups** (they set every ply to the sidebar material)")
    preset_cols = st.columns(len(LAYUP_PRESETS))
    for column, (label, text) in zip(preset_cols, LAYUP_PRESETS.items()):
        if column.button(label, key=f"preset_{text}"):
            st.session_state.plies = parse_layup(text, ply_thickness_m)
            st.session_state.editor_version += 1
            st.rerun()
    quick = st.text_input("Or type a layup (angles in degrees, separated by comma or slash; s mirrors the listed half)", "[0,45,-45,90]s")
    actions = st.columns(3)
    if actions[0].button("Apply layup"):
        try:
            st.session_state.plies = parse_layup(quick, ply_thickness_m)
            st.session_state.editor_version += 1
            st.rerun()
        except ValueError as error:
            st.error(str(error))
    if actions[1].button("Reverse stack"):
        st.session_state.plies = list(reversed(st.session_state.plies))
        st.session_state.editor_version += 1
        st.rerun()
    if actions[2].button("Mirror stack"):
        if len(st.session_state.plies) > 50:
            st.error("Mirroring would exceed the 100-ply limit")
        else:
            st.session_state.plies += list(reversed(st.session_state.plies))
            st.session_state.editor_version += 1
            st.rerun()
    editor = pd.DataFrame([{"Angle [deg]": ply["theta"], "Thickness [mm]": ply["t"] * 1e3,
                            "Material": MATERIAL_NAMES[ply["mat"]]}
                           for ply in st.session_state.plies])
    st.caption("Ply table, bottom (−h/2) to top (+h/2). Double-click a cell to edit it.")
    changed = st.data_editor(
        editor, num_rows="dynamic", hide_index=True, width="stretch",
        key=f"ply_editor_{st.session_state.editor_version}",
        column_config={
            "Angle [deg]": st.column_config.NumberColumn("Angle [deg]", default=0.0, step=5.0,
                                                         help="Fibre angle from the global x-axis, counter-clockwise positive."),
            "Thickness [mm]": st.column_config.NumberColumn("Thickness [mm]", default=float(thickness_mm), min_value=0.001,
                                                            format="%.3f", help="Thickness of this ply."),
            "Material": st.column_config.SelectboxColumn("Material", options=MATERIAL_NAMES, default=MATERIAL_NAMES[0],
                                                         required=True, help="Sidebar material or one of the cited datasets."),
        })
    if not changed.equals(editor):
        try:
            st.session_state.plies = editor_to_layup(changed.to_dict("records"), MATERIAL_NAMES)
            st.rerun()
        except ValueError as error:
            st.error(str(error))
    if stiffness is not None:
        st.altair_chart(stack_plot(stiffness.z, st.session_state.plies, MATERIAL_NAMES), width="stretch")
    with st.expander("In plain words: what do these numbers mean?"):
        st.markdown("- **Q** describes one ply with the fibres along its own 1-axis. **Q̄** is the same ply seen from the laminate's x-axis after rotating it by its angle.\n"
                    "- At 0° the ply is stiff along x; at 90° it is soft along x and stiff along y. At ±45° it resists shear well.\n"
                    "- Off-axis plies get non-zero Q̄₁₆/Q̄₂₆: pulling the ply also shears it. A **balanced** stack (each +θ matched by −θ) cancels this in A; "
                    "a **symmetric** stack makes B = 0. Bend–twist terms D₁₆/D₂₆ usually remain.")

with tabs[3]:
    st.subheader("Layup → A, B and D")
    st.info("**Step 3 · What to do:** read the three matrices. Then go back to the Layup tab, press **Reverse stack** or change an angle, and see which numbers move.")
    if stiffness is not None:
        st.latex(r"A_{ij}=\sum_k\bar Q_{ij}^{(k)}\Delta z_k,\quad B_{ij}=\tfrac12\sum_k\bar Q_{ij}^{(k)}\Delta(z_k^2),\quad D_{ij}=\tfrac13\sum_k\bar Q_{ij}^{(k)}\Delta(z_k^3)")
        columns = st.columns(3)
        for column, title, matrix, divisor, pattern in zip(columns, ("A [MN/m]", "B [N]", "D [N·m]"),
                                                            (stiffness.A, stiffness.B, stiffness.D), (1e6, 1, 1),
                                                            ("%.2f", "%.1f", "%.3f")):
            column.markdown(f"**{title}**")
            show_matrix(column, matrix, divisor, ["x", "y", "xy"], pattern)
        constants = engineering_constants(stiffness)
        st.markdown("**Equivalent engineering constants** (the laminate treated as a homogeneous plate of thickness h)")
        const_cols = st.columns(6)
        const_cols[0].metric("$E_x$ [GPa]", f"{constants.Ex / 1e9:.2f}")
        const_cols[1].metric("$E_y$ [GPa]", f"{constants.Ey / 1e9:.2f}")
        const_cols[2].metric("$G_{xy}$ [GPa]", f"{constants.Gxy / 1e9:.2f}")
        const_cols[3].metric("$\\nu_{xy}$", f"{constants.nu_xy:.3f}")
        const_cols[4].metric("$E_x$ flexural [GPa]", f"{constants.Ex_flex / 1e9:.2f}")
        const_cols[5].metric("$E_y$ flexural [GPa]", f"{constants.Ey_flex / 1e9:.2f}")
        if not near_zero(float(np.max(np.abs(stiffness.B))), float(np.max(np.abs(stiffness.A)) * (stiffness.z[-1] - stiffness.z[0]))):
            ex_restrained = 1.0 / ((stiffness.z[-1] - stiffness.z[0]) * np.linalg.inv(stiffness.A)[0, 0])
            st.warning(f"B ≠ 0: these are apparent constants with curvature free to develop (from ABD⁻¹). "
                       f"With bending restrained, Ex = 1/(h·(A⁻¹)₁₁) = {ex_restrained / 1e9:.2f} GPa.")
        st.caption("From the compliance a, d = blocks of ABD⁻¹: membrane Ex = 1/(h·a₁₁), Ey = 1/(h·a₂₂), Gxy = 1/(h·a₆₆), νxy = −a₁₂/a₁₁; "
                   "flexural Ex = 12/(h³·d₁₁). Membrane and flexural values differ because D weights outer plies more.")
        with st.expander("Full ABD and ply-interface positions"):
            abd = tidy(pd.DataFrame(stiffness.ABD, index=["Nx", "Ny", "Nxy", "Mx", "My", "Mxy"],
                                    columns=["εx", "εy", "γxy", "κx", "κy", "κxy"]))
            st.dataframe(abd, width="stretch", column_config=fmt(abd, "%.4g"))
            st.caption("Mixed SI block units: A [N/m], B [N], D [N·m].")
            st.dataframe(pd.DataFrame({"Interface": range(len(stiffness.z)), "z [mm]": stiffness.z * 1e3}),
                         hide_index=True, width="stretch", column_config=fmt(None, "%.3f", ["z [mm]"]))
        b_scale = np.max(np.abs(stiffness.A)) * (stiffness.z[-1] - stiffness.z[0])
        if near_zero(float(np.max(np.abs(stiffness.B))), float(b_scale)):
            st.success("B ≈ 0: membrane forces do not create extension–bending coupling in this CLT model.")
        else:
            st.info("B ≠ 0: membrane loading can also create curvature. Reverse the stack and inspect the sign of B.")
        a_scale = float(np.max(np.abs(stiffness.A)))
        if near_zero(float(max(abs(stiffness.A[0, 2]), abs(stiffness.A[1, 2]))), a_scale):
            st.write("A₁₆ and A₂₆ ≈ 0: little in-plane extension–shear coupling.")
        else:
            st.write("A₁₆/A₂₆ are nonzero: normal and shear membrane responses are coupled.")
        d_scale = float(np.max(np.abs(stiffness.D)))
        if near_zero(float(max(abs(stiffness.D[0, 2]), abs(stiffness.D[1, 2]))), d_scale):
            st.write("D₁₆ and D₂₆ ≈ 0: no bend–twist coupling.")
        else:
            st.write(f"D₁₆/D₂₆ are nonzero (D₁₆/D₁₁ = {stiffness.D[0, 2] / stiffness.D[0, 0]:.3f}): bending also produces some twist. "
                     "Balanced symmetric stacks with ±θ plies keep this term; \"quasi-isotropic\" describes A only, not D.")
        with st.expander("In plain words: A, B and D"):
            st.markdown("- **A** is in-plane stiffness: how much force per unit width gives how much stretch. Bigger A₁₁ = stiffer along x.\n"
                        "- **B** couples stretching and bending. For a symmetric stack B = 0, so pulling does not bend the plate.\n"
                        "- **D** is bending stiffness. It grows fast with distance from the mid-plane, so outer plies matter most.")
        st.caption(f"Balanced (each +θ ply matched by an equal −θ ply of the same material): {'yes' if is_balanced(st.session_state.plies) else 'no'}. A₁₁/A₂₂ = {stiffness.A[0,0]/stiffness.A[1,1]:.3g}; values above one indicate greater x-direction extensional stiffness.")

with tabs[4]:
    st.subheader("ABD and applied loads → strain, curvature and ply stress")
    st.info("**Step 4 · What to do:** change the load preset in the sidebar and watch the strains, curvature and the stress in each ply change. "
            "σ₁ is stress along the fibres, σ₂ across them, τ₁₂ in shear.")
    if response is not None:
        st.latex(r"\begin{bmatrix}\epsilon^0\\\kappa\end{bmatrix}=[ABD]^{-1}\begin{bmatrix}N\\M\end{bmatrix},\qquad \epsilon(z)=\epsilon^0+z\kappa")
        left, right = st.columns(2)
        left.dataframe(tidy(pd.DataFrame({"Mid-plane strain [µε]": response.midplane_strain * 1e6},
                                         index=["εx⁰", "εy⁰", "γxy⁰"])), width="stretch",
                       column_config=fmt(None, "%.1f", ["Mid-plane strain [µε]"]))
        right.dataframe(tidy(pd.DataFrame({"Curvature [1/m]": response.curvature},
                                          index=["κx", "κy", "κxy"])), width="stretch",
                        column_config=fmt(None, "%.4f", ["Curvature [1/m]"]))
        st.write("Strain varies linearly through the thickness, ε(z) = ε⁰ + zκ, with z measured upward from the mid-plane; positive κx (from positive Mx) puts the top face in tension. "
                 "Ply stresses come from rotating the global strain into each ply's fibre axes and applying Q.")
        surfaces = pd.DataFrame([{"Ply": p.ply, "Angle [deg]": p.angle_deg, "Face": p.surface,
                                  "z [mm]": p.z * 1e3, "ε₁ [µε]": p.local_strain[0] * 1e6,
                                  "ε₂ [µε]": p.local_strain[1] * 1e6, "γ₁₂ [µε]": p.local_strain[2] * 1e6,
                                  "σ₁ [MPa]": p.local_stress[0] / 1e6,
                                  "σ₂ [MPa]": p.local_stress[1] / 1e6,
                                  "τ₁₂ [MPa]": p.local_stress[2] / 1e6}
                                 for p in response.ply_surfaces])
        surfaces = tidy(surfaces)
        st.dataframe(surfaces, hide_index=True, width="stretch", height=table_height(len(surfaces)),
                     column_config={**fmt(None, "%.3f", ["z [mm]"]), **fmt(None, "%.0f", ["ε₁ [µε]", "ε₂ [µε]", "γ₁₂ [µε]"]),
                                    **fmt(None, "%.2f", ["σ₁ [MPa]", "σ₂ [MPa]", "τ₁₂ [MPa]"])})
        st.download_button("Download ply-surface results (CSV)", surfaces.to_csv(index=False).encode("utf-8-sig"),
                           file_name="ply_surface_response.csv", mime="text/csv")
        plot_left, plot_right = st.columns(2)
        plot_left.altair_chart(through_thickness_plot(response, "stress"), width="stretch")
        plot_right.altair_chart(through_thickness_plot(response, "strain"), width="stretch")
        st.caption("Each line segment is one ply. Global strains εx, εy, γxy are continuous through the thickness; fibre-axis stresses σ₁, σ₂, τ₁₂ change at ply interfaces because ply stiffness and ply axes change.")
        with st.expander("In plain words: strain and stress"):
            st.markdown("- **Strain** is how much the laminate stretches or bends; the whole stack deforms together, so the global strain varies linearly (a straight line) through the thickness.\n"
                        "- **Stress** depends on each ply's own stiffness, so it can jump from ply to ply even where strain is continuous.\n"
                        "- Stiff plies (fibres along the load) attract the most stress.")

with tabs[5]:
    st.subheader("Local ply stress → first-ply screening")
    st.info("**Step 5 · What to do:** find the row with the largest index (or the smallest R) and read the load factor below the table. "
            "An index below 1 means the ply is below its first-ply limit for these inputs; a load factor above 1 means the loads could grow by that factor.")
    if response is not None:
        st.write("Maximum Stress compares each stress component with its own tension/compression or shear strength. Tsai–Wu combines all components in one quadratic polynomial.")
        st.latex(r"FI=F_1\sigma_1+F_2\sigma_2+F_{11}\sigma_1^2+F_{22}\sigma_2^2+2F_{12}\sigma_1\sigma_2+F_{66}\tau_{12}^2")
        st.caption("F₁₂ = −0.5√(F₁₁F₂₂) (Tsai–Hahn) is an assumption, not measured interaction data.")
        st.write("**Hashin** (plane-stress, Hashin-1980-inspired initiation criterion) separates four modes and names the active one: fibre tension FT = (σ₁/Xt)² + (τ₁₂/S)²; fibre compression "
                 "FC = (σ₁/Xc)²; matrix tension MT = (σ₂/Yt)² + (τ₁₂/S)²; matrix compression "
                 "MC = (σ₂/2Sₜ)² + [(Yc/2Sₜ)² − 1]σ₂/Yc + (τ₁₂/S)².")
        st.caption("Parameters: Xt, Xc, Yt, Yc, S₁₂, Sₜ (= S₂₃) and α. Shear contribution: α = 1 in fibre tension (the Hashin 1980 form; a chosen setting "
                   "that should be validated with combined σ₁–τ₁₂ tests; α = 0 is the Hashin–Rotem-type alternative), the full (τ₁₂/S)² in both matrix modes, none in "
                   "fibre compression. Plane stress drops σ₃, τ₁₃, τ₂₃, so interlaminar failure is not assessed. Sₜ is not in the five allowables: "
                   "Sₜ = Yc/(2·tan 53°) is assumed (a Mohr–Coulomb value for a typical 53° fracture angle, not measured S₂₃). "
                   "Hashin R is the strength ratio from solving index(R·σ) = 1. Hashin is reported next to Max Stress and Tsai–Wu; "
                   "the first-ply screen and load factor below still use Max Stress and Tsai–Wu only.")
        st.info("FI is a quadratic index, so FI = 0.5 does **not** mean 50% of the failure load. Use the strength ratio R "
                "(the load scale at which FI = 1; if the linear terms vanish, R = 1/√FI) to compare with the linear Max Stress index, where 1/index is the load scale.")
        rows = []
        for point, check, allow in zip(response.ply_surfaces, checks, surface_strengths):
            rows.append({"Ply": point.ply, "Face": point.surface,
                         "Material": MATERIAL_NAMES[st.session_state.plies[point.ply - 1]["mat"]],
                         "Fibre σ₁/X": abs(point.local_stress[0]) / (allow.Xt if point.local_stress[0] >= 0 else allow.Xc),
                         "Transverse σ₂/Y": abs(point.local_stress[1]) / (allow.Yt if point.local_stress[1] >= 0 else allow.Yc),
                         "Shear |τ₁₂|/S": abs(point.local_stress[2]) / allow.S,
                         "Max Stress index": check.maximum_stress_utilization,
                         "Controlling mode": check.maximum_stress_mode,
                         "Tsai–Wu FI": check.tsai_wu_index,
                         "Tsai–Wu R": tsai_wu_load_factor(point.local_stress, allow),
                         "Hashin active mode": check.hashin_mode,
                         "Hashin index": check.hashin_index,
                         "Hashin R": hashin(point.local_stress, allow).load_factor,
                         "Screen": "Exceeds limit" if max(check.maximum_stress_utilization, check.tsai_wu_index) >= 1 else "Below limit"})
        ratio_cols = ["Fibre σ₁/X", "Transverse σ₂/Y", "Shear |τ₁₂|/S", "Max Stress index", "Tsai–Wu FI", "Tsai–Wu R",
                      "Hashin index", "Hashin R"]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=table_height(len(rows)),
                     column_config={c: st.column_config.NumberColumn(c, format="%.3f") for c in ratio_cols})
        critical_i, factor, criterion = first_ply_limit(response.ply_surfaces, surface_strengths)
        result_left, result_mid, result_right = st.columns(3)
        if math.isfinite(factor):
            critical = response.ply_surfaces[critical_i]
            result_left.metric("First-ply location", f"Ply {critical.ply}, {critical.surface.lower()} face")
            result_mid.metric("Controlling criterion", criterion)
        else:
            result_left.metric("First-ply location", "No load")
            result_mid.metric("Controlling criterion", "—")
        result_right.metric("Proportional first-ply load factor", "No load" if math.isinf(factor) else f"{factor:.3f}")
        st.caption("The load factor scales all six entered load components together until either criterion first reaches 1.")
        with st.expander("In plain words: how to read this table"):
            st.markdown("- Each index compares a stress with the strength in the same direction. **1.0 = at the limit.**\n"
                        "- **Max Stress** checks the three directions separately. **Tsai–Wu** combines them in one quadratic expression, so stresses in different directions interact.\n"
                        "- **Load factor** answers: by how much can I multiply all loads before the first ply reaches its limit? Above 1 = spare capacity; below 1 = already beyond.\n"
                        "- This is first-ply screening. It does not model progressive damage.")

        with st.container(border=True):
            st.markdown("**Thermal preload: cure cooling and cryogenic temperature**")
            active_materials = sorted({ply["mat"] for ply in st.session_state.plies})
            thermal_ready = all(thermal_records[index] is not None for index in active_materials)
            if not thermal_ready:
                st.warning("Thermal results are unavailable for an UNSOURCED custom material. Select a cited material dataset before using this block.")
            else:
                thermal_rows = []
                for index in active_materials:
                    record = thermal_records[index]
                    thermal_rows.append({
                        "Material": MATERIAL_NAMES[index],
                        "α₁ [µm/(m·K)]": record.alpha1 * 1e6,
                        "α₂ [µm/(m·K)]": record.alpha2 * 1e6,
                        "α₁₂ [µm/(m·K)]": 0.0,
                        "Reference [°C]": record.thermal_reference_temperature_c,
                        "Reference basis": record.thermal_reference_basis,
                    })
                thermal_frame = pd.DataFrame(thermal_rows)
                st.dataframe(thermal_frame, hide_index=True, width="stretch",
                             column_config={name: st.column_config.NumberColumn(name, format="%.3f")
                                            for name in ("α₁ [µm/(m·K)]", "α₂ [µm/(m·K)]",
                                                         "α₁₂ [µm/(m·K)]", "Reference [°C]")})

                input_cols = st.columns(3)
                thermal_case = input_cols[0].selectbox(
                    "Thermal case",
                    ["Direct ΔT", "Cool from reference to final temperature"],
                    key="thermal_case",
                )
                direct_delta = input_cols[1].number_input(
                    "ΔT [°C] (user-selected)", value=-100.0, step=10.0, key="thermal_delta_t"
                )
                final_temperature = input_cols[2].number_input(
                    "Chosen final / cryogenic temperature [°C]", value=-196.0, step=10.0,
                    key="thermal_final_temperature",
                )
                combine_mechanical = st.checkbox(
                    "Add the sidebar mechanical loads to the displayed ply stresses",
                    value=True, key="thermal_combine_mechanical",
                )

                if thermal_case == "Direct ΔT":
                    temperature_changes = float(direct_delta)
                    active_changes = [float(direct_delta)] * len(active_materials)
                else:
                    temperature_changes = np.zeros(len(materials_list), dtype=float)
                    for index, record in enumerate(thermal_records):
                        if record is not None:
                            temperature_changes[index] = temperature_change_from_reference(
                                record.thermal_reference_temperature_c, final_temperature
                            )
                    active_changes = [temperature_changes[index] for index in active_materials]

                try:
                    residual = recover_thermal_response(
                        stiffness, st.session_state.plies, materials_list, temperature_changes
                    )
                    displayed = recover_thermal_response(
                        stiffness, st.session_state.plies, materials_list, temperature_changes,
                        loads if combine_mechanical else None,
                    )
                    thermal_index, thermal_factor, thermal_criterion = first_ply_mechanical_load_factor(
                        residual, response, surface_strengths
                    )
                except (ValueError, np.linalg.LinAlgError) as error:
                    st.error(f"Thermal case cannot be analysed: {error}")
                else:
                    direct_label = (f"{active_changes[0]:.1f}" if np.ptp(active_changes) < 1e-12
                                    else f"{min(active_changes):.1f} to {max(active_changes):.1f}")
                    residual_max = max(abs(point.local_stress[1]) for point in residual.ply_surfaces) / 1e6
                    thermal_metrics = st.columns(3)
                    thermal_metrics[0].metric("Active ΔT [°C]", direct_label)
                    thermal_metrics[1].metric("Max residual |σ₂| [MPa]", f"{residual_max:.2f}")
                    if math.isfinite(thermal_factor):
                        factor_value = f"{thermal_factor:.3f}"
                        factor_delta = (f"{thermal_factor / factor:.3f}× vs mechanical-only"
                                        if math.isfinite(factor) and factor > 0 else None)
                    else:
                        factor_value, factor_delta = "No mechanical load", None
                    thermal_metrics[2].metric("First-ply factor with thermal preload", factor_value,
                                              delta=factor_delta, delta_color="off")

                    thermal_stress_rows = []
                    for residual_point, displayed_point in zip(residual.ply_surfaces, displayed.ply_surfaces):
                        row = {
                            "Ply": residual_point.ply,
                            "Face": residual_point.surface,
                            "Angle [deg]": residual_point.angle_deg,
                            "Residual σ₁ [MPa]": residual_point.local_stress[0] / 1e6,
                            "Residual σ₂ [MPa]": residual_point.local_stress[1] / 1e6,
                            "Residual τ₁₂ [MPa]": residual_point.local_stress[2] / 1e6,
                        }
                        if combine_mechanical:
                            row.update({
                                "Combined σ₁ [MPa]": displayed_point.local_stress[0] / 1e6,
                                "Combined σ₂ [MPa]": displayed_point.local_stress[1] / 1e6,
                                "Combined τ₁₂ [MPa]": displayed_point.local_stress[2] / 1e6,
                            })
                        thermal_stress_rows.append(row)
                    thermal_stress_frame = pd.DataFrame(thermal_stress_rows)
                    st.dataframe(thermal_stress_frame, hide_index=True, width="stretch",
                                 height=table_height(len(thermal_stress_frame)),
                                 column_config=fmt(thermal_stress_frame, "%.3f"))
                    critical_thermal = residual.ply_surfaces[thermal_index]
                    st.caption(
                        f"The thermal-preload factor holds residual stress fixed and scales only the sidebar mechanical loads; "
                        f"control: ply {critical_thermal.ply}, {critical_thermal.surface.lower()} face, {thermal_criterion}. "
                        "The direct case applies one ΔT to every ply; the reference-to-final case uses each material's listed reference temperature."
                    )

                cited_records = []
                for index in active_materials:
                    record = thermal_records[index]
                    if record.name not in cited_records:
                        cited_records.append(record.name)
                        st.markdown(
                            f"{record.name}: [CTE source]({record.cte_source_url}); "
                            f"[reference-temperature source]({record.temperature_source_url})."
                        )
                st.caption("Moisture, creep, and temperature-dependent properties are not modelled. Cure chemistry and chemical shrinkage are also excluded.")

with tabs[6]:
    st.subheader("Compare candidate layups under the current material and loads")
    st.info("**What to do:** type 2–5 layups, one per line, and compare stiffness, stress and load factor side by side. "
            "These candidates use the sidebar material for every ply; mixed-material stacks are built in the Layup tab.")
    st.write("Enter 2–5 layups, one per line. Thickness is the same editable ply thickness for every candidate. All candidates use the current six-component load vector.")
    candidates_text = st.text_area("Candidate layups", "[0,90]s\n[0,45,-45,90]s\n[0,0,45,-45,90]s", height=125)
    candidates = [line.strip() for line in candidates_text.splitlines() if line.strip()]
    if not 2 <= len(candidates) <= 5:
        st.error("Enter between two and five layups.")
    else:
        try:
            designs = [assess_design(f"Design {i+1}", text, ply_thickness_m, material, strengths, loads)
                       for i, text in enumerate(candidates)]
        except (ValueError, np.linalg.LinAlgError) as error:
            st.error(f"Candidate comparison could not be calculated: {error}")
        else:
            comparison = pd.DataFrame([{"Design": d.name, "Layup": d.layup,
                                        "Plies": d.plies, "Thickness [mm]": d.thickness_m * 1e3,
                                        "A₁₁ [MN/m]": d.A11 / 1e6, "D₁₁ [N·m]": d.D11,
                                        "max |B| [N]": d.B_norm, "εx⁰ [µε]": d.epsilon_x * 1e6,
                                        "Max Stress index": d.max_utilization,
                                        "Min Tsai–Wu R": d.min_tsai_wu_ratio,
                                        "First-ply load factor": d.first_ply_load_factor,
                                        "First-ply location": (f"Ply {d.critical_ply}, {d.critical_surface.lower()}"
                                                              if d.critical_ply is not None else "No load"),
                                        "Controlling criterion": d.critical_criterion}
                                       for d in designs])
            comparison = tidy(comparison)
            st.dataframe(comparison, hide_index=True, width="stretch",
                         column_config={**fmt(None, "%.3f", ["Thickness [mm]", "D₁₁ [N·m]", "Max Stress index", "Min Tsai–Wu R", "First-ply load factor"]),
                                        **fmt(None, "%.2f", ["A₁₁ [MN/m]"]), **fmt(None, "%.1f", ["max |B| [N]"]),
                                        **fmt(None, "%.0f", ["εx⁰ [µε]"])})
            st.download_button("Download candidate comparison (CSV)", comparison.to_csv(index=False).encode("utf-8-sig"),
                               file_name="laminate_comparison.csv", mime="text/csv")
            objective = st.selectbox("Rank candidates by", ["Highest first-ply load factor", "Lowest |εx⁰|", "Highest A₁₁", "Highest D₁₁"])
            column, ascending = {"Highest first-ply load factor": ("First-ply load factor", False),
                                 "Lowest |εx⁰|": ("εx⁰ [µε]", True),
                                 "Highest A₁₁": ("A₁₁ [MN/m]", False),
                                 "Highest D₁₁": ("D₁₁ [N·m]", False)}[objective]
            ranking = comparison.assign(**{"|εx⁰|": comparison["εx⁰ [µε]"].abs()})
            if objective == "Lowest |εx⁰|":
                column = "|εx⁰|"
            ranking = ranking.sort_values(column, ascending=ascending)
            st.metric("Top candidate for selected criterion", ranking.iloc[0]["Layup"])
            if np.isfinite(ranking[column].to_numpy(dtype=float)).all():
                st.altair_chart(alt.Chart(ranking).mark_bar(color="#087f8c", cornerRadiusEnd=4).encode(
                    x=alt.X(f"{column}:Q", title=column),
                    y=alt.Y("Layup:N", sort=None, title=None),
                    tooltip=["Layup", alt.Tooltip(f"{column}:Q", format=".3g")],
                ).properties(height=48 * len(ranking) + 40), width="stretch")
            else:
                st.info("All zero-load designs have an unbounded load factor; enter a nonzero load to compare this criterion.")
            st.caption("A stiffer or thicker candidate may rank well while using more material. This is a transparent criterion-based ranking, not an optimiser.")

with tabs[7]:
    st.subheader("Pressure vessel: filament-wound cylinder")
    st.info("**What to do:** set the radius and the wall, then read the winding-angle study. The study uses the sidebar material; "
            "the second part checks the layup from the Layup tab as a cylinder wall.")
    st.write("A closed thin-walled cylinder under internal pressure p carries Nx = pR/2 along its axis (x) and Ny = pR around the hoop (y). "
             "Ply angles are measured from the axis, so a 90° ply is a hoop winding.")
    st.latex(r"N_x=\tfrac{1}{2}pR,\qquad N_y=pR,\qquad \text{netting: }\tan^2\theta=\frac{N_y}{N_x}=2\;\Rightarrow\;\theta=54.74^\circ")
    vessel_cols = st.columns(3)
    radius_mm = vessel_cols[0].number_input("Radius R [mm]", min_value=1.0, value=100.0, step=10.0, key="vessel_radius")
    wall_plies = int(vessel_cols[1].number_input("Wall plies for the ±θ study (multiple of 4)", min_value=4, max_value=100,
                                                  value=16, step=4, key="vessel_plies"))
    working_mpa = vessel_cols[2].number_input("Working pressure [MPa]", min_value=0.0, value=10.0, step=1.0, key="vessel_working")
    radius_m = radius_mm * 1e-3
    if wall_plies % 4:
        st.error("Use a multiple of 4 plies, so the ±θ wall is balanced and symmetric.")
    else:
        sweep = []
        for theta in range(0, 91):
            theta_wall = angle_ply_wall(theta, wall_plies, ply_thickness_m)
            result = screen_cylinder(theta_wall, [material], [strengths], radius_m)
            last_ply = progressive_failure(theta_wall, [material], [strengths], cylinder_resultants(1.0, radius_m)).last_ply_load_factor
            sweep.append({"angle": theta, "first_ply": result.first_ply_pressure_pa / 1e6, "last_ply": last_ply / 1e6,
                          "netting": result.netting_bound_pa / 1e6, "mode": result.first_ply_mode})
        sweep_frame = pd.DataFrame(sweep)
        best = sweep_frame.loc[sweep_frame["first_ply"].idxmax()]
        netting_best = screen_cylinder(angle_ply_wall(NETTING_ANGLE_DEG, wall_plies, ply_thickness_m), [material], [strengths], radius_m)
        wall_mm = wall_plies * thickness_mm
        study_cols = st.columns(4)
        study_cols[0].metric("Wall thickness [mm]", f"{wall_mm:.2f}")
        study_cols[1].metric("Netting angle", f"±{NETTING_ANGLE_DEG:.2f}°")
        study_cols[2].metric("Netting burst at ±54.7° [MPa]", f"{netting_best.netting_pressure_pa / 1e6:.1f}")
        best_label = f"{best['angle']:.0f}°" if best["angle"] in (0, 90) else f"±{best['angle']:.0f}°"
        study_cols[3].metric("Best first-ply pressure [MPa]", f"{best['first_ply']:.1f} at {best_label}")
        long = sweep_frame.drop(columns="mode").melt("angle", var_name="key", value_name="pressure")
        long["limit"] = long["key"].map({"first_ply": "First-ply failure (CLT)", "last_ply": "Last-ply failure (Hashin, progressive)",
                                         "netting": "Fibre limit (netting)"})
        layers = [alt.Chart(long).mark_line(strokeWidth=3).encode(
                      x=alt.X("angle:Q", title="Winding angle ±θ [deg]", scale=alt.Scale(domain=[0, 90])),
                      y=alt.Y("pressure:Q", title="Pressure [MPa]", scale=alt.Scale(domainMin=0)),
                      color=alt.Color("limit:N", scale=alt.Scale(domain=["First-ply failure (CLT)", "Last-ply failure (Hashin, progressive)",
                                                                         "Fibre limit (netting)"],
                                                                 range=["#e07b22", "#7b3fa0", "#087f8c"]),
                                      legend=alt.Legend(orient="top", title=None)),
                      tooltip=[alt.Tooltip("angle:Q", title="Angle [deg]"), alt.Tooltip("limit:N", title="Limit"),
                               alt.Tooltip("pressure:Q", title="Pressure [MPa]", format=".2f")]),
                  alt.Chart(pd.DataFrame({"x": [NETTING_ANGLE_DEG]})).mark_rule(strokeDash=[5, 4], color="#5b7080").encode(x="x:Q")]
        if working_mpa > 0:
            layers.append(alt.Chart(pd.DataFrame({"y": [working_mpa]})).mark_rule(color="#c0392b").encode(y="y:Q"))
        st.altair_chart(alt.layer(*layers).properties(height=330), width="stretch")
        st.caption(f"±θ wall of {wall_plies} plies, sidebar material, R = {radius_mm:g} mm. Dashed line: netting angle 54.74°"
                   + ("; red line: working pressure." if working_mpa > 0 else ".")
                   + " Away from 54.74° fibres alone cannot balance Nx and Ny; the teal curve is the pressure at which the more demanding "
                   "direction would bring the fibres to Xt (an upper bound). Purple: last-ply pressure of the progressive-failure model "
                   "with its default degradation factors (assumptions, see the layup check below).")
        ratio = netting_best.first_ply_pressure_pa / max(netting_best.netting_pressure_pa, 1e-12)
        peak_text = (f"is also highest near this angle here ({best_label}, failure mode: {best['mode'].lower()}). "
                     if abs(best["angle"] - NETTING_ANGLE_DEG) <= 3 else
                     f"peaks at {best_label} for this material (failure mode: {best['mode'].lower()}). ")
        ratio_text = (f"At ±54.7° the first ply fails at about {ratio:.0%} of the netting burst estimate: matrix damage starts well before "
                      "the fibres break. Burst is governed by fibre failure; matrix cracks matter for stiffness, fatigue and gas tightness, "
                      "which in a Type IV tank is provided by the polymer liner."
                      if ratio < 1 else
                      "For this material the CLT first-ply estimate exceeds the netting estimate, so the fibre-only bound is not meaningful here.")
        st.markdown("**How to read it.** Netting theory lets only the fibres carry load: a ±θ wind can balance Ny = 2Nx with fibres alone only at "
                    "tan²θ = 2, so the netting burst pressure peaks at ±54.7°. The CLT first-ply pressure, where the matrix still carries load, "
                    + peak_text + ratio_text)
        if radius_mm / max(wall_mm, 1e-9) < 10:
            st.warning(f"R/h = {radius_mm / wall_mm:.1f} is below 10: the thin-wall assumption Ny = pR becomes inaccurate.")

    st.markdown("**Check the current layup as a cylinder wall**")
    if stiffness is not None:
        current = screen_cylinder(st.session_state.plies, materials_list, strengths_list, radius_m)
        current_wall = (stiffness.z[-1] - stiffness.z[0]) * 1e3
        check_cols = st.columns(3)
        check_cols[0].metric("First-ply failure pressure [MPa]", f"{current.first_ply_pressure_pa / 1e6:.2f}",
                             help=f"Ply {current.first_ply_ply}, {current.first_ply_surface.lower()} face; {current.first_ply_criterion} criterion; mode: {current.first_ply_mode.lower()}.")
        check_cols[1].metric("Netting burst estimate [MPa]", f"{current.netting_pressure_pa / 1e6:.2f}",
                             help="Exact netting solution: fibre stresses between 0 and Xt that satisfy both axial and hoop equilibrium.")
        if working_mpa > 0:
            check_cols[2].metric("Netting burst / working pressure", f"{current.netting_pressure_pa / 1e6 / working_mpa:.2f}")
        if current.netting_pressure_pa <= 0:
            st.warning("Netting burst = 0: with fibres only, this layup cannot balance Nx and Ny (for example a single ±θ wind away from 54.7°). "
                       "Add hoop (90°) or low-angle helical plies.")
        st.caption(f"Current layup ({len(st.session_state.plies)} plies, h = {current_wall:.2f} mm), each ply with its own material. "
                   "Hoop (90°) plies carry Ny and low-angle helical plies carry Nx; try [90,15,-15,90]s against [55,-55,55,-55]s.")
        st.markdown("**First-ply vs last-ply failure of the current layup (progressive failure)**")
        st.write("The wall is loaded with Nx = pR/2 and Ny = pR. At each failure the failed ply is degraded, ABD is rebuilt and the pressure rises "
                 "until the discount algorithm stops: the first failure is first-ply failure by Hashin; the last pressure is where this model stops (two degradations of a family, see the rules), not a measured burst pressure.")
        with st.expander("Degradation rules: model assumptions, not material data"):
            rule_cols = st.columns(3)
            fibre_factor = rule_cols[0].number_input("E₁ kept after fibre failure", min_value=0.001, max_value=1.0, value=0.01,
                                                     step=0.01, format="%.3f", key="deg_fibre")
            matrix_e2_factor = rule_cols[1].number_input("E₂ kept after matrix failure", min_value=0.001, max_value=1.0, value=0.1,
                                                         step=0.05, format="%.3f", key="deg_e2")
            matrix_g_factor = rule_cols[2].number_input("G₁₂ kept after matrix failure", min_value=0.001, max_value=1.0, value=0.1,
                                                        step=0.05, format="%.3f", key="deg_g12")
            degradation = DegradationRules(fibre_factor, matrix_e2_factor, matrix_g_factor)
            st.caption(degradation.statement(transverse_shear_assumed=any(s.St is None for s in strengths_list)) + " The last-ply pressure changes with these factors.")
        try:
            progressive = progressive_failure(st.session_state.plies, materials_list, strengths_list,
                                              cylinder_resultants(1.0, radius_m), degradation)
        except ValueError as error:
            st.warning(str(error))
        else:
            first_event = progressive.events[0]
            prog_cols = st.columns(4)
            prog_cols[0].metric("First-ply, Hashin [MPa]", f"{progressive.first_ply_load_factor / 1e6:.2f}",
                                help=f"Ply {first_event.ply}, {first_event.surface.lower()} face; mode: {first_event.mode.lower()}. "
                                     "The CLT first-ply value above uses Maximum Stress and Tsai–Wu.")
            prog_cols[1].metric("Last-ply (model stop) [MPa]", f"{progressive.last_ply_load_factor / 1e6:.2f}",
                                help="Pressure at which the discount algorithm stops (two-level residual-stiffness termination rule). Every residual stiffness stays positive: this is not a physical ultimate load.")
            prog_cols[2].metric("Last-ply / first-ply", f"{progressive.last_ply_load_factor / progressive.first_ply_load_factor:.2f}",
                                help="Reserve between the first damage and the end of the load-carrying capacity.")
            prog_cols[3].metric("Last-ply / netting estimate",
                                "n/a" if current.netting_pressure_pa <= 0 else f"{progressive.last_ply_load_factor / current.netting_pressure_pa:.2f}",
                                help="Netting (fibres only, shown above) is the reference; near 1 means the fibres govern the burst.")
            rows = []
            for step in progressive.history[1:]:
                pressure = f"{step.load_factor / 1e6:.2f}"
                if step.kind == "failure":
                    step_events = [e for e in progressive.events if e.step == step.step]
                    rows.append({"Step": step.step, "Pressure [MPa]": float(pressure), "What happens": "Hashin failure",
                                 "Mode": ", ".join(sorted({e.mode for e in step_events})),
                                 "Plies": ", ".join(str(e.ply) for e in step_events), "Stiffness left": step.stiffness_ratio})
                else:
                    rows.append({"Step": step.step, "Pressure [MPa]": float(pressure),
                                 "What happens": "Residual strength exceeded: degraded again",
                                 "Mode": ", ".join(sorted({family for _, family in step.escalations})),
                                 "Plies": ", ".join(str(ply) for ply, _ in step.escalations), "Stiffness left": step.stiffness_ratio})
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=table_height(len(rows)),
                         column_config={"Pressure [MPa]": st.column_config.NumberColumn(format="%.2f"),
                                        "Stiffness left": st.column_config.NumberColumn(format="%.3f",
                                            help="Secant stiffness along the pressure load, relative to the undamaged wall.")})
            pressure_mpa, hoop_strain = progressive.load_strain_curve(1)
            curve = pd.DataFrame({"strain": hoop_strain * 100.0, "pressure": pressure_mpa / 1e6})
            marks = [("First-ply (CLT)", current.first_ply_pressure_pa / 1e6, "#e07b22"),
                     ("Last-ply (progressive)", progressive.last_ply_load_factor / 1e6, "#7b3fa0")]
            if current.netting_pressure_pa > 0:
                marks.append(("Netting estimate", current.netting_pressure_pa / 1e6, "#087f8c"))
            if working_mpa > 0:
                marks.append(("Working pressure", working_mpa, "#c0392b"))
            mark_frame = pd.DataFrame(marks, columns=["limit", "pressure", "color"])
            progressive_chart = alt.layer(
                alt.Chart(curve).mark_line(color="#3b6fb6", strokeWidth=3).encode(
                    x=alt.X("strain:Q", title="Hoop strain εy [%]", scale=alt.Scale(domainMin=0)),
                    y=alt.Y("pressure:Q", title="Pressure [MPa]", scale=alt.Scale(domainMin=0)),
                    tooltip=[alt.Tooltip("strain:Q", title="εy [%]", format=".3f"), alt.Tooltip("pressure:Q", title="p [MPa]", format=".2f")]),
                alt.Chart(mark_frame).mark_rule(strokeDash=[5, 4]).encode(
                    y="pressure:Q", color=alt.Color("limit:N", scale=alt.Scale(domain=list(mark_frame["limit"]), range=list(mark_frame["color"])),
                                                    legend=alt.Legend(orient="top", title=None)),
                    tooltip=[alt.Tooltip("limit:N", title="Limit"), alt.Tooltip("pressure:Q", title="p [MPa]", format=".2f")]),
            ).properties(height=300)
            st.altair_chart(progressive_chart, width="stretch")
            ratio_note = progressive.last_ply_load_factor / progressive.first_ply_load_factor
            st.markdown(
                f"**How to read it.** The first damage is {first_event.mode.lower()} in ply {first_event.ply} at "
                f"{progressive.first_ply_load_factor / 1e6:.2f} MPa; the wall keeps carrying pressure with less and less stiffness "
                f"(the jumps in the curve), until {progressive.last_ply_load_factor / 1e6:.2f} MPa, {ratio_note:.2f}× the first-ply value. "
                f"Why it ends: {progressive.collapse_reason}. "
                "Matrix cracking (first ply) matters for stiffness, fatigue and gas tightness; burst is governed by the fibres, so the netting "
                "estimate stays the reference for the fibre limit.")
            st.caption("Progressive failure is applied to the cylindrical wall only (dome stations stay at first-ply, membrane theory). "
                       "The last-ply value depends on the assumed degradation factors and the Hashin criterion with an assumed transverse "
                       "shear strength; it is a screening estimate, not a validated burst prediction. The load factor is never reduced after a failure: "
                       "this is not a stability analysis (snap-through is not detected). Not modelled: open holes, fatigue, impact, moisture and "
                       "temperature, manufacturing defects, fibre kinking, crack growth, leakage and interlaminar strength. Use one computational ply per physical ply; "
                       "there is no fracture-energy regularisation.")
    st.divider()
    st.markdown("**Dome: geodesic winding into the polar opening**")
    st.write("On a dome the fibres follow geodesics, so the polar opening r₀ fixes the winding angle: α₀ = asin(r₀/R) on the cylinder, "
             "rising to 90° at the opening (angles from the meridian, as above). The dome wall is the ±α₀ wall (same plies and sidebar "
             "material) carried over the dome. It thickens toward the polar opening, and the membrane resultants follow the dome curvature "
             "(r₁ meridional, r₂ circumferential radius).")
    st.latex(r"r\sin\alpha=r_0,\quad t(r)=t_{cyl}\frac{R\cos\alpha_0}{r\cos\alpha},\quad "
             r"N_\varphi=\frac{p\,r_2}{2},\quad N_\theta=p\,r_2\Bigl(1-\frac{r_2}{2r_1}\Bigr)")
    if wall_plies % 4:
        st.info("Use a multiple of 4 wall plies above to evaluate the dome.")
    else:
        dome_cols = st.columns(3)
        dome_r0_ratio = dome_cols[0].number_input("Polar opening ratio r₀ / R", min_value=0.05, max_value=0.95, value=0.5,
                                                  step=0.05, key="dome_r0_ratio")
        dome_aspect = dome_cols[1].number_input("Dome depth / R (1 = hemisphere, 0.5 = 2:1 ellipsoid)", min_value=0.3, max_value=1.2,
                                                value=1.0, step=0.05, key="dome_aspect")
        dome_r0 = dome_r0_ratio * radius_m
        dome_alpha0 = cylinder_winding_angle_deg(dome_r0, radius_m)
        dome_cols[2].metric("Cylinder winding angle α₀", f"±{dome_alpha0:.1f}°",
                            help="asin(r₀/R). Hoop plies are not geodesic and are not part of this dome wall.")
        dome_layup = angle_ply_wall(dome_alpha0, wall_plies, ply_thickness_m)
        try:
            dome_result = dome_stations(dome_layup, [material], [strengths], dome_r0, radius_m, aspect_ratio=dome_aspect)
        except ValueError as error:
            st.error(str(error))
        else:
            dome_cyl_mpa = screen_cylinder(dome_layup, [material], [strengths], radius_m).first_ply_pressure_pa / 1e6
            dome_frame = pd.DataFrame({"r": dome_result.radius_m * 1e3, "angle": dome_result.alpha_deg,
                                       "thickness": dome_result.thickness_m * 1e3,
                                       "first_ply": dome_result.first_ply_pressure_pa / 1e6,
                                       "valid": dome_result.membrane_valid})
            weakest = dome_result.weakest_valid_index()
            zone_mm = dome_result.bending_zone_m * 1e3
            dome_metrics = st.columns(3)
            dome_metrics[0].metric("Wall thickness, cylinder → last station [mm]",
                                   f"{dome_frame['thickness'].iloc[0]:.2f} → {dome_frame['thickness'].iloc[-1]:.1f}",
                                   help="The last station is at r = 1.02·r₀: the model thickness is infinite at r₀.")
            if weakest is None:
                dome_metrics[1].metric("Weakest valid dome station, first-ply [MPa]", "n/a",
                                       help=f"Every station lies within the bending zone (about {zone_mm:.0f} mm) of the junction or the "
                                            "opening, so membrane theory gives no usable strength value for this wall.")
            else:
                dome_metrics[1].metric("Weakest valid dome station, first-ply [MPa]", f"{dome_frame['first_ply'].iloc[weakest]:.2f}",
                                       help=f"At r = {dome_frame['r'].iloc[weakest]:.0f} mm, ply {dome_result.first_ply_ply[weakest]}; "
                                            f"mode: {dome_result.first_ply_mode[weakest].lower()}. Stations within about {zone_mm:.0f} mm "
                                            "(meridional arc) of the junction or the opening are excluded.")
            dome_metrics[2].metric("Cylinder first-ply [MPa]", f"{dome_cyl_mpa:.2f}",
                                   help="Same ±α₀ wall as a cylinder (Ny = pR), for comparison.")
            dome_x = alt.X("r:Q", title="Parallel radius r [mm]  (cylinder → polar opening)", scale=alt.Scale(reverse=True))
            angle_line = alt.Chart(dome_frame).mark_line(color="#087f8c", strokeWidth=3).encode(
                x=dome_x, y=alt.Y("angle:Q", title="Winding angle α [deg]", scale=alt.Scale(domain=[0, 90]),
                                  axis=alt.Axis(titleColor="#087f8c")),
                tooltip=[alt.Tooltip("r:Q", title="r [mm]", format=".1f"), alt.Tooltip("angle:Q", title="α [deg]", format=".1f")])
            thickness_line = alt.Chart(dome_frame).mark_line(color="#e07b22", strokeWidth=3).encode(
                x=dome_x, y=alt.Y("thickness:Q", title="Wall thickness [mm]", scale=alt.Scale(domainMin=0),
                                  axis=alt.Axis(titleColor="#e07b22", orient="right")),
                tooltip=[alt.Tooltip("r:Q", title="r [mm]", format=".1f"), alt.Tooltip("thickness:Q", title="t [mm]", format=".2f")])
            fp_layers = [alt.Chart(dome_frame).mark_line(color="#9db4d6", strokeWidth=2, strokeDash=[2, 3]).encode(
                             x=dome_x, y=alt.Y("first_ply:Q", title="First-ply pressure [MPa]", scale=alt.Scale(domainMin=0))),
                         alt.Chart(dome_frame[dome_frame["valid"]]).mark_line(color="#3b6fb6", strokeWidth=3, point=True).encode(
                             x=dome_x, y=alt.Y("first_ply:Q", title="First-ply pressure [MPa]", scale=alt.Scale(domainMin=0)),
                             tooltip=[alt.Tooltip("r:Q", title="r [mm]", format=".1f"),
                                      alt.Tooltip("first_ply:Q", title="p first-ply [MPa]", format=".2f")]),
                         alt.Chart(pd.DataFrame({"y": [dome_cyl_mpa]})).mark_rule(strokeDash=[5, 4], color="#5b7080").encode(y="y:Q")]
            if working_mpa > 0:
                fp_layers.append(alt.Chart(pd.DataFrame({"y": [working_mpa]})).mark_rule(color="#c0392b").encode(y="y:Q"))
            chart_cols = st.columns(2)
            chart_cols[0].altair_chart(alt.layer(angle_line, thickness_line).resolve_scale(y="independent").properties(height=300),
                                       width="stretch")
            chart_cols[1].altair_chart(alt.layer(*fp_layers).properties(height=300), width="stretch")
            st.caption("Left: winding angle (teal) and wall thickness (orange). Right: first-ply pressure of the wall at each station; "
                       "dashed grey = the same ±α₀ wall as a cylinder" + ("; red = working pressure" if working_mpa > 0 else "")
                       + f". Faint dotted blue: stations within ≈{zone_mm:.0f} mm of the junction or opening, where the membrane/CLT value is not a strength prediction.")
            junction_ratio = dome_result.n_theta[0] / radius_m
            weakest_text = ("No station is far enough from the edges for a membrane-theory strength value. " if weakest is None else
                            f"The weakest valid station (r = {dome_frame['r'].iloc[weakest]:.0f} mm, "
                            f"{dome_result.first_ply_mode[weakest].lower()}) is where the helical plies carry the dome loads worst. ")
            dome_text = (f"Clairaut's relation turns the fibres from α₀ = {dome_alpha0:.1f}° toward the hoop direction at the opening, and the "
                         "constant band width makes the wall thicken as 1/(r cos α). " + weakest_text +
                         "At the junction the dome hoop resultant is "
                         f"{junction_ratio:.2f}·pR against pR in the cylinder, so the membrane hoop load jumps there and a bending boundary layer "
                         "forms; the thickness law is singular at the opening. Neither edge is a strength prediction: use a shell-bending or "
                         "finite-element transition analysis for them. ")
            if float(dome_result.n_theta.min()) < 0:
                dome_text += "For this depth N_θ is negative near the equator (depth below about 0.71·R): the hoop direction is in compression. "
            st.markdown("**How to read it.** " + dome_text)
            st.caption("Dome model limits: helical plies only (no hoop plies, boss or liner), no fibre slippage, constant band width and fibre "
                       "volume fraction, membrane theory (no bending). N_φ = p r₂/2 assumes a pressure-tight boss that passes the axial reaction "
                       "p·π·r₀² into the shell at the opening. The edge zone is an isotropic-shell estimate (ν = 0.3, cylinder wall thickness). "
                       "The isotensoid profile is not included.")
    st.info("**Model limits.** The cylinder checks cover the cylindrical section only; the dome part above models the helical plies alone "
            "(no bosses, end-fittings or slippage), thin-wall membrane resultants, no liner, "
            "no residual or thermal stresses. Netting ignores the matrix; for hybrid walls it is an upper estimate because fibres of "
            "different stiffness do not reach their strengths together. Real tank burst also depends on dome design, winding quality and progressive damage.")

with tabs[8]:
    st.subheader("Manufacturing: what the ideal CLT model leaves out")
    st.write("CLT assumes the laminate is built exactly as drawn. Choose a process or a discrepancy to see what has to be controlled before the model represents the real part.")
    st.dataframe(pd.DataFrame([
        {"Method": "Wet lay-up", "Principle": "Manual fibre placement and impregnation", "Advantage": "Low equipment cost", "Limitation": "Operator and void variability"},
        {"Method": "Vacuum bagging", "Principle": "Vacuum consolidates the laminate during cure", "Advantage": "Better consolidation", "Limitation": "Leak and process control"},
        {"Method": "Resin infusion", "Principle": "Resin flows through a dry preform", "Advantage": "Suitable for larger parts", "Limitation": "Dry spots and flow paths"},
        {"Method": "Prepreg/autoclave", "Principle": "Controlled prepreg cured with heat and pressure", "Advantage": "Good process repeatability", "Limitation": "High cost and equipment needs"},
        {"Method": "Filament winding", "Principle": "Resin-wetted tows wound on a rotating mandrel", "Advantage": "Automated; cylinders and pressure vessels", "Limitation": "Mostly axisymmetric shapes"},
    ]), hide_index=True, width="stretch")
    process_details = {
        "Wet lay-up": ("Fibres are positioned and resin is introduced manually.",
                       "Check resin content, ply orientation and trapped air during lay-up."),
        "Vacuum bagging": ("Vacuum consolidates the stack while resin cures.",
                           "Check bag integrity, compaction and the specified cure process."),
        "Resin infusion": ("Resin is drawn through a dry fibre preform.",
                           "Check flow paths and complete wet-out; dry zones or voids require inspection."),
        "Prepreg/autoclave": ("Pre-impregnated plies are laid up and cured with controlled heat and pressure.",
                              "Check material storage, orientation, bagging and the prescribed cure cycle."),
        "Filament winding": ("Continuous tows are wound over a rotating mandrel at programmed hoop and helical angles.",
                             "Check winding angle, tow tension, band gaps/overlaps and resin content."),
    }
    chosen_process = st.selectbox("Inspect a manufacturing route", list(process_details))
    process_principle, process_control = process_details[chosen_process]
    st.info(f"**How it works:** {process_principle}\n\n**Control point:** {process_control}")
    defect_details = {
        "Wrong ply orientation": "Changes the intended Q̄ and therefore A/B/D. A calculation using the drawing no longer represents the built stack.",
        "Voids or porosity": "Changes the manufactured material and may reduce its properties. CLT cannot infer a property knockdown without measured data.",
        "Delamination": "Breaks the perfect-bonding assumption between plies. This app does not calculate interlaminar stresses or damage growth.",
    }
    chosen_defect = st.selectbox("Which discrepancy would you investigate?", list(defect_details))
    st.warning(defect_details[chosen_defect])
    st.markdown("Process-control and inspection examples: [FAA AC 21-26A](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_21-26A.pdf). The app applies **no invented defect knockdown factor**.")

with tabs[9]:
    st.subheader("Applications: two worked examples")
    application = st.radio("Choose a context", ["Aerospace-inspired panel", "Wind-blade spar cap (unsymmetric)"], horizontal=True)
    if application == "Aerospace-inspired panel":
        st.write("A thin wing-skin panel carries axial and in-plane shear resultants. Compare three **equal-thickness** layups under an illustrative load to see how orientation tailors the membrane response.")
        scenario = st.selectbox("Illustrative load case", ["Axial Nx = 100 kN/m", "In-plane shear Nxy = 50 kN/m"])
        is_shear = scenario.startswith("In-plane")
        scenario_load = np.array([0, 0, 50e3, 0, 0, 0] if is_shear else [100e3, 0, 0, 0, 0, 0], dtype=float)
        panel_stacks = ["[0,0]s", "[0,90]s", "[45,-45]s"]
        panel_designs = [assess_design(name, name, ply_thickness_m, material, strengths, scenario_load)
                         for name in panel_stacks]
        panel_rows = [{"Layup": d.layup, "Thickness [mm]": d.thickness_m * 1e3,
                       ("A₆₆ [MN/m]" if is_shear else "A₁₁ [MN/m]"): (d.A66 if is_shear else d.A11) / 1e6,
                       ("γxy⁰ [µε]" if is_shear else "εx⁰ [µε]"): (d.gamma_xy if is_shear else d.epsilon_x) * 1e6,
                       "Max Stress index": d.max_utilization,
                       "First-ply load factor": d.first_ply_load_factor} for d in panel_designs]
        panel_frame = pd.DataFrame(panel_rows)
        st.dataframe(panel_frame, hide_index=True, width="stretch",
                     column_config={**fmt(panel_frame, "%.3f"), **fmt(None, "%.2f", [c for c in panel_frame if "MN/m" in c]),
                                    **fmt(None, "%.0f", [c for c in panel_frame if "µε" in c])})
        winner = min(panel_designs, key=lambda d: abs(d.gamma_xy if is_shear else d.epsilon_x))
        st.success(f"Lowest {'shear' if is_shear else 'x'} strain in this equal-thickness set: {winner.layup}.")
        st.markdown("Real wing structure is also sized by buckling, joints, impact/damage tolerance and environmental effects, using qualified allowables ([FAA AC 20-107B](https://www.faa.gov/airports/resources/advisory_circulars/index.cfm/go/document.information/documentNumber/20-107B)).")
    else:
        layup_sc, stiffness_sc = analyze_spar_cap()
        h_sc = (stiffness_sc.z[-1] - stiffness_sc.z[0]) * 1e3
        st.write("A wind-blade spar-cap region modelled as an equivalent two-layer panel: **3 mm triaxial glass skin + 65 mm unidirectional glass cap**, "
                 f"both at 0°. Material data: {MATERIAL_SOURCE}.")
        st.caption("A [MN/m]:")
        show_matrix(st, stiffness_sc.A, 1e6, ["x", "y", "xy"], "%.1f")
        offset_mm = stiffness_sc.B[0, 0] / stiffness_sc.A[0, 0] * 1e3
        st.write(f"The stack is unsymmetric, so B ≠ 0 (B₁₁ = {stiffness_sc.B[0, 0] / 1e3:,.0f} kN). Physically, the x-direction neutral axis lies "
                 f"B₁₁/A₁₁ = **{offset_mm:.2f} mm** above the geometric mid-plane, shifted away from the softer triax skin, "
                 "so an axial force through the mid-plane also bends the panel.")
        st.caption(f"At h = {h_sc:.0f} mm this is a thick section; transverse shear, which CLT neglects, may matter.")

with tabs[10]:
    st.subheader("Verification and model limits")
    st.write("Automated checks cover Q̄(0°) = Q, rotation invariants, B ≈ 0 for symmetric stacks, closed-form all-0° A and D, sign reversal of B, "
             "stress recovery, hybrid stacks, pure bending, the failure criteria at their strength points, laminate engineering constants "
             "and the pressure-vessel resultants and netting angle. Run them with `python -m unittest discover -s tests -v`.")
    benchmark_material = {"E1": 181e9, "E2": 10.3e9, "G12": 7.17e9, "v12": 0.28}
    benchmark = assemble_laminate_stiffness(parse_layup("[0,90]s", 0.125e-3), [benchmark_material])
    reference = pd.DataFrame([{"Quantity": "A₁₁ [MN/m]", "Published example": 48.039, "Calculated": benchmark.A[0, 0] / 1e6},
                              {"Quantity": "D₁₁ [N·m]", "Published example": 1.671, "Calculated": benchmark.D[0, 0]},
                              {"Quantity": "max |B| [N]", "Published example": 0.0, "Calculated": float(np.max(np.abs(benchmark.B)))}])
    reference = tidy(reference)
    st.dataframe(reference, hide_index=True, width="stretch", column_config=fmt(reference, "%.4f"))
    st.markdown("Independent worked example, [0/90]s T300/5208: [source and derivation](https://mpolyco.com/learn/classical-laminate-theory). Published values are rounded.")
    st.info("**Model limits.** Linear-elastic plies in plane stress, perfectly bonded, thin-plate (Kirchhoff) kinematics without transverse shear. "
            "Thermal residual stresses are calculated in the Failure tab's thermal block only; the other tabs and the general PDF use mechanical loading. "
            "Not included in the thermal model: moisture, creep, temperature-dependent properties, interlaminar stresses and buckling. "
            "Strengths are literature values, not qualified allowables; Tsai–Wu F₁₂ is assumed.")
