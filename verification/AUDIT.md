# Engineering audit log

The code was written with AI coding assistants. An AI-written change was accepted only after it was checked against the hand-derived equations, limiting cases, a published worked example and automated tests. This file records what those checks found and what was changed.

## v4 refinement audit - 7 October 2026

Baseline: R0 commit `116a072`. User scope: complete the AI/application stages of PLAN_v4_refine_no_new_features; personal A1-A5 are excluded. Optional R6 needs the supplied original article pages and was deferred without filling any source gap.

| Stage / requirement | Current evidence and disposition |
|---|---|
| R0 numeric protection | tests/snapshot_v3.json retained byte-for-byte; snapshot regression passes. No core/, material record, validation result or dependency change. |
| R0b independent review | REVIEW_thermal_optimise.md: eleven numbered findings, derivations and independent numerical probes; no confirmed equation defect, no snapshot update. |
| R1 clarity | CLARITY_R1.md reviews all eleven tabs and drafts the requested explanations and glossary. Accepted scope, axis, microstrain, model-stop, thermal and validation clarifications are in existing screens. |
| R2 style / honesty | ui_theme.py centralises CSS, palette and fifteen terms. Three status badges, actual unscored-validation text and a collapsible limits panel are visible. No navigation mode or tab was added. |
| R3 existing charts | presentation.py uses solver curve arrays and pre-damage event states, with consistent mode colours in charts and tables. Dome opening and shaded station cells use existing radius and membrane_valid arrays. Unused legend modes are omitted to avoid clipping. |
| R4 existing export | report.py remains the exporter. Mechanical summary and cylinder case are separated; first-ply, model stop, netting, curve, assumptions, version/date/recorded tests are included. Tests prove one page at 4/16/40 plies and exact displayed pressure values. Final sample and all three Report No. 2 pages visually inspected. |
| R5 input handling | ROBUSTNESS_R5.md and eight focused regressions: malformed material cells, extreme angles, nonfinite/zero thickness, mm-to-m underflow and invalid counts. Existing guards cover empty/over-100 editor stacks, one ply, zero working pressure and unavailable custom CTE. Dome UI restricts r0/R to 0.05-0.95; core tests reject r0 >= R. |
| G2 / R7 text disposition | TEXT_REVIEW_G2.md: #1,2,4,10,11 confirmed and corrected. #3 partly confirmed: the displayed hybrid scenarios are specifically two hoop-material assignments, not a proven bound over every order. #5-9 rejected as defects because the current badges, validation, stop, thermal scope and reference wording already state the limitations. |
| Full suite | Historical R5 run: 161 passed, 0 skipped. The latest run summary is in qa_results.json; a full local log is reproducible with python verification/run_refine_qa.py. Includes every material/load/layup preset with all eleven tabs rendered, cached-core export regression, snapshot and report checks. |
| Browser / download | local_browser_qa.json and live_browser_qa.json record eleven actual tab clicks and downloaded cylinder PDFs with zero exceptions after b21ae01. README screenshot uses the visually inspected pressure-strain chart. The initial live ImportError is resolved; this does not establish experimental validity. |
| Cleanup / boundaries | Four old untracked PDF/PNG variants preserved under ignored _local/old_files/r0_preserved. pytest.ini restricts discovery to current tests; .gitattributes treats PDF/PNG as binary. No original test was removed. |

R1 draft corrections: do not globally say Hashin never controls first-ply (the vessel reports its own Hashin initiation); apply that distinction only to the laminate summary. Manufacturing content is labelled background, rather than claimed as a computed process recommendation. Larger first-ply factors, netting ratios and implied radii are not presented as design safety factors or experimental validation.

Import fix: app imports new thermal names directly from core.thermal and conditionally refreshes a cached core package if established mechanics exports are missing. A regression removes engineering_constants and the thermal aggregate names from an already-cached core package and verifies app rendering. This reproduces the suspected stale-package condition; it does not claim access to redacted cloud logs. Mechanics are unchanged.

