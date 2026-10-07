"""Report No. 2 (PDF, English): progressive failure, review corrections and validation status. Reads validation/results.json.

Usage: python reports/make_report_2.py   ->  reports/Report_2_progressive_failure_and_validation.pdf
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from report import APP_URL, _fonts, _styles, _table   # noqa: E402

R = json.loads((ROOT / "validation" / "results.json").read_text(encoding="utf-8"))
CASES = {c["id"]: c for c in R["cases"]}
OUT = ROOT / "reports" / "Report_2_progressive_failure_and_validation.pdf"
REPO = "https://github.com/Artyom09062002/composite-laminate-tool"


def kangal(spec, suffix="primary"):
    return next(r for r in CASES["KANGAL_2020"]["runs"] if r["specimen"] == spec and r["label"].endswith(suffix))


def main() -> None:
    regular, bold = _fonts()
    st = _styles(regular, bold)
    bullet = st["body"].clone("bullet", leftIndent=9, bulletIndent=0, spaceAfter=1.5)
    story = [
        Paragraph("Composite Laminate Tool v3: progressive failure and validation status", st["title"]),
        Paragraph(f"Report No. 2 · 7 October 2026 · Author: Artem · App: {APP_URL} · Code: {REPO}", st["meta"]),
        Paragraph("Educational and screening tool. Not a certified design calculation.", st["meta"]),
        Paragraph("1. Purpose", st["h"]),
        Paragraph("This report documents version 3 of the laminate tool, which now covers a filament-wound pressure vessel with a geodesic dome and a progressive "
                  "(ply-by-ply) failure model. It states what changed after an independent review of the Hashin and progressive-failure code, and reports the first "
                  "attempt to compare the model with published burst-test data. The result of that comparison is mostly negative, and it is reported as such.", st["body"]),
        Paragraph("2. What changed since v2", st["h"]),
    ]
    for text in (
        "<b>Dome:</b> geodesic winding (Clairaut), thickness build-up and membrane resultants along the dome; the cylinder junction and the polar-opening zone are flagged and excluded from the headline value.",
        "<b>Hashin criterion</b> (plane stress, four modes, active mode, strength ratio) reported next to Maximum Stress and Tsai-Wu.",
        "<b>Progressive failure:</b> load factor from first-ply to the last-ply stopping point, failure sequence, ABD rebuilt after every failure, load-strain curve.",
        "<b>Pressure vessel tab:</b> CLT first-ply, Hashin first-ply, last-ply and the netting estimate side by side, with editable degradation factors.",
        "<b>Review corrections</b> (Section 4) and a validation harness (<font name='%s'>validation/</font>). Automated tests: 43 in v2, 120 now, all passing." % regular):
        story.append(Paragraph(text, bullet, bulletText="•"))
    story += [
        Paragraph("3. Method summary", st["h"]),
        Paragraph("<b>Vessel wall.</b> A closed thin cylinder of radius R under pressure p carries N<sub>x</sub> = pR/2 and N<sub>y</sub> = pR. Netting theory (fibres only) balances both "
                  "at the winding angle tan<super>2</super>θ = 2, θ = 54.74°; the app solves the fibre-only equilibrium exactly for any layup. CLT first-ply uses Maximum Stress and Tsai-Wu.", st["body"]),
        Spacer(1, 3),
        Paragraph("<b>Hashin initiation</b> (plane-stress, Hashin-1980-inspired; σ<sub>3</sub>, τ<sub>13</sub>, τ<sub>23</sub> are not assessed). Fibre tension: (σ<sub>1</sub>/X<sub>t</sub>)<super>2</super> + α(τ<sub>12</sub>/S)<super>2</super>, α = 1; "
                  "fibre compression: (σ<sub>1</sub>/X<sub>c</sub>)<super>2</super>; matrix tension: (σ<sub>2</sub>/Y<sub>t</sub>)<super>2</super> + (τ<sub>12</sub>/S)<super>2</super>; matrix compression: "
                  "(σ<sub>2</sub>/2S<sub>T</sub>)<super>2</super> + [(Y<sub>c</sub>/2S<sub>T</sub>)<super>2</super> − 1]σ<sub>2</sub>/Y<sub>c</sub> + (τ<sub>12</sub>/S)<super>2</super>. "
                  "The load factor solves index(λσ) = 1. α = 1 is a chosen setting, and S<sub>T</sub> = Y<sub>c</sub>/(2 tan 53°) is an <b>assumption</b> used when no transverse shear strength is given.", st["body"]),
        Spacer(1, 3),
        Paragraph("<b>Progressive failure</b> (ply discount, load-controlled, linear between failures). At each failure the failed ply is degraded (fibre failure: E<sub>1</sub> × 0.01; "
                  "matrix failure: E<sub>2</sub> and G<sub>12</sub> × 0.1), ABD is rebuilt and the next failure load is found exactly. A ply loaded beyond its original strength again is degraded a second time; "
                  "a third exceedance stops the run (a two-level residual-stiffness termination rule). The degradation factors and this rule are <b>model assumptions, not material data</b>. "
                  "The last-ply value is where the algorithm stops, not a validated ultimate or burst load.", st["body"]),
        Paragraph("4. Independent review and what it changed", st["h"]),
        Paragraph("A second AI model reviewed the Hashin and progressive-failure code in 12 comments. Each was verified by derivation or by running the code before any change: "
                  "3 confirmed as defects, 6 confirmed as claims stronger than the model supports (wording, labelling), 3 partly confirmed, none rejected outright "
                  "(five parts were deliberately not acted on, with reasons in the audit file). The Hashin formulas and the load-factor solver were not changed.", st["body"]),
        Spacer(1, 3),
    ]
    review = [["Finding (confirmed)", "Consequence found by test", "Action"],
              ["Pure in-plane shear with α = 1 gives FT = MT = 1", "Progressive model degraded fibres and matrix in all plies of a UD laminate under pure shear (8 events, E<sub>1</sub> × 0.01 with no fibre stress)",
               "Initiation unchanged; a fibre-tension index driven by its shear term is applied as matrix damage (documented choice, not validated)"],
              ["S<sub>T</sub> = Y<sub>c</sub>/(2 tan 53°) is not a measured property", "The check MC = 1 at σ<sub>2</sub> = −Y<sub>c</sub> holds for any S<sub>T</sub>; the default (92.7 MPa) exceeds S<sub>12</sub> = 68 MPa for T300/5208",
               "Marked ASSUMED in every result; S<sub>T</sub> varied as sensitivity"],
              ["\"Last-ply\" read as an ultimate load", "All residual stiffnesses stay positive; no stability check; load factor never reduced", "Renamed \"model stop\"; held steps flagged"],
              ["Stopping and new failures at the same load", "New failures at the stopping load were dropped from the failure list", "Single batch rule, tested"]]
    from reportlab.platypus import Paragraph as P
    cell = st["cell"]
    story.append(_table([[P(c, cell) if i else c for c in row] if i else row for i, row in enumerate(review)], [47 * mm, 70 * mm, 57 * mm], regular, bold, align_right_from=9))
    story += [
        Paragraph("Not acted on: calibrated mode-specific degradation rules and fracture-energy regularisation (no calibration data, out of scope for a screening model), stability-aware "
                  "solution control, and the claimed dependence on splitting a ply (load factors were identical for 1 to 8 sub-plies in the cases tried; only event counts change).", st["small"]),
        Paragraph("5. Validation against published burst-test data", st["h"]),
    ]
    k1, k2 = kangal("GF_P1"), kangal("GF_P2")
    h1lo, h1hi = [r for r in CASES["KANGAL_2020"]["runs"] if r["specimen"] == "HY_P1"][:2]
    h2lo, h2hi = [r for r in CASES["KANGAL_2020"]["runs"] if r["specimen"] == "HY_P2"][:2]
    alam = CASES["ALAM_2020"]["runs"][0]
    a, imp = alam["pR_N_per_m"], alam["implied_radius_mm_for_measured_mean_burst"]
    ka = [r for r in CASES["KARTAV_2021"]["runs"] if r["failure_location"].startswith("cylindrical")]

    def f(x): return f"{x:.0f}"
    rows = [["Case (source)", "Measured [bar]", "CLT first-ply", "Hashin first-ply", "Last-ply (stop)", "Netting", "Status"]]
    for name, run in (("Kangal GF P1", k1), ("Kangal GF P2", k2)):
        p = run["predicted"]
        rows.append([name, str(run["measured_burst_bar"]), f(p["first_ply_clt_bar"]), f(p["first_ply_hashin_bar"]), f(p["last_ply_bar"]), f(p["netting_bar"]),
                     "composite wall only; steel liner not modelled"])
    for name, lo, hi in (("Kangal hybrid P1", h1lo, h1hi), ("Kangal hybrid P2", h2lo, h2hi)):
        rng = lambda k: f"{lo['predicted'][k]:.0f}–{hi['predicted'][k]:.0f}"
        rows.append([name, str(lo["measured_burst_bar"]), rng("first_ply_clt_bar"), rng("first_ply_hashin_bar"), rng("last_ply_bar"), rng("netting_bar"), "bounds: stack order unsourced"])
    rows.append(["Alam T800S (p·R, kN/m)", f"{CASES['ALAM_2020']['measured_mean_burst_psi'] * 6894.757e-5:.0f} (mean of 3)", f(a["first_ply_clt"] / 1e3), f(a["first_ply_hashin"] / 1e3),
                 f(a["last_ply"] / 1e3), f(a["netting"] / 1e3), f"radius unsourced; equals measured at R = {imp['first_ply_clt']:.0f}–{imp['last_ply']:.0f} mm"])
    rows.append(["Kartav ALCF10–13 (netting)", f"{min(r['measured_burst_bar'] for r in ka)}–{max(r['measured_burst_bar'] for r in ka)}", "n/a", "n/a", "n/a",
                 f"{min(list(r['netting_bar'].values())[0] for r in ka):.0f}–{max(list(r['netting_bar'].values())[0] for r in ka):.0f} (R = 153 mm); "
                 f"{min(list(r['netting_bar'].values())[1] for r in ka):.0f}–{max(list(r['netting_bar'].values())[1] for r in ka):.0f} (R = 76.5 mm)", "radius ambiguous; Al liner; order unsourced"])
    story.append(Paragraph("Four published cases (three usable here) were assembled with an AI research assistant and are <b>unverified</b>. No source reports the inner radius, and the two Type III vessels have a metal liner "
                           "the model does not contain. Pressures in bar unless stated. No parameter was tuned to any measurement.", st["body"]))
    story.append(Spacer(1, 3))
    story.append(_table([[P(c, cell) if i else c for c in row] if i else row for i, row in enumerate(rows)], [30 * mm, 21 * mm, 16 * mm, 16 * mm, 16 * mm, 30 * mm, 45 * mm], regular, bold, align_right_from=9))
    story.append(Spacer(1, 4))
    chart = Image(str(ROOT / "validation" / "predicted_vs_measured.png"), width=112 * mm, height=112 * mm * 4.6 / 6.4)
    story.append(KeepTogether([chart]))
    gain1 = k1["diagnostic_gain_over_bare_liner_bar"]["using_mean_liner_657"]
    gain2 = k2["diagnostic_gain_over_bare_liner_bar"]["using_mean_liner_657"]
    story += [
        Paragraph("<b>Reading.</b> The comparison cannot confirm or reject the model. (i) The composite-only netting estimate is 0.26 of the measured total for the Kangal glass vessels, as expected without the liner. "
                  f"(ii) The measured gain over the bare steel liner (mean 657 bar) is {gain1} and {gain2} bar against netting 242 and 232 bar (ratios {k1['diagnostic_netting_over_gain_mean_liner']:.2f} and {k2['diagnostic_netting_over_gain_mean_liner']:.2f}); "
                  "this is a plausibility check only, since a yielding liner does not share load additively and the bare liners themselves scatter by 622–692 bar. "
                  f"(iii) First-ply is {k1['predicted']['first_ply_hashin_bar']:.0f} bar, about 2 % of burst: matrix cracking, not burst. "
                  "(iv) The last-ply value moves from 64 to 243 bar with the unsourced stack order of the same 12 plies and by a factor of 3.5 over the residual factors, while netting stays at 242 bar. "
                  "(v) For Alam the model matches the measured burst only if R is 45–52 mm, to be compared with the paper's figures. "
                  "(vi) Kartav's published radius (153 mm) gives only 29–32 % of the measured burst even for the cylinder failures, i.e. it is inconsistent with the burst values; this cannot be resolved without the paper's Figure 1.", st["body"]),
        Paragraph("<b>Likely causes of the gaps:</b> liner not modelled; dome and end effects; fibre-to-ply strength translation (netting uses the ply X<sub>t</sub>); unsourced radius, dome and stack order; "
                  "free-plate CLT for unsymmetric walls; test scatter (919 vs 879 bar for one design, 6 % between identical Kartav configurations).", st["body"]),
        Paragraph("6. Limits", st["h"]),
        Paragraph("Not modelled: liner and boss, dome progressive failure, interlaminar stresses and delamination, thermal and cure stresses, moisture and temperature, fatigue, impact, holes and concentrators, "
                  "manufacturing defects, fibre kinking, crack growth, leakage and stability of the softening path. Strengths are literature values, not qualified allowables. "
                  "Results are valid only for a real ply-by-ply discretisation; there is no fracture-energy regularisation.", st["body"]),
        Paragraph("7. Next steps", st["h"]),
    ]
    for text in ("Read the radius, polar opening and dome from the paper figures (Alam, Kangal, Kartav) and re-run <font name='%s'>validation/run_validation.py</font>." % regular,
                 "Prefer a Type IV case with a published burst value (Lüders 2025: extract the burst event from the public CSV) so that the liner does not dominate.",
                 "Add the liner as a simple load-sharing element only when its properties are sourced.",
                 "Thermal residual stresses (cure and cryogenic), then layup optimisation as a labelled screening tool.",
                 "Repeat the stack-order test with a shell-restrained wall instead of free-plate CLT."):
        story.append(Paragraph(text, bullet, bulletText="•"))
    story += [
        Paragraph("8. AI workflow", st["h"]),
        Paragraph("Two AI models were used, and each reviewed the other's work. Claude wrote and ran the code and verified every review comment by derivation or by running the code before acting. "
                  "ChatGPT assembled the published burst-test data and acted as independent reviewer of the dome module (10 comments: 4 confirmed, 6 rejected as errors after verification) and of the "
                  "Hashin and progressive-failure code (12 comments, Section 4). Claude in turn checked ChatGPT's data for internal consistency and recorded 11 flags, among them the missing inner radius in every source. "
                  "The list of confirmed and rejected review comments, with reasons, is in <font name='%s'>verification/AUDIT.md</font>, with per-round tables in <font name='%s'>verification/REVIEW_C3.md</font> and "
                  "<font name='%s'>verification/REVIEW_C4.md</font>. Reviewer remarks that cite the literature were not independently checked against the sources." % (regular, regular, regular), st["body"]),
    ]
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=13 * mm, bottomMargin=13 * mm,
                            title="Composite Laminate Tool v3: progressive failure and validation status", author="Artem")
    doc.build(story)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
