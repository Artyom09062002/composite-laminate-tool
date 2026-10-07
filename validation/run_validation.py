"""Run the model on every case in validation/data.json and write validation/results.json (Task C4).

Rules followed by this script
-----------------------------
* Every number comes from data.json (as pasted, UNVERIFIED) or is DERIVED from it with the derivation recorded in the output.
* Nothing is tuned to a measurement. A run is labelled "primary" (inputs as published or derived) or "sensitivity" (one input
  changed to show how much it matters); sensitivities are never used as the prediction.
* Where an input is UNSOURCED the case is not run for that quantity and the result says why.
* The model predicts the load that the COMPOSITE WALL of a cylinder can carry (CLT first-ply, Hashin first-ply, last-ply
  = where the discount algorithm stops, and fibre-only netting). It has no liner, dome or end-fitting model, so for a
  Type III vessel (steel/aluminium liner) it is not like-for-like with the measured total burst pressure.

Usage:  python validation/run_validation.py
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import StrengthAllowables                                   # noqa: E402
from core.progressive import DegradationRules, progressive_failure   # noqa: E402
from core.vessel import cylinder_resultants, netting_pressure        # noqa: E402
from workflow import screen_cylinder                                 # noqa: E402

DATA = json.loads((ROOT / "validation" / "data.json").read_text(encoding="utf-8"))
CASES = {case["id"]: case for case in DATA["cases"]}
MPA, BAR, PSI, KSI, IN = 1e6, 1e5, 6894.757293168, 6.894757293168e6, 0.0254
UNSOURCED = "UNSOURCED"


def val(node):
    """The numeric value of a data.json leaf ({'value': x, ...} or a bare number)."""
    node = node["value"] if isinstance(node, dict) and "value" in node else node
    if node == UNSOURCED or isinstance(node, str):
        raise ValueError(f"input is {node!r}")
    return float(node)


def lamina(card: dict, scale: float, keys: dict) -> tuple[dict, StrengthAllowables]:
    """Build a core material and strengths from a data.json lamina card (compression strengths as magnitudes)."""
    material = {"E1": val(card[keys["E1"]]) * scale, "E2": val(card[keys["E2"]]) * scale,
                "G12": val(card[keys["G12"]]) * scale, "v12": val(card[keys["v12"]])}
    strengths = {k: abs(val(card[keys[k]])) * scale for k in ("Xt", "Xc", "Yt", "Yc")}
    strengths["S"] = abs(val(card[keys["S"]])) * scale
    return material, strengths


def run_model(layup, materials, strength_kwargs, radius_m, *, st=None, rules=None):
    """Predicted wall pressures [Pa] at radius ``radius_m`` plus the failure sequence summary."""
    strengths = [StrengthAllowables(**kw, St=(st[i] if st else None)) for i, kw in enumerate(strength_kwargs)]
    screen = screen_cylinder(layup, materials, strengths, radius_m)
    unit = cylinder_resultants(1.0, radius_m)
    prog = progressive_failure(layup, materials, strengths, unit, rules or DegradationRules())
    first = prog.events[0]
    return {
        "first_ply_clt_pa": screen.first_ply_pressure_pa, "first_ply_clt_criterion": screen.first_ply_criterion,
        "first_ply_clt_ply": screen.first_ply_ply,
        "first_ply_hashin_pa": prog.first_ply_load_factor,
        "first_hashin_event": f"ply {first.ply} {first.surface.lower()} face, {first.mode}",
        "last_ply_pa": prog.last_ply_load_factor,
        "last_ply_over_first_ply_hashin": prog.last_ply_load_factor / prog.first_ply_load_factor,
        "netting_pa": screen.netting_pressure_pa,
        "n_failure_events": len(prog.events), "cascade_steps": prog.cascade_steps,
        "stop_reason": prog.collapse_reason,
        "transverse_shear_assumed": any(s.St is None for s in strengths),
    }


def mpa(pa):  # round for readability, keep the full value elsewhere
    return None if pa is None else round(pa / MPA, 3)


def summarise(pred: dict, unit: float, unit_name: str, measured: float | None) -> dict:
    out = {k: (v / unit if k.endswith("_pa") else v) for k, v in pred.items()}
    out = {k.replace("_pa", f"_{unit_name}"): v for k, v in out.items()}
    if measured:
        for key in ("first_ply_clt", "first_ply_hashin", "last_ply", "netting"):
            out[f"{key}_over_measured"] = pred[f"{key}_pa"] / unit / measured
    return out


def stack(angles, thicknesses, mats):
    return [{"theta": float(a), "t": float(t), "mat": int(m)} for a, t, m in zip(angles, thicknesses, mats)]


# ---------------------------------------------------------------------------------------------------------------
def kangal() -> dict:
    case = CASES["KANGAL_2020"]
    g = case["geometry"]
    wall = val(g["liner_wall_thickness"]) * 1e-3
    keys = {"E1": "E1", "E2": "E2=E3", "G12": "G12=G13", "v12": "nu12=nu13", "Xt": "Xt", "Xc": "Xc", "Yt": "Yt", "Yc": "Yc", "S": "S12"}
    glass, glass_s = lamina(case["lamina"]["glass_epoxy"], MPA, keys)
    carbon, carbon_s = lamina(case["lamina"]["carbon_epoxy"], MPA, keys)
    bursts = case["burst"]["tests"]
    nominal = [11, -11, 90, 90] * 3                                   # [±11/90_2]_3, text; stacking direction UNSOURCED
    specimens = [("GF_P1", "P1", "P1", bursts["GF_COPV"]["P1"]), ("GF_P2", "P2", "P2", bursts["GF_COPV"]["P2"]),
                 ("HY_P1", "P1", "P1", bursts["GF_CF_hybrid_COPV"]["P1"]), ("HY_P2", "P2", "P2", bursts["GF_CF_hybrid_COPV"]["P2"])]
    out_runs, notes = [], []
    derived_note = ("Radius is DERIVED, not published: Table 1 labels its diameters only 'average'. (COPV diameter - liner diameter)/2 equals "
                    "12 x measured ply thickness (P1 GF: 2.50 vs 2.496 mm), so the liner diameter is the liner OUTER diameter. "
                    "Composite inner radius = liner diameter/2; pressure acts on the liner bore, radius = liner diameter/2 - 4.5 mm wall.")
    # measured ply thickness lives under layup
    for spec, liner_key, _, burst in specimens:
        liner_d = val(g["liner_average_diameter"][liner_key]) * 1e-3
        t_ply = val(case["layup"]["measured_avg_ply_thickness"][spec]) * 1e-3
        r_pressure, r_composite = liner_d / 2 - wall, liner_d / 2
        bare_liner = bursts["bare_steel_liner"]
        measured_mpa = burst * BAR / MPA
        base = dict(specimen=spec, measured_burst_bar=burst, measured_burst_mpa=measured_mpa,
                    bare_liner_burst_bar=bare_liner[liner_key], paper_fe_bar=bursts["GF_COPV" if spec.startswith("GF") else "GF_CF_hybrid_COPV"]["FE"],
                    ply_thickness_mm=t_ply * 1e3, radius_pressure_mm=r_pressure * 1e3, radius_composite_inner_mm=r_composite * 1e3)
        if spec.startswith("GF"):
            lay = stack(nominal, [t_ply] * 12, [0] * 12)
            pred = run_model(lay, [glass], [glass_s], r_pressure)
            run = {"label": f"{spec} primary", "kind": "primary", **base, "stack_inner_to_outer": nominal,
                   "predicted": summarise(pred, BAR, "bar", burst)}
            # plausibility diagnostic only: measured burst minus the bare steel liner (two liners, 622 and 692 bar). Load sharing
            # of a yielding liner and the composite is NOT additive, and the liner properties are UNSOURCED.
            mean_liner = case["burst"]["paper_reported_averages"]["bare_steel_liner"]
            run["diagnostic_gain_over_bare_liner_bar"] = {"using_mean_liner_657": burst - mean_liner,
                                                          "range_using_622_and_692": [burst - max(bare_liner.values()), burst - min(bare_liner.values())]}
            run["diagnostic_netting_over_gain_mean_liner"] = pred["netting_pa"] / BAR / (burst - mean_liner)
            out_runs.append(run)
            # sensitivities (one change at a time)
            sens = []
            sens.append(("radius = composite inner radius", run_model(lay, [glass], [glass_s], r_composite)))
            # stack order is UNSOURCED. (Reversing the whole stack, or putting the hoop pair first, is a mirror image and gives identical numbers, so these are not tests.)
            hoop_first = [90, 11, -11, 90] * 3
            blocks = [11, -11] * 3 + [90] * 6
            sens.append(("stack order [90,+11,-11,90]x3 (hoop plies on both sides of each helical pair)", run_model(stack(hoop_first, [t_ply] * 12, [0] * 12), [glass], [glass_s], r_pressure)))
            sens.append(("stack order [+11,-11]x3 then 90x6 (blocks)", run_model(stack(blocks, [t_ply] * 12, [0] * 12), [glass], [glass_s], r_pressure)))
            t_fe = val(case["layup"]["ply_thickness_FE"]) * 1e-3
            sens.append(("ply thickness 0.2 mm (FE value) instead of measured", run_model(stack(nominal, [t_fe] * 12, [0] * 12), [glass], [glass_s], r_pressure)))
            for name, st in (("St = S12 (assumed)", glass_s["S"]), ("St = 0.5 S12 (assumed)", 0.5 * glass_s["S"])):
                sens.append((f"Hashin {name} instead of Yc/(2 tan 53)", run_model(lay, [glass], [glass_s], r_pressure, st=[st])))
            for name, rules in (("residual factors E1 0.001 / E2,G12 0.01", DegradationRules(0.001, 0.01, 0.01)),
                                ("residual factors E1 0.1 / E2,G12 0.3", DegradationRules(0.1, 0.3, 0.3)),
                                ("residual factors 0.5 / 0.5 / 0.5", DegradationRules(0.5, 0.5, 0.5)),
                                ("fibre failure also removes E2, G12 (x0.1)", DegradationRules(0.01, 0.1, 0.1, 0.1, 0.1))):
                sens.append((name, run_model(lay, [glass], [glass_s], r_pressure, rules=rules)))
            for name, pred_s in sens:
                out_runs.append({"label": f"{spec} sensitivity: {name}", "kind": "sensitivity", "specimen": spec,
                                 "predicted": summarise(pred_s, BAR, "bar", burst)})
        else:
            # hybrid: the 12-ply stack order is UNSOURCED (Figure 4b). Bounds only: all hoop plies glass / all hoop plies carbon.
            lay_lo = stack(nominal, [t_ply] * 12, [0] * 12)
            lay_hi = stack(nominal, [t_ply] * 12, [1 if a == 90 else 0 for a in nominal])
            for name, lay in (("bound: all hoop plies glass", lay_lo), ("bound: all hoop plies carbon (upper)", lay_hi)):
                pred = run_model(lay, [glass, carbon], [glass_s, carbon_s], r_pressure)
                out_runs.append({"label": f"{spec} sensitivity: {name}", "kind": "sensitivity", **base,
                                 "predicted": summarise(pred, BAR, "bar", burst),
                                 "note": "hybrid stack order UNSOURCED (Figure 4b only): a bound, not a prediction"})
    return {"id": "KANGAL_2020", "data_status": case["status"], "model_scope": "cylinder wall, composite only (steel liner NOT modelled)",
            "derivation": derived_note, "runs": out_runs,
            "not_run": [{"item": "total burst of the Type III vessel", "reason": "34CrMo4 liner properties UNSOURCED; no liner/composite load-sharing model"},
                        {"item": "hybrid prediction", "reason": "12-ply hybrid stack order UNSOURCED; only bounds given"},
                        {"item": "dome", "reason": "dome profile and polar opening UNSOURCED; failures were cylindrical"}]}


def alam() -> dict:
    case = CASES["ALAM_2020"]
    lam = case["lamina"]
    material = {"E1": val(lam["E1"]) * KSI, "E2": val(lam["E2"]) * KSI, "G12": val(lam["G12"]) * KSI, "v12": val(lam["nu12"])}
    strengths = {"Xt": val(lam["XT"]) * KSI, "Xc": val(lam["XC"]) * KSI, "Yt": val(lam["YT"]) * KSI, "Yc": val(lam["YC"]) * KSI, "S": val(lam["SL"]) * KSI}
    st = [val(lam["SL"]) * KSI]                                       # text: S_L = S_T = 14 ksi (Hashin definition)
    plies = case["layup"]["plies"]
    angles = [p["angle_deg"] for p in plies]
    thick = [p["thickness_in"] * IN for p in plies]
    tests = case["burst"]["tests"]
    mean_psi = sum(tests) / len(tests)
    unit_radius = 1.0                                                  # R = 1 m: results are p*R in N/m
    lay = stack(angles, thick, [0] * 5)
    runs = []
    for name, lay_x, kind in (("primary: stack as listed (ply 1 first)", lay, "primary"),):
        pred = run_model(lay_x, [material], [strengths], unit_radius, st=st)
        # with R = 1 m the "pressure" is p*R in N/m; implied radius = p*R / measured burst
        entry = {"label": f"ALAM {name}", "kind": kind, "stack_ply1_to_ply5_deg": [p["angle_deg"] for p in plies],
                 "pR_N_per_m": {k.replace("_pa", ""): v for k, v in pred.items() if k.endswith("_pa")},
                 "implied_radius_mm_for_measured_mean_burst": {k.replace("_pa", ""): v / (mean_psi * PSI) * 1e3 for k, v in pred.items() if k.endswith("_pa")},
                 "hashin_first_event": pred["first_hashin_event"], "stop_reason": pred["stop_reason"]}
        runs.append(entry)
    return {"id": "ALAM_2020", "data_status": case["status"], "model_scope": "cylinder wall (Type IV: polymer liner assumed to carry no load)",
            "measured_burst_psi": tests, "measured_mean_burst_psi": mean_psi, "paper_fe_psi_range": case["burst"]["fe"]["range"],
            "result_form": "p*R [N/m] and the radius at which each prediction would equal the measured mean burst. No pressure is predicted: the "
                           "inner radius is UNSOURCED (Figures 1-3). p_pred = (p*R)/R once R is read from the figure; no radius is assumed here.",
            "runs": runs,
            "not_run": [{"item": "predicted burst pressure vs measured", "reason": "inner radius, wall/liner thickness, dome UNSOURCED"}]}


def kartav() -> dict:
    case = CASES["KARTAV_2021"]
    lam = case["lamina"]["carbon_epoxy"]
    x_t = val(lam["Xt"]) * MPA
    t_h = val(case["layup"]["helical_layer_thickness"]) * 1e-3
    t_o = val(case["layup"]["hoop_layer_thickness"]) * 1e-3
    radius_cases = {"R = 153 mm (as published, 'average radius')": 0.153, "R = 76.5 mm (153 mm read as a diameter)": 0.0765}
    rows = []
    for name, cfg in case["layup"]["configurations_Table2"].items():
        angles = [14.0] * cfg["helical"] + [90.0] * cfg["hoop"]
        thick = [t_h] * cfg["helical"] + [t_o] * cfg["hoop"]
        layup = stack(angles, thick, [0] * len(angles))
        exp = case["burst"]["tests"][name]
        row = {"config": name, "helical_layers": cfg["helical"], "hoop_layers": cfg["hoop"], "measured_burst_bar": exp["exp"],
               "failure_location": exp["failure"], "netting_bar": {}}
        for label, radius in radius_cases.items():
            row["netting_bar"][label] = netting_pressure(layup, [x_t] * len(layup), radius) / BAR
        rows.append(row)
    return {"id": "KARTAV_2021", "data_status": case["status"], "model_scope": "netting diagnostic only (fibre strength = ply Xt), cylinder wall, order-independent",
            "runs": rows,
            "not_run": [{"item": "CLT first-ply, Hashin first-ply, last-ply", "reason": "ply-by-ply stack order UNSOURCED (graphical only); doily G12 UNSOURCED"},
                        {"item": "comparison with measured burst", "reason": "Al 6061-T6 liner properties UNSOURCED; radius ambiguous; ALCF1-9 failed in the DOMES (a cylinder-wall model does not apply)"}],
            "note": "Netting from the cylinder layup (9 helical +/-14 layers of 0.25 mm and N hoop layers of 0.2 mm). Doily layers belong to the domes and are excluded."}


def main() -> None:
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    results = {"_meta": {"task": "C4", "date": "2026-10-07", "code": f"working tree on top of commit {commit}",
                         "input_status": "data.json is UNVERIFIED (pasted from a ChatGPT research answer); no original PDF was opened",
                         "tuning": "none: no parameter was adjusted to any measurement; 'sensitivity' runs change one input and are never the prediction",
                         "degradation_defaults": "E1 x0.01 after fibre failure, E2 and G12 x0.1 after matrix failure (assumptions, not material data)",
                         "transverse_shear": "St = Yc/(2 tan 53 deg) ASSUMED unless the source supplies it (Alam: S_T = 14 ksi from the pasted text)"},
               "cases": [kangal(), alam(), kartav()]}
    (ROOT / "validation" / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote validation/results.json")


if __name__ == "__main__":
    main()
