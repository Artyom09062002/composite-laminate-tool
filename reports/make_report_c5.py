"""Reproduce the C5 thermal teaching cases using sourced built-in material data."""
from pathlib import Path
import sys

import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import (assemble_laminate_stiffness, recover_ply_surfaces, recover_thermal_response,
                  first_ply_mechanical_load_factor, StrengthAllowables)
from materials import DEFAULT_MATERIALS
from workflow import parse_layup
from report import _fonts, _styles, _table


def main():
    output = Path(__file__).resolve().parents[1] / "output" / "pdf" / "C5_thermal_laminates.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    regular, bold = _fonts()
    styles = _styles(regular, bold)
    story = [Paragraph("C5 - Thermal stresses in laminates", styles["title"]),
             Paragraph("Engineering teaching model | 7 October 2026 | SI internally", styles["meta"]),
             Paragraph("Uniform temperature change produces thermal resultants NT and MT. "
                       "ABD solves the free-plate response; local stresses use total strain minus "
                       "the ply thermal strain. The first-ply factor holds thermal stress fixed "
                       "and scales the mechanical loads using Maximum Stress and Tsai-Wu.", styles["body"])]
    for record in DEFAULT_MATERIALS.values():
        story.append(Paragraph(record.name, styles["h"]))
        story.append(Paragraph(f"alpha1 = {record.alpha1 * 1e6:g}, alpha2 = {record.alpha2 * 1e6:g} "
                               f"micrometres/(metre K); alpha12 = 0 in principal axes. "
                               f"Reference = {record.thermal_reference_temperature_c:.3f} deg C. "
                               f"{record.thermal_reference_basis}", styles["body"]))
        story.append(Paragraph("The example uses [0/90]s, illustrative ply thickness 0.125 mm, "
                               "and Nx = 100 kN/m. Final temperatures 20 deg C and -196 deg C "
                               "are chosen scenario inputs, not measured validation data.", styles["small"]))
        material = record.as_thermal_core_material()
        layup = parse_layup("[0,90]s", 0.125e-3)
        stiffness = assemble_laminate_stiffness(layup, [material])
        loads = np.array([100e3, 0, 0, 0, 0, 0], dtype=float)
        mechanical = recover_ply_surfaces(stiffness, layup, [material], loads)
        rows = [["Final T [C]", "dT [K]", "0-ply residual sigma2 [MPa]", "Mechanical factor"]]
        for temperature in (20.0, -196.0):
            delta = temperature - record.thermal_reference_temperature_c
            residual = recover_thermal_response(stiffness, layup, [material], delta)
            _, factor, _ = first_ply_mechanical_load_factor(
                residual, mechanical, StrengthAllowables(**record.as_strengths()))
            rows.append([f"{temperature:g}", f"{delta:.3f}",
                         f"{residual.ply_surfaces[0].local_stress[1] / 1e6:.3f}", f"{factor:.3f}"])
        story.append(_table(rows, [25*mm, 25*mm, 65*mm, 45*mm], regular, bold))
        story.append(Paragraph("A factor of zero means cooling alone reaches or exceeds the "
                               "first-ply screening limit. This is reported as calculated, without "
                               "adjusting properties to obtain agreement.", styles["small"]))
        story.append(Paragraph(f"CTEs: {record.cte_reference} "
                               f'<link href="{record.cte_source_url}">Source document</link>. '
                               f"Temperature: {record.temperature_reference} "
                               f'<link href="{record.temperature_source_url}">Source document</link>.', styles["small"]))
        story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Limits and verification", styles["h"]))
    story.append(Paragraph("Moisture, creep, and temperature-dependent properties are not modelled. "
                           "Cure chemistry, chemical shrinkage and interlaminar stress are excluded. "
                           "Reference temperatures depend on cure history; the Scotchply cure "
                           "temperature is used as an assumed stress-free reference. Cryogenic "
                           "results extrapolate constant room-temperature properties and are not "
                           "validated cryogenic strength predictions. Acceptance tests cover ply CTE "
                           "recovery, symmetry, equal quasi-isotropic expansion, transverse residual "
                           "tension after cooling, net force balance and mechanical-load scaling.", styles["body"]))
    SimpleDocTemplate(str(output), pagesize=A4, rightMargin=22*mm, leftMargin=22*mm,
                      topMargin=16*mm, bottomMargin=16*mm).build(story)
    print(output)


if __name__ == "__main__":
    main()
