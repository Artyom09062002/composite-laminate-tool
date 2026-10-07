# Composite Laminate Design & Analysis Tool

**Live app:** <https://composite-laminate-tool.streamlit.app/>  ·  **Author:** Artyom

A Streamlit application that makes Classical Lamination Theory (CLT) visible step by step:

`material → Q → Q̄ → stacking sequence → ABD → mid-plane strain and curvature → ply stresses → first-ply failure (Maximum Stress, Tsai–Wu, Hashin) → progressive failure to the last ply`

You choose the material (two cited datasets or your own values), the layup (angle, thickness and material of every ply, so hybrid stacks are possible) and the six load resultants (`Nx, Ny, Nxy, Mx, My, Mxy`). Every tab shows the equation, the numbers and a short interpretation. The app also gives the laminate's equivalent engineering constants (Ex, Ey, Gxy, νxy, flexural moduli) and exports a PDF report of the current analysis.

Further tabs compare 2–5 candidate layups, screen a filament-wound cylinder under internal pressure (first-ply pressure from CLT, the progressive-failure last-ply pressure and the netting-theory burst estimate, with the ±54.7° winding angle) and a geodesic dome, connect the model to manufacturing processes and defects, show two application examples, and check the code against a published worked example.

## Run locally

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
python -m unittest discover -s tests -v
```

On Windows, double-clicking `START_APP.cmd` creates a virtual environment, installs the dependencies and opens the app; `START_APP.cmd --check` runs the tests only.

## Conventions

- SI units internally (Pa, m, N). Display: moduli and stresses in GPa/MPa, thickness in mm, loads in kN/m and N·m/m, A in MN/m, B in N, D in N·m, strain in µε, curvature in 1/m.
- Plane-stress order `[σ1, σ2, τ12]` and `[ε1, ε2, γ12]`, with engineering shear strain.
- Positive ply angle: counter-clockwise from the global x-axis to the fibre axis 1.
- Plies are listed from the `−h/2` face to the `+h/2` face; `z` is measured upward from the mid-plane.

## Code layout

| Path | Content |
|---|---|
| `core/` | CLT mechanics: `Q`, `Q̄`, `A/B/D`, engineering constants, laminate response, Maximum Stress, Tsai–Wu and Hashin (`failure.py`), progressive failure (`progressive.py`), cylinder resultants and netting theory, geodesic dome (`dome.py`) |
| `workflow.py` | Layup parsing, ply-table validation, symmetry/balance checks, design summaries, pressure-vessel screening |
| `report.py` | PDF report of the current analysis (ReportLab; DejaVu fonts in `assets/fonts`, Bitstream Vera licence) |
| `materials/` | Reference material data with sources |
| `examples/` | Wind-blade spar-cap example (unsymmetric thick panel) |
| `app.py` | Streamlit interface |
| `tests/` | 120 automated tests (mechanics properties, reference values, hybrids, bending, engineering constants, pressure vessel, dome, Hashin, progressive failure, review regressions, app wiring, report, input validation) |
| `verification/` | Reference-value script, the engineering audit log (`AUDIT.md`) and the verdicts on the two independent reviews: dome (`REVIEW_C3.md`) and Hashin / progressive failure (`REVIEW_C4.md`) |
| `validation/` | Burst-test cases (`data.json`, unverified), the runner `run_validation.py`, `results.json`, tables and chart in `README.md`; result: no like-for-like comparison was possible (see its README) |
| `reports/` | Report No. 2 (PDF) and its generator |

## Data sources

- Lamina data: the classic T300/5208 graphite/epoxy and Scotchply 1002 glass/epoxy values (Tsai & Hahn, *Introduction to Composite Materials*, 1980; Kaw, *Mechanics of Composite Materials*, 2nd ed., CRC Press, 2006), as tabulated in [Martinez & Bishay, *Composites Part C* (2021), Table 2](https://www.csun.edu/~pbishay/pubs/Martinez_Bishay_CPC_2020.pdf). The 0.125 mm ply thickness is an illustrative value.
- Verification: the `[0/90]s` stiffness is compared with a [published worked CLT example](https://mpolyco.com/learn/classical-laminate-theory) (`A₁₁ = 48.039 MN/m`, `D₁₁ = 1.671 N·m`).
- Spar-cap example: glass material data from Sandia report SAND2011-3779 (SNL100-00 blade), Table 19.
- Pressure vessel: thin-wall equilibrium and netting analysis as in standard filament-winding texts (e.g. S. T. Peters (ed.), *Composite Filament Winding*, ASM International, 2011).
- Manufacturing and aerospace context: [FAA AC 21-26A](https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_21-26A.pdf), [FAA AC 20-107B](https://www.faa.gov/airports/resources/advisory_circulars/index.cfm/go/document.information/documentNumber/20-107B).

## How AI was used

The code was written with AI coding assistants, working under written rules. [AGENTS.md](AGENTS.md) fixes the units, sign conventions and the rule that equations in `core/` change only with an engineering justification and a regression test. [CLAUDE.md](CLAUDE.md) is the brief for a separate AI review pass. AI output was accepted only after the equations, units, limiting cases and the published example were checked. The review passes found real problems (a wrong reference value in a test, hidden default strengths, a wrong formula in a UI caption, a failure of the Tsai–Wu strength ratio under pure bending); each was fixed and covered by a test. Two AI models reviewed each other's work: one wrote and ran the code, the other reviewed the dome module and the Hashin / progressive-failure code, and the first checked the second's research data. Every review comment was verified before acting; the confirmed and rejected comments are listed in [verification/AUDIT.md](verification/AUDIT.md).

## Limitations

Linear-elastic plies in plane stress, perfect bonding and thin-plate (Kirchhoff) kinematics. Not modelled: cure/thermal residual stresses, transverse shear, interlaminar stresses, delamination, buckling and environmental effects. Hashin is a plane-stress, Hashin-1980-inspired initiation criterion (alpha = 1 is a chosen setting; the transverse shear strength Yc/(2 tan 53°) is assumed when none is given). Progressive failure is a ply-discount screening model: its degradation factors (E1 ×0.01 after fibre failure, E2 and G12 ×0.1 after matrix failure) and the two-level termination rule are model assumptions, not material data, and the last-ply pressure is where this algorithm stops, not a validated ultimate or burst load; it changes with the factors (a factor of 3.5 over a reasonable range) and, for unsymmetric walls, with the stack order. It is applied to the cylindrical wall only, with one computational ply per physical ply and no stability analysis. Also not modelled: open holes, fatigue, impact, moisture and temperature, manufacturing defects, fibre kinking, crack growth, leakage and interlaminar strength. Comparison with published burst tests was attempted (`validation/`) and could not be completed like for like: no source gives the inner radius and the Type III vessels have a metal liner the model does not contain. The dome part uses membrane theory with helical plies only (no end-fittings, liner or slip); near the cylinder/dome junction and the polar opening it is not a strength prediction. Strengths are literature values, not qualified allowables, and Tsai–Wu uses the assumed interaction term `F12 = −0.5√(F11·F22)`. The tool is for learning and first-ply screening, not for certified design.
