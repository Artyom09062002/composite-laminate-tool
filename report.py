"""PDF report of the current analysis (inputs, ABD, engineering constants, ply results)."""
from __future__ import annotations

import io
import math
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from core import evaluate_failure, tsai_wu_load_factor

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
APP_URL = "https://composite-laminate-tool.streamlit.app/"
INK, TEAL, GRID, SHADE = colors.HexColor("#173042"), colors.HexColor("#087f8c"), colors.HexColor("#c9d8de"), colors.HexColor("#eef5f7")


def _fonts() -> tuple[str, str]:
    try:
        pdfmetrics.registerFont(TTFont("DejaVu", str(FONT_DIR / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
        return "DejaVu", "DejaVu-Bold"
    except Exception:  # fonts missing: fall back to the built-in Helvetica
        return "Helvetica", "Helvetica-Bold"


def _styles(regular: str, bold: str) -> dict[str, ParagraphStyle]:
    base = dict(fontName=regular, alignment=TA_LEFT)
    return {
        "title": ParagraphStyle("title", fontName=bold, fontSize=17, leading=21, textColor=INK, spaceAfter=2),
        "meta": ParagraphStyle("meta", **base, fontSize=8.5, leading=11, textColor=colors.HexColor("#5b7080")),
        "h": ParagraphStyle("h", fontName=bold, fontSize=11.5, leading=15, textColor=TEAL, spaceBefore=9, spaceAfter=4),
        "body": ParagraphStyle("body", **base, fontSize=9, leading=12.5, textColor=INK),
        "small": ParagraphStyle("small", **base, fontSize=7.8, leading=10.2, textColor=colors.HexColor("#4a5d6b")),
        "cell": ParagraphStyle("cell", **base, fontSize=7.8, leading=9.6, textColor=INK),
    }


def _table(rows, widths, regular, bold, header=True, align_right_from=1):
    head = ParagraphStyle("head", fontName=bold, fontSize=7.8, leading=9.6, textColor=INK)
    rows = [[Paragraph(c, head) if (header and r == 0) else c for c in row] for r, row in enumerate(rows)]
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("FONT", (0, 0), (-1, -1), regular, 7.8),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
        ("ALIGN", (align_right_from, 0 if not header else 1), (-1, -1), "RIGHT"),
    ]
    if header:
        style += [("FONT", (0, 0), (-1, 0), bold, 7.8), ("BACKGROUND", (0, 0), (-1, 0), SHADE)]
    table.setStyle(TableStyle(style))
    return table


def _fmt(value: float, digits: int = 4) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "—"
    if abs(value) < 1e-12:
        return "0"
    return f"{value:.{digits}g}"


def _fixed(value: float, decimals: int) -> str:
    """Fixed-point text without a negative zero (-0.00)."""
    return f"{round(float(value), decimals) + 0.0:.{decimals}f}"


def _small(value: float, scale_floor: float = 1e-12) -> str:
    """Curvature-type values: round-off below scale_floor is shown as 0."""
    return "0" if abs(value) < scale_floor else f"{value:.4g}"


def _matrix(name: str, matrix, scale: float, unit: str, regular, bold, digits=4):
    rows = [[f"{name} [{unit}]", "x", "y", "xy"]]
    for label, row in zip(("x", "y", "xy"), matrix):
        rows.append([label, *(_fmt(v / scale, digits) for v in row)])
    return _table(rows, [17 * mm, 13.5 * mm, 13.5 * mm, 13.5 * mm], regular, bold)


def build_pdf_report(*, material_name: str, material: dict, strengths, layup: list[dict],
                     material_names: list[str], loads, stiffness, constants, response,
                     surface_strengths, first_ply: tuple[int, float, str]) -> bytes:
    regular, bold = _fonts()
    st = _styles(regular, bold)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm,
                            title="Laminate analysis report", author="Composite Laminate Design & Analysis Tool")
    story = [
        Paragraph("Laminate analysis report", st["title"]),
        Paragraph(f"Composite Laminate Design &amp; Analysis Tool · {date.today():%d %B %Y} · {APP_URL}", st["meta"]),
        Paragraph("Classical Lamination Theory, linear-elastic plies in plane stress, first-ply screening. "
                  "Educational tool, not a certified design calculation.", st["meta"]),
    ]

    # 1. Inputs
    story.append(Paragraph("1. Inputs", st["h"]))
    s = strengths
    story.append(Paragraph(
        f"<b>Sidebar material:</b> {material_name}. E<sub>1</sub> = {material['E1'] / 1e9:.4g} GPa, "
        f"E<sub>2</sub> = {material['E2'] / 1e9:.4g} GPa, G<sub>12</sub> = {material['G12'] / 1e9:.4g} GPa, "
        f"ν<sub>12</sub> = {material['v12']:.3g}. Strengths: X<sub>t</sub> = {s.Xt / 1e6:.4g}, X<sub>c</sub> = {s.Xc / 1e6:.4g}, "
        f"Y<sub>t</sub> = {s.Yt / 1e6:.4g}, Y<sub>c</sub> = {s.Yc / 1e6:.4g}, S = {s.S / 1e6:.4g} MPa.", st["body"]))
    nx, ny, nxy, mx, my, mxy = loads
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        f"<b>Loads per unit width:</b> N<sub>x</sub> = {nx / 1e3:.4g}, N<sub>y</sub> = {ny / 1e3:.4g}, "
        f"N<sub>xy</sub> = {nxy / 1e3:.4g} kN/m; M<sub>x</sub> = {mx:.4g}, M<sub>y</sub> = {my:.4g}, "
        f"M<sub>xy</sub> = {mxy:.4g} N·m/m.", st["body"]))
    story.append(Spacer(1, 4))
    ply_rows = [["Ply", "Angle [deg]", "Thickness [mm]", "Material", "z bottom [mm]", "z top [mm]"]]
    for i, ply in enumerate(layup):
        ply_rows.append([str(i + 1), f"{ply['theta']:g}", f"{ply['t'] * 1e3:.4g}", material_names[ply["mat"]],
                         f"{stiffness.z[i] * 1e3:.4g}", f"{stiffness.z[i + 1] * 1e3:.4g}"])
    ply_table = _table(ply_rows, [10 * mm, 22 * mm, 24 * mm, 58 * mm, 28 * mm, 28 * mm], regular, bold)
    ply_table.setStyle(TableStyle([("ALIGN", (3, 1), (3, -1), "LEFT")]))
    story.append(Paragraph("Stacking sequence, bottom (−h/2) to top (+h/2):", st["small"]))
    story.append(ply_table)

    # 2. Stiffness
    story.append(Paragraph("2. Laminate stiffness", st["h"]))
    abd = Table([[_matrix("A", stiffness.A, 1e6, "MN/m", regular, bold),
                  _matrix("B", stiffness.B, 1.0, "N", regular, bold),
                  _matrix("D", stiffness.D, 1.0, "N·m", regular, bold)]],
                colWidths=[60 * mm, 60 * mm, 60 * mm])
    abd.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(abd)
    c = constants
    h_mm = (stiffness.z[-1] - stiffness.z[0]) * 1e3
    story.append(Spacer(1, 5))
    story.append(_table(
        [["Thickness h [mm]", "E<sub>x</sub> [GPa]", "E<sub>y</sub> [GPa]", "G<sub>xy</sub> [GPa]", "ν<sub>xy</sub>", "ν<sub>yx</sub>", "E<sub>x</sub> flexural [GPa]", "E<sub>y</sub> flexural [GPa]"],
         [f"{h_mm:.4g}", f"{c.Ex / 1e9:.4g}", f"{c.Ey / 1e9:.4g}", f"{c.Gxy / 1e9:.4g}", f"{c.nu_xy:.4g}",
          f"{c.nu_yx:.4g}", f"{c.Ex_flex / 1e9:.4g}", f"{c.Ey_flex / 1e9:.4g}"]],
        [22 * mm, 20 * mm, 20 * mm, 21 * mm, 17 * mm, 17 * mm, 30 * mm, 30 * mm], regular, bold, align_right_from=0))
    b_max = float(abs(stiffness.B).max()); a_scale = float(abs(stiffness.A).max()) * (stiffness.z[-1] - stiffness.z[0])
    if b_max > max(1e-8 * a_scale, 1e-10):
        story.append(Paragraph("B ≠ 0: these are apparent constants with curvature free to develop; with bending restrained the "
                               "membrane moduli are higher.", st["small"]))
    story.append(Paragraph("Equivalent constants of the laminate as a homogeneous plate of thickness h, from the compliance "
                           "ABD<super>−1</super> (membrane: E<sub>x</sub> = 1/(h·a<sub>11</sub>); flexural: E<sub>x</sub> = 12/(h<super>3</super>·d<sub>11</sub>)).", st["small"]))

    # 3. Response
    story.append(Paragraph("3. Mid-plane response", st["h"]))
    e0, k = response.midplane_strain, response.curvature
    story.append(_table(
        [["ε<sub>x</sub><super>0</super> [µε]", "ε<sub>y</sub><super>0</super> [µε]", "γ<sub>xy</sub><super>0</super> [µε]", "κ<sub>x</sub> [1/m]", "κ<sub>y</sub> [1/m]", "κ<sub>xy</sub> [1/m]"],
         [_fixed(e0[0] * 1e6, 1), _fixed(e0[1] * 1e6, 1), _fixed(e0[2] * 1e6, 1), _small(k[0]), _small(k[1]), _small(k[2])]],
        [30 * mm] * 6, regular, bold, align_right_from=0))

    # 4. Ply results
    story.append(Paragraph("4. Ply stresses and first-ply screening", st["h"]))
    rows = [["Ply", "Face", "Angle", "σ<sub>1</sub> [MPa]", "σ<sub>2</sub> [MPa]", "τ<sub>12</sub> [MPa]", "Max Stress index", "Mode", "Tsai–Wu FI", "Tsai–Wu R"]]
    for point, allow in zip(response.ply_surfaces, surface_strengths):
        check = evaluate_failure(point.local_stress, allow)
        rows.append([str(point.ply), point.surface, f"{point.angle_deg:g}°",
                     _fixed(point.local_stress[0] / 1e6, 2), _fixed(point.local_stress[1] / 1e6, 2),
                     _fixed(point.local_stress[2] / 1e6, 2), f"{check.maximum_stress_utilization:.3f}",
                     check.maximum_stress_mode, f"{check.tsai_wu_index:.3f}",
                     _fmt(tsai_wu_load_factor(point.local_stress, allow), 4)])
    results = _table(rows, [10 * mm, 14 * mm, 15 * mm, 17 * mm, 17 * mm, 18 * mm, 19 * mm, 30 * mm, 18 * mm, 18 * mm],
                     regular, bold, align_right_from=2)
    results.setStyle(TableStyle([("ALIGN", (7, 1), (7, -1), "LEFT")]))
    story.append(results)
    index, factor, criterion = first_ply
    if math.isfinite(factor):
        p = response.ply_surfaces[index]
        verdict = (f"<b>First-ply result:</b> proportional load factor <b>{factor:.3f}</b> (all six load components scaled together). "
                   f"First limit at ply {p.ply} ({p.angle_deg:g}°, {p.surface.lower()} face), {criterion} criterion. "
                   + ("Below the first-ply limit at the entered loads." if factor >= 1 else
                      "The entered loads exceed the first-ply limit."))
    else:
        verdict = "<b>First-ply result:</b> no load applied."
    story.append(Spacer(1, 5))
    story.append(KeepTogether([Paragraph(verdict, st["body"])]))

    # 5. Limits
    story.append(Paragraph("5. Model limits", st["h"]))
    story.append(Paragraph(
        "Linear-elastic plies in plane stress, perfectly bonded, thin-plate (Kirchhoff) kinematics without transverse shear. "
        "Not included: cure/thermal residual stresses, interlaminar stresses, progressive damage, buckling and environmental "
        "effects. Strengths are literature reference values, not qualified allowables; the Tsai–Wu interaction term "
        "F<sub>12</sub> = −0.5√(F<sub>11</sub>F<sub>22</sub>) is assumed.", st["small"]))

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont(regular, 7)
        canvas.setFillColor(colors.HexColor("#7a8c98"))
        canvas.drawString(16 * mm, 8 * mm, "Composite Laminate Design & Analysis Tool · laminate analysis report")
        canvas.drawRightString(A4[0] - 16 * mm, 8 * mm, f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