Deferred: R6 original-page extraction; personal A1-A5; temperature-dependent properties, liner/boss load sharing, certified allowables, physical burst/ultimate prediction and stability remain outside the model. No experimental validation pass is claimed.

Completion audit: all mandatory AI stages R0b, R1-R5, G2 and R7 have the file/test/runtime evidence listed above. R0 was the preserved baseline. Optional R6 was deferred because A5 pages were not supplied; A1-A5 were explicitly excluded by the user. Git push succeeded for d83851c and b21ae01; the public application displayed the revised labels and all eleven tabs and served its cylinder PDF. No core or snapshot difference from 116a072, no removed tests, no added application dependencies, physics modules, tabs or navigation modes.

## Professor-facing follow-up

`verification/PROFESSOR_PASS.md` records nine confirmed interpretation/input-reporting findings and their fixes. The operating route is `DEMO_ROUTE.md`; limitations are in `LIMITS_BEFORE_SHOW.md`. They are technical guides, not the user's personal A1-A5 deliverables. The quiz reuses the existing angle study and follows its 0/90 endpoints. Mechanical summary, thermal no-load face, edited-card provenance, unbalanced netting and large-strain extrapolation are qualified explicitly. The PDF now prints actual sidebar elastic and strength inputs.

Current suite: 163 passed, zero skipped, including unchanged snapshot and the extended PDF page/value checks. Core, material/source records, validation numbers and dependencies remain unchanged. Visual QA confirmed the revised sample remains one page without clipping. After 43969b3, all eleven local/live tabs were clicked without errors, and both cylinder downloads contained one page with identical extracted text, including actual material inputs and large-strain qualification. Evidence: verification/live_browser_qa.json; previous v4 records above retain their historical counts.

## Earlier benchmark details

- `Q̄(0°) = Q`; the 30° glass/epoxy `Q̄` agrees with the closed-form transformation (`verification/benchmark.py`).
- Ply interfaces run from `−h/2` to `+h/2`; stresses are recovered at both faces of every ply from `ε(z) = ε⁰ + zκ`.
- Symmetric stacks give `B ≈ 0`; reversing a stack keeps `A` and `D` and flips the sign of `B`.
- `[0/90]s` T300/5208 with 0.125 mm plies reproduces a published worked example: `A₁₁ = 48.039 MN/m`, `D₁₁ = 1.671 N·m`.
- All calculations are SI internally.

## First audit: findings and corrections

1. **Failure used a fixed demo load** instead of the active load vector. It now uses the sidebar loads.
2. **Strength inputs kept stale values** when the material was switched. Elastic and strength inputs now switch together; a reset button restores the cited values.
3. **An earlier transformation check quoted 30° `Q̄` values** that did not match its own elastic constants. The test now uses the closed-form equations.
4. **Invalid ply-table rows were dropped silently.** They now raise a visible error with the ply number.

## Second review: findings and corrections

1. **Wrong reference value in a benchmark test** (Q₁₁). Corrected to 181.811 GPa, which follows from the stated constants.
2. **Strengths had silent default values.** They are now required inputs.
3. **The UI stated `R = 1/FI`.** The correct statement is `R = 1/√FI`, and only when the linear Tsai–Wu terms vanish.
4. **The Tsai–Wu strength ratio failed under pure bending.** At the mid-plane the stress is round-off noise, and the quadratic term was obtained by differencing, which could make it non-positive. The two terms are now computed directly; regression tests cover pure `Mx`, `My` and `Mxy`.
5. **The balance check ignored ply material**, so +45° graphite with −45° glass was reported as balanced. It now matches angle and material.
6. **Explanatory text corrected:** under `Nx`, `εx = a₁₁Nx` (not `Nx/A₁₁`) when `A₁₆ ≠ 0`; symmetry removes `B`, balance removes `A₁₆/A₂₆`, neither removes `D₁₆/D₂₆`; only the global strains are continuous through the thickness.

## Update: engineering constants, PDF report, pressure vessel

Added after supervisor feedback, with the same rule: no new result without a test.

