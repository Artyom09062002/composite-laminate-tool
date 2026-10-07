# UX_INVENTORY: what each tab shows and what a first-time viewer will not understand

Source: read from `app.py` (R0, 7 Oct 2026), not from a screenshot walk-through. "Gap" means a term, number or choice
that a first-time viewer (a composites professor or an engineer who has not used the tool) cannot decode from the screen alone.
Nothing here has been changed in the app; this is an inventory for the next UX task.

## Always visible (hero, sidebar, summary, how-to)

- **Inputs (sidebar):** material dataset (2 cited sets + Custom), E1, E2, G12, nu12, default ply thickness; load preset and Nx, Ny, Nxy, Mx, My, Mxy; strengths Xt, Xc, Yt, Yc, S (collapsed by default). The layup is edited in tab 2.
- **Outputs:** Plies, Thickness, Symmetric, Max Stress index, Min Tsai-Wu R, one "Result in plain words" box, PDF report button; a four-step "how to use" panel.
- **Charts:** none.
- **Gap:** (1) "Max Stress index" (1 = failure, load scale = 1/index) and "Tsai-Wu R" (load scale directly) have opposite directions and are side by side. (2) The sidebar material is only "ply material 0"; a ply set to another dataset in tab 2 ignores sidebar edits, and nothing says so on the sidebar. (3) The sidebar loads drive tabs 3-5 and Compare, but not "Start here" (own fixed Nx = 100 kN/m), Applications (own load cases) or the vessel tab (pressure-driven). (4) The hero says "first-ply screening", but the app now also has progressive failure, domes, thermal and an optimiser; the headline does not signal the pressure-vessel focus of SPEC v3.

## Start here
- **Inputs:** a prediction radio (Increase / Decrease / Stay the same), "Check my prediction", an angle slider 0-90 in steps of 5. Material and thickness come from the sidebar; load is fixed at Nx = 100 kN/m.
- **Outputs:** A11, x strain, Max Stress index for the chosen angle; a "trace the cause" sentence.
- **Charts:** A11 vs fibre angle; x strain vs fibre angle (both lines, 0-90 deg in steps of 10).
- **Gap:** the quiz wording ("will A11 increase, decrease..." for [theta,theta]s) is clear, but "Correct" only handles "Decrease" and any other answer is told to "try the slider". The final sentence ("A16 not 0, eps_x grows faster than 1/A11") needs CLT vocabulary. The tab is a teaching warm-up and never mentions pressure vessels, the actual subject of the app.

## 1 Material and Q
- **Inputs:** none of its own (sidebar material).
- **Outputs:** source link and note, nu21, the 3x3 Q matrix in GPa, term-by-term formulas.
- **Charts:** none.
- **Gap:** index labels "1, 2, 12" and engineering shear strain gamma12 appear without a picture of the 1-2 axes;

## 2 Layup and Q-bar
- **Inputs:** angle slider (-90 to 90); four layup preset buttons; a typed layup string; Apply / Reverse / Mirror; an editable ply table (angle, thickness, material per ply, add/delete rows).
- **Outputs:** Q-bar for the slider angle; Q-bar11 and Q-bar22 at 0, 45, 90 deg; ply stack picture; "in plain words" box.
- **Charts:** coloured ply stack (z in mm, labelled by angle, material in hybrids).
- **Gap:** layup syntax `[0,45,-45,90]s` (the trailing `s` mirrors the listed half) is explained in one caption, with the comma/slash rule. The "Material" column offers "Sidebar material" first, which is not a material name. The slider angle is unrelated to the ply table and the tab does not say so.

## 3 ABD
- **Inputs:** none (layup from tab 2).
- **Outputs:** A, B, D matrices, six engineering constants (Ex, Ey, Gxy, nu_xy, Ex and Ey flexural), full ABD and z positions in an expander, coupling messages (B = 0, A16/A26, D16/D26), balanced / A11-to-A22 note.
- **Charts:** none (tables only).
- **Gap:** units differ per matrix (MN/m, N, N·m) and the 6x6 expander uses raw SI in "%.4g"; B and D16 messages use "near zero" thresholds that are not shown. "Apparent constants with curvature free" and "flexural vs membrane Ex" are not self-explanatory.

## 4 Response
- **Inputs:** none (sidebar loads, layup from tab 2).
- **Outputs:** mid-plane strain (micro-strain), curvature (1/m), a bottom/top-face table with fibre-axis strain and stress for every ply, CSV download.
- **Charts:** stress and strain vs z through the thickness (lines per component, drawn per ply).
- **Gap:** two table rows per ply (Bottom, Top) and fibre-axis stress jumps at interfaces are explained only in a caption; micro-strain ("µε") needs a hint.

