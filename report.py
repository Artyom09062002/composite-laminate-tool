"""Compact one-page export of the existing laminate and cylinder analyses."""
from __future__ import annotations
import io
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line, PolyLine, Circle, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from presentation import progressive_frames, validation_status
from ui_theme import APP_VERSION, PALETTE, MODE_COLOURS

FONT_DIR = Path(__file__).parent / "assets" / "fonts"
APP_URL = "https://composite-laminate-tool.streamlit.app/"
INK, TEAL, GRID, SHADE = [colors.HexColor(PALETTE[k]) for k in ("ink", "teal", "grid", "shade")]


def _fonts():
    try:
        pdfmetrics.registerFont(TTFont("DejaVu", str(FONT_DIR / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
        return "DejaVu", "DejaVu-Bold"
    except (OSError, ValueError):
        return "Helvetica", "Helvetica-Bold"


def _fmt(value, digits=4):
    if value is None or not math.isfinite(value):
        return "n/a"
    return "0" if abs(value) < 1e-12 else f"{value:.{digits}g}"


def _styles(regular, bold):
    """Retain the typography API used by the existing historical reports."""
    styles = {}
    for key, size, leading in (("title",17,21),("meta",8.5,11),("h",11.5,15),
                               ("body",9,12.5),("small",7.8,10.2),("cell",7.8,9.6)):
        styles[key] = ParagraphStyle(key, fontName=bold if key in ("title","h") else regular,
                                    fontSize=size, leading=leading, textColor=TEAL if key == "h" else INK,
                                    spaceBefore=9 if key == "h" else 0, spaceAfter=4 if key == "h" else 0)
    return styles


def _table(rows, widths, regular, bold, header=True, align_right_from=1):
    """Compatibility for Report No. 2 and the existing thermal report."""
    cell = _styles(regular,bold)["cell"]
    wrapped = [[Paragraph(value,cell) if isinstance(value,str) else value for value in row] for row in rows]
    table = Table(wrapped,colWidths=widths,repeatRows=1 if header else 0)
    table.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.4,GRID), ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("FONT",(0,0),(-1,-1),regular,7.8),("TOPPADDING",(0,0),(-1,-1),2.2),
        ("BOTTOMPADDING",(0,0),(-1,-1),2.2)] +
        ([("BACKGROUND",(0,0),(-1,0),SHADE)] if header else [])))
    return table


def _fixed(value, decimals):
    return f"{round(float(value), decimals) + 0.0:.{decimals}f}"


def _small(value, scale_floor=1e-12):
    return "0" if abs(value) < scale_floor else f"{value:.4g}"


def _recorded_tests():
    path = Path(__file__).parent / "verification" / "qa_results.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return f"Recorded suite: {data['tests_run']} tests, {data['failures']} failures, {data['errors']} errors, {data['skipped']} skipped"
    return "Recorded R0 baseline: 146 tests; current checks in verification/AUDIT.md"


