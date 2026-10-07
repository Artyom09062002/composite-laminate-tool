"""Build the chart and the README table from validation/results.json (Task C4). Run after run_validation.py."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
R = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
CASES = {c["id"]: c for c in R["cases"]}
COLORS = {"first": "#e07b22", "last": "#7b3fa0", "netting": "#087f8c"}


def kangal_runs():
    out = {}
    for run in CASES["KANGAL_2020"]["runs"]:
        out.setdefault(run["specimen"], []).append(run)
    return out


def chart(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 4.6), dpi=200)
    ax.plot([0, 1600], [0, 1600], color="#8a9aa5", lw=1, ls="--", zorder=0)
    ax.text(1150, 1260, "y = x", color="#5b7080", fontsize=8)
    runs = kangal_runs()
    for spec in ("GF_P1", "GF_P2"):
        primary = next(r for r in runs[spec] if r["label"].endswith("primary"))
        x, p = primary["measured_burst_bar"], primary["predicted"]
        ax.scatter([x], [p["first_ply_hashin_bar"]], color=COLORS["first"], marker="o", s=34, zorder=3)
        ax.scatter([x], [p["last_ply_bar"]], color=COLORS["last"], marker="o", s=34, zorder=3)
        ax.scatter([x], [p["netting_bar"]], color=COLORS["netting"], marker="o", s=34, zorder=3)
    for spec in ("HY_P1", "HY_P2"):
        lo, hi = runs[spec][0], runs[spec][1]
        x = lo["measured_burst_bar"]
        for key, color in (("last_ply_bar", COLORS["last"]), ("netting_bar", COLORS["netting"])):
            ax.plot([x, x], [lo["predicted"][key], hi["predicted"][key]], color=color, lw=3, alpha=0.55, solid_capstyle="butt", zorder=2)
    for row in CASES["KARTAV_2021"]["runs"]:
        if not row["failure_location"].startswith("cylindrical"):
            continue
        values = list(row["netting_bar"].values())
        ax.plot([row["measured_burst_bar"]] * 2, [min(values), max(values)], color=COLORS["netting"], lw=1.4, marker="_", ms=7, zorder=2)
    ax.annotate("Kangal (steel liner): dots = glass COPV,\ncomposite wall only, liner not modelled;\nbars = two hoop-material assignments:\nall glass / all carbon, order unsourced", (880, 330),
                (60, 520), fontsize=7.5, color="#173042", arrowprops=dict(arrowstyle="-", color="#8a9aa5", lw=0.8))
    ax.annotate("Kartav (Al liner): bar from R = 153 mm\n(low end) to R = 76.5 mm (high end)", (1415, 420), (1000, 120), fontsize=7.5,
                color="#173042", arrowprops=dict(arrowstyle="-", color="#8a9aa5", lw=0.8))
    for label, color in (("Hashin first-ply", COLORS["first"]), ("Last-ply (model stop)", COLORS["last"]), ("Netting (fibres only)", COLORS["netting"])):
        ax.scatter([], [], color=color, label=label, s=34)
    ax.set_xlim(0, 1600); ax.set_ylim(0, 1600)
    ax.set_xlabel("Measured burst pressure [bar]"); ax.set_ylabel("Predicted by the model [bar]")
    ax.set_title("Predicted vs measured burst pressure (Alam: no radius, not plotted)", fontsize=9, color="#173042")
    ax.legend(loc="upper left", fontsize=7.5, frameon=False)
    ax.grid(color="#dfe8ec", lw=0.6); ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)


def fmt(x, n=1):
    return f"{x:.{n}f}"


def tables() -> str:
    runs = kangal_runs()
    lines = ["**Table 1. Kangal 2020, glass-fibre COPV (Type III): model of the composite wall only vs the measured TOTAL burst of the vessel (bar).** "
             "Radius derived from Table 1 (see below), ply thickness as measured, stack as notated, assumed transverse shear strength, default degradation factors.", "",
             "| Specimen | Measured | Paper FE | CLT first-ply | Hashin first-ply | Last-ply (model stop) | Netting | Netting / measured | Measured minus mean bare liner (657) | Netting / that gain |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for spec in ("GF_P1", "GF_P2"):
        run = next(r for r in runs[spec] if r["label"].endswith("primary")); p = run["predicted"]
        gain = run["diagnostic_gain_over_bare_liner_bar"]["using_mean_liner_657"]
        lines.append(f"| {spec} | {run['measured_burst_bar']} | {run['paper_fe_bar']} | {fmt(p['first_ply_clt_bar'])} | {fmt(p['first_ply_hashin_bar'])} | {fmt(p['last_ply_bar'])} | "
                     f"{fmt(p['netting_bar'])} | {p['netting_over_measured']:.2f} | {gain} | {run['diagnostic_netting_over_gain_mean_liner']:.2f} |")
    for spec in ("HY_P1", "HY_P2"):
        lo, hi = runs[spec][0], runs[spec][1]
        rng = lambda k: f"{fmt(lo['predicted'][k])} to {fmt(hi['predicted'][k])}"
        lines.append(f"| {spec} (two assignments) | {lo['measured_burst_bar']} | {lo['paper_fe_bar']} | {rng('first_ply_clt_bar')} | {rng('first_ply_hashin_bar')} | {rng('last_ply_bar')} | "
                     f"{rng('netting_bar')} | {lo['predicted']['netting_over_measured']:.2f} to {hi['predicted']['netting_over_measured']:.2f} | n/a | n/a |")
    lines += ["", "Hybrid rows show two assumed assignments (all hoop plies glass or all hoop plies carbon). Stack order is UNSOURCED; these scenarios do not prove global bounds and are not vessel predictions.", "",
              "**Table 2. SENSITIVITY (not predictions): GF_P1, one change at a time (bar).**", "",
              "| Change from the primary run | CLT first-ply | Hashin first-ply | Last-ply (model stop) | Netting |", "|---|---|---|---|---|"]
    for run in runs["GF_P1"]:
        p = run["predicted"]
        label = "primary run" if run["label"].endswith("primary") else run["label"].split("sensitivity: ")[1]
        lines.append(f"| {label} | {fmt(p['first_ply_clt_bar'])} | {fmt(p['first_ply_hashin_bar'])} | {fmt(p['last_ply_bar'])} | {fmt(p['netting_bar'])} |")
    alam = CASES["ALAM_2020"]["runs"][0]
    a, imp = alam["pR_N_per_m"], alam["implied_radius_mm_for_measured_mean_burst"]
    lines += ["", f"**Table 3. Alam 2020, T800S Type IV: no pressure can be predicted (inner radius UNSOURCED).** Stack [-13, +13, 88, -13, +13], ply thicknesses 0.033/0.033/0.009/0.033/0.033 in, "
              f"S_T = S_L = 14 ksi from the pasted text. Measured bursts 2282, 2327, 2391 psi (mean {CASES['ALAM_2020']['measured_mean_burst_psi']:.0f} psi = {CASES['ALAM_2020']['measured_mean_burst_psi'] * 6894.757 / 1e6:.2f} MPa). "
              "The model gives p R; the predicted pressure is (p R)/R for the radius R read from Figures 1-3.", "",
              "| Quantity | p R [kN/m] | Radius at which it would equal the measured mean burst [mm] |", "|---|---|---|"]
    for key, name in (("first_ply_clt", "CLT first-ply"), ("first_ply_hashin", "Hashin first-ply"), ("last_ply", "Last-ply (model stop)"), ("netting", "Netting (fibres only)")):
        lines.append(f"| {name} | {a[key] / 1e3:.0f} | {imp[key]:.0f} |")
    lines += ["", "**Table 4. Kartav 2021 (Al liner, Type III): netting diagnostic only, configurations whose failure was reported in the cylindrical mid-region (bar).**", "",
              "| Config | Measured | Netting, R = 153 mm (as published) | Netting, 153 mm read as a diameter (R = 76.5 mm) |", "|---|---|---|---|"]
    for row in CASES["KARTAV_2021"]["runs"]:
        if row["failure_location"].startswith("cylindrical"):
            v = list(row["netting_bar"].values())
            lines.append(f"| {row['config']} | {row['measured_burst_bar']} | {v[0]:.0f} | {v[1]:.0f} |")
    return "\n".join(lines)


def main() -> None:
    chart(ROOT / "predicted_vs_measured.png")
    block = tables()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    start, end = "<!-- C4-TABLES-START -->", "<!-- C4-TABLES-END -->"
    if start in readme:
        a, b = readme.index(start), readme.index(end) + len(end)
        readme = readme[:a] + f"{start}\n{block}\n{end}" + readme[b:]
        (ROOT / "README.md").write_text(readme, encoding="utf-8")
    print(block)


if __name__ == "__main__":
    main()