1. **Equivalent engineering constants** from `ABD⁻¹`. Checked: a unidirectional stack returns E₁, E₂, G₁₂ and ν₁₂ exactly; a quasi-isotropic stack has Ex = Ey and Gxy = Ex/(2(1+νxy)), while its flexural moduli are not isotropic; for symmetric stacks the membrane constants equal those from `A⁻¹`.
2. **PDF report** of the current analysis (inputs, layup, A/B/D, constants, mid-plane response, ply-by-ply screening, model limits). Checked that a valid PDF is produced.
3. **Filament-wound cylinder.** Nx = pR/2 and Ny = pR; netting angle tan²θ = 2 (54.74°) and netting burst 2·Xt·h/(3R) at that angle. A review found that the first netting formula, min(2Σ X t cos², Σ X t sin²)/R, overestimates burst for mixed hoop + helical walls (by 25 % for [90,30,−30]s); it was replaced by the exact fibres-only solution (pR = 2.4·X·t for that wall, now a test), and the min() form is kept only as the labelled upper bound in the winding-angle plot. Also checked: a single ±45° wind has zero netting capacity; a pure hoop wall carries no axial load; the reported first-ply pressure brings the governing criterion exactly to 1; for T300/5208 the CLT first-ply pressure of a ±θ wall peaks within 2° of the netting angle.

## Dome and Hashin / progressive-failure review rounds (C3, C4)

A second AI model reviewed the dome module (10 comments) and the Hashin and progressive-failure code (12 comments). Every comment was verified by derivation or by running the code before any change; the full tables with evidence are in `REVIEW_C3.md` and `REVIEW_C4.md`.

**Dome review (C3).** Confirmed and fixed: #1 (opening, not pole: wording), #3 and #10 (junction and turnaround-zone stations were reported as the weakest station: now flagged and excluded from the headline), #7 (the membrane equation assumes a pressure-tight boss: stated). Rejected as errors, equations verified correct: #2 thickness law, #4 ellipsoid radii, #5 membrane equations, #6 compression criterion, #8 netting vs CLT, #9 membrane CLT validity. No equation changed.

**Hashin and progressive failure (C4).** Confirmed as defects: #2 (pure shear with alpha = 1 degraded fibres and matrix: shear-dominated fibre-tension initiation is now applied as matrix damage), #10 (stopping exceedance and new failures at the same load factor were not batched), #12 (limitations incomplete). Confirmed as stronger claims than the model supports (wording or labelling fixed): #1 (alpha = 1 is a chosen setting), #3 (assumed transverse shear strength, which also exceeds S12 for T300/5208), #4 ("2D Hashin" named plane-stress Hashin-1980-inspired), #7 ("residual-strength cap" is a two-level termination rule), #8 (last-ply = where the algorithm stops, not an ultimate load), #9 (non-decreasing load factor is not a stability analysis; held steps flagged). Partly confirmed: #5 (residual factors are assumptions: reported as a range), #6 (optional loss of E2 and G12 after fibre failure), #11 (splitting a ply leaves the load factors unchanged in the cases tried; the limit is stated). Not acted on, with reasons: not activating FT at small sigma1 or switching to alpha = 0 (weakens initiation), separate calibrated FT/FC/MT/MC rules (no data), a damage-evolution law with fracture energy (out of scope), arc-length control (not implemented). Reviewer remarks citing the literature (NASA review, the 53 degree angle) were not verified against the sources.

**Reverse check.** The first model checked the second model's research data for internal consistency and recorded 11 flags in `validation/README.md` (Part A), among them that the inner radius is missing in every source and that the same carbon lamina card appears in two papers.

## Remaining limitations

Strengths are literature values, not qualified allowables. `F₁₂ = −0.5√(F₁₁F₂₂)` is an assumption. Results are linear-elastic CLT screening; progressive damage is a ply-discount model with assumed factors, and residual thermal stresses and transverse shear are not modelled. A comparison with published burst data could not be completed like for like (`validation/README.md`).