def pressure_strain_drawing(progressive, font):
    """The same arrays and pre-damage event coordinates used by the UI."""
    curve, events = progressive_frames(progressive)
    drawing = Drawing(500, 190)
    x0, y0, w, h = 45, 35, 410, 100
    xmax = max(float(curve.strain.max()), 1e-12)
    ymax = max(float(curve.pressure.max()), 1e-12)
    x = lambda v: x0 + w * float(v) / xmax
    y = lambda v: y0 + h * float(v) / ymax
    drawing.add(Line(x0, y0, x0+w, y0, strokeColor=GRID))
    drawing.add(Line(x0, y0, x0, y0+h, strokeColor=GRID))
    drawing.add(PolyLine([coordinate for row in curve.itertuples() for coordinate in (x(row.strain), y(row.pressure))],
                         strokeColor=colors.HexColor("#3b6fb6"), strokeWidth=1.7))
    for row in events.itertuples():
        drawing.add(Circle(x(row.strain), y(row.pressure), 2.8,
                           fillColor=colors.HexColor(MODE_COLOURS[row.Mode]), strokeColor=colors.white))
    for fraction in (0, .5, 1):
        drawing.add(String(x0+w*fraction, y0-12, f"{xmax*fraction:.3g}", fontName=font, fontSize=7, textAnchor="middle"))
        drawing.add(String(x0-6, y0+h*fraction, f"{ymax*fraction:.3g}", fontName=font, fontSize=7, textAnchor="end"))
    drawing.add(String(x0+w/2, 8, "Hoop strain [%]", fontName=font, fontSize=8, textAnchor="middle"))
    drawing.add(String(3, 150, "Pressure [MPa]", fontName=font, fontSize=8))
    for i, mode in enumerate(events.Mode.unique()):
        drawing.add(String(100+(i%2)*220, 175-(i//2)*12, mode,
                           fillColor=colors.HexColor(MODE_COLOURS[mode]), fontName=font, fontSize=6.5))
    return drawing


def build_pdf_report(*, material_name, material, strengths, layup, material_names, loads,
                     stiffness, constants, response, surface_strengths, first_ply, vessel=None):
    regular, bold = _fonts()
    styles = {
        "title": ParagraphStyle("title", fontName=bold, fontSize=16, leading=20, textColor=INK),
        "body": ParagraphStyle("body", fontName=regular, fontSize=8, leading=11, textColor=INK),
        "small": ParagraphStyle("small", fontName=regular, fontSize=7, leading=9, textColor=INK),
        "h": ParagraphStyle("h", fontName=bold, fontSize=10, leading=13, textColor=TEAL, spaceBefore=7, spaceAfter=3),
    }
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=16*mm, rightMargin=16*mm,
                            topMargin=12*mm, bottomMargin=14*mm, title="Composite screening report", pageCompression=0)
    story = [Paragraph("Composite screening report", styles["title"]),
             Paragraph("Educational CLT and cylinder screening. Reference data, not qualified design allowables.", styles["small"])]
    def text(value, style="body"):
        story.append(Paragraph(value, styles[style]))
    def heading(value):
        text(value, "h")
    def table(rows, widths):
        wrapped = [[Paragraph(escape(str(v)), styles["small"]) for v in row] for row in rows]
        t = Table(wrapped, colWidths=widths, hAlign="LEFT")
        t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.4,GRID), ("BACKGROUND",(0,0),(-1,0),SHADE),
                               ("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),3),
                               ("BOTTOMPADDING",(0,0),(-1,-1),3)]))
        story.append(t)
    heading("Inputs and load cases")
    h = float(stiffness.z[-1]-stiffness.z[0])
    text(f"<b>Material:</b> {escape(material_name)}. {len(layup)} physical plies; thickness {h*1e3:.4g} mm.")
    # Run-length encoding keeps the full physical sequence readable at 40 and 100 plies.
    groups = []
    uniform = len({(p['t'], p['mat']) for p in layup}) == 1
    for ply in layup:
        label = f"{ply['theta']:g}°" if uniform else f"{ply['theta']:g}°/{ply['t']*1e3:.3g}mm/M{ply['mat']}"
        if groups and groups[-1][0] == label:
            groups[-1][1] += 1
        else:
            groups.append([label, 1])
    sequence = "; ".join(f"{label}" + (f" x{count}" if count > 1 else "") for label,count in groups)
    if len(sequence) <= 500:
        text("Bottom to top: " + escape(sequence), "small")
    else:
        text("Long stack: full bottom-to-top ply inputs remain in the app; this page reports the governing result.", "small")
    active = sorted({p["mat"] for p in layup})
    if uniform:
        text(f"Each ply: {layup[0]['t']*1e3:.4g} mm, M{layup[0]['mat']}.", "small")
    text("; ".join(f"M{i}: {escape(material_names[i])}" for i in active), "small")
    text("Laminate loads: N [kN/m] = (" + ", ".join(f"{v/1e3:.4g}" for v in loads[:3]) +
         "); M [N·m/m] = (" + ", ".join(f"{v:.4g}" for v in loads[3:]) + ").", "small")
    heading("Laminate stiffness and response (sidebar mechanical loads)")
    table([["A [MN/m]", "B [N]", "D [N·m]"]] +
          [[" / ".join(_fmt(v/scale) for v in matrix[row]) for matrix,scale in
            ((stiffness.A,1e6),(stiffness.B,1),(stiffness.D,1))] for row in range(3)], [60*mm]*3)
    text("Each matrix row uses x, y, xy order. E_x / E_y / G_xy [GPa]: " +
         " / ".join(f"{v/1e9:.4g}" for v in (constants.Ex, constants.Ey, constants.Gxy)) + ".", "small")
    text("Mid-plane strain [µε]: " + " / ".join(_fixed(v*1e6,1) for v in response.midplane_strain) +
         "; curvature [1/m]: " + " / ".join(_small(v) for v in response.curvature) + ".", "small")
    index, factor, criterion = first_ply
    if math.isfinite(factor):
        point = response.ply_surfaces[index]
        text(f"Mechanical first-ply load factor: <b>{factor:.4g}</b> ({escape(criterion)}), ply {point.ply}, {escape(point.surface)} face. " +
             ("Entered loads are below or at the initiation limit." if factor >= 1 else "Entered loads exceed the initiation limit."))
    else:
        text("Mechanical first-ply load factor: no applied load.")
    if vessel is not None:
        current, progressive = vessel["screen"], vessel["progressive"]
        heading("Cylinder pressure case (separate from sidebar loads)")
        text(f"R = {vessel['radius_m']*1e3:.4g} mm; current layup h = {h*1e3:.4g} mm; working pressure = {vessel['working_mpa']:.4g} MPa. Nx=pR/2, Ny=pR.")
        table([["First-ply CLT [MPa]", "First-ply Hashin [MPa]", "Last-ply model stop [MPa]", "Netting [MPa]"],
               [f"{current.first_ply_pressure_pa/1e6:.4f}", f"{progressive.first_ply_load_factor/1e6:.4f}",
                f"{progressive.last_ply_load_factor/1e6:.4f}", f"{current.netting_pressure_pa/1e6:.4f}"]], [45*mm]*4)
        text("First-ply marks calculated initiation. Last-ply is the assumed algorithm stop, <b>not an ultimate or burst load</b>. Netting is a separate fibre-only equilibrium reference.", "small")
        story.append(pressure_strain_drawing(progressive, regular))
        text("Points: initiation modes before stiffness reduction; jumps: redistribution at held pressure. This is not a stability analysis.", "small")
    heading("Limits and validation")
    text(validation_status(), "small")
    text("Model assumptions: plane stress, perfect bonding, thin-plate CLT; Tsai-Wu interaction F12 is assumed. " +
         ("Cylinder degradation: E1 retained " + f"{vessel['rules'].fibre_E1_factor:g}; E2 / G12 retained " +
          f"{vessel['rules'].matrix_E2_factor:g} / {vessel['rules'].matrix_G12_factor:g}; Hashin transverse shear strength assumed when not supplied. " if vessel else "") +
         "Not included in this export: thermal preload, dome strength, liner/boss load sharing, interlaminar damage, fatigue, leakage, buckling, manufacturing defects or temperature-dependent properties.", "small")
    day = datetime.now(timezone(timedelta(hours=5))).date()
    def footer(canvas, document):
        canvas.setFont(regular, 6.5)
        canvas.setFillColor(INK)
        canvas.drawString(16*mm, 9*mm, f"{day.isoformat()} (UTC+5) · {APP_VERSION} · " + _recorded_tests())
        canvas.drawRightString(A4[0]-16*mm, 6*mm, f"Page {document.page} · {APP_URL}")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