## 5 Failure (includes Hashin and the thermal block)
- **Inputs:** none for the first-ply table. Thermal block: case (Direct dT / Cool from reference to final), dT, chosen final temperature, "assumed common stress-free temperature", checkbox to add sidebar loads.
- **Outputs:** per-face ratios, Max Stress index, Tsai-Wu FI and R, Hashin active mode, index and R, a screen verdict; first-ply location, criterion, proportional load factor. Thermal: CTE table with sources, Active dT, Max residual |sigma2|, first-ply factor with thermal preload, residual and combined stress table, source links.
- **Charts:** none.
- **Gap:** this is the densest tab (about a dozen columns per row). A first-time viewer sees three failure criteria (Max Stress, Tsai-Wu, Hashin) with three different scales, but the verdict and load factor use only Max Stress and Tsai-Wu; Hashin is shown in the table and excluded from the verdict (stated only in a caption). FI vs R (quadratic index vs load scale) is explained in an info box. The thermal block is nested inside a tab called "Failure", so a viewer looking for "thermal" will not find it from the tab names; "stress-free temperature", "residual stress" and "thermal preload" are not defined on screen. S_t is assumed (Mohr-Coulomb, 53 deg), stated only in a caption. The block is unavailable for Custom materials (UNSOURCED warning).

## Compare
- **Inputs:** a text area with 2-5 layup strings; a "Rank by" selector (first-ply load factor, lowest |eps_x|, highest A11, highest D11).
- **Outputs:** 13-column comparison table with CSV download, top-candidate metric.
- **Charts:** horizontal bar chart of the chosen criterion.
- **Gap:** thickness differs between candidates (same ply count only if the strings have the same length), so "highest A11" mostly ranks thicker stacks; this is stated once in the final caption.

## Pressure vessel (one tab, five sections)
Order: winding-angle study, current-layup check, progressive failure, cylinder optimiser, dome.
- **Inputs:** radius R, wall plies (multiple of 4), working pressure; degradation factors E1/E2/G12 (expander); optimiser angle set, candidate budget, "Search cylinder layups" button, ranking selector; dome r0/R and dome depth/R.
- **Outputs:** wall thickness, netting angle and netting burst at +/-54.7 deg, best first-ply pressure; first-ply (CLT), netting estimate, netting/working ratio; first-ply (Hashin), last-ply (model stop), last-ply/first-ply, last-ply/netting; failure-step table; optimiser top five with netting reference; dome alpha0, thickness, weakest valid station, cylinder first-ply.
- **Charts:** pressure vs winding angle (first-ply, last-ply, netting, netting-angle rule, working pressure); pressure vs hoop strain with limit rules; dome angle and thickness vs r; dome first-ply pressure vs r.
- **Gap:** (1) Three different pressures (first-ply, last-ply "model stop", netting) appear within one screen of each other; "last-ply" is explicitly not a burst pressure and the label says "model stop", but a headline reader will compare it with the burst of a real tank. (2) "Netting burst" is shown at +/-54.7 deg and "Optimiser netting ideal" is a second netting number with a different definition. (3) Optimiser vocabulary: "count vector", "fibre projection bound", "canonical mirrored order", "first / netting ideal". (4) Dome: r0/R, "depth/R (1 = hemisphere, 0.5 = 2:1)", "membrane-valid stations", faint dotted segments. (5) No chart shows the vessel geometry. (6) The tab silently assumes a metal-free, liner-free, boss-free vessel; the limits box is at the bottom. (7) Nothing links to the validation result (see Cross-cutting).

## Manufacturing
- **Inputs:** a manufacturing-route selector, a defect selector.
- **Outputs:** static process table (5 routes), one "how it works / control point" box, one defect warning, FAA link.
- **Charts:** none.
- **Gap:** all text is static and generic (nothing is computed); it is not tied to the vessel the rest of the app is about. It conflicts with the rule that every explanatory text is traceable to something the app computes or validates unless it is labelled as general background.

## Applications
- **Inputs:** radio (aerospace panel / wind-blade spar cap), load-case selector (aerospace only).
- **Outputs:** three-layup table with A11 or A66, strain, Max Stress index, load factor; "lowest strain" verdict; spar-cap A matrix and neutral-axis shift (B11/A11).
- **Charts:** none.
- **Gap:** no pressure-vessel application although that is the app's focus.

## Verification
- **Inputs:** none.
- **Outputs:** the [0/90]s published comparison (A11, D11, max |B|), the test command, a model-limits box.
- **Charts:** none.
- **Gap:** the table is hard-coded and a single-case comparison; the text lists tests up to the pressure-vessel netting angle and does not mention the dome, Hashin, progressive-failure, thermal or optimiser tests. The test suite count is not shown. See Cross-cutting for the validation result.

## Cross-cutting gaps (important for a first-time viewer or a professor)
1. **The validation outcome is not in the app.** `validation/README.md` and Report No. 2 state that no like-for-like comparison with measured burst data was possible (inner radius NOT REPORTED in all four sources; Type III liner UNSOURCED). `app.py` never mentions this. The "last-ply" and "netting" numbers therefore appear without their validation status.
2. **Navigation:** 11 tabs; the thermal block is inside "5 Failure", progressive failure, optimiser and dome are inside "Pressure vessel"; nothing in the tab names shows that the app has these features.
3. **Defaults are a research composite (T300/5208), a 100 mm radius and 16 plies:** the vessel results at default inputs describe a 2 mm wall at R/h = 50, not a real hydrogen tank; the app does not offer a hydrogen-tank scenario or say it is a teaching geometry.
4. **Units:** SI internally, GPa / MPa / mm / kN/m on screen, mixed per table (A in MN/m, B in N, D in N·m).
5. **Assumption labels exist but are scattered:** assumed S_t, F12, degradation factors, common thermal reference are each stated in captions near the number, not in one list.
6. **No export of the pressure-vessel results:** the PDF and CSV exports cover the laminate tabs only.
