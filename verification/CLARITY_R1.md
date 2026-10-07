# R1: clarity pass on existing screens

Scope: wording and interpretation of controls and outputs already present in `app.py`; no new behavior or features. The screen inventory below is grounded in `UX_INVENTORY.md` and the current UI strings/code paths in `app.py`. Proposed text is plain-English copy; retain equations and numerical methods unchanged.

## Highest-value confusion points by tab

Each tab has at most five points. “Draft” wording is an editorial recommendation, not a claim that the text is already present.

| Existing tab | Confusion point | Two-sentence plain-English draft | Existing-code trace |
|---|---|---|---|
| Start here | The graph's stiffness and strain trends need a physical interpretation; the fixed load can look like a user input. | “This lesson holds the axial load at 100 kN/m and changes the fibre angle. Compare the curve with your prediction; the material and ply thickness come from the sidebar.” | `tabs[0]`; fixed illustrative load and A11/strain charts. |
| 1 · Material & Q | 1/2/12 axes and engineering shear are abstract without an axis reminder. | “Direction 1 runs along the fibres, direction 2 lies across them, and 12 denotes in-plane shear. Q describes stiffness in those fibre axes.” | `tabs[1]`; Q matrix, ν21 and formulas. |
| 2 · Layup & Q-bar | “Sidebar material” can be mistaken for a named dataset; slider angle is separate from the edited stack. | “The angle slider previews one ply and does not change the layup table. In the table, ‘Sidebar material’ means the values currently entered in the sidebar.” | `tabs[2]`; slider, layup parser/editor, material selector. |
| 3 · ABD | A/B/D units differ; near-zero is a scale-based numerical threshold; free-curvature constants are easy to misread. | “A measures in-plane stiffness, B measures coupling between stretching and bending, and D measures bending stiffness. Matrix units differ: A is N/m, B is N, and D is N·m; ‘approximately zero’ uses a numerical tolerance.” | `tabs[3]`; matrix displays, `near_zero`, “In plain words: A, B and D” expander. |
| 4 · Response | Microstrain and duplicate bottom/top face rows need explanation. | “Microstrain (µε) is strain multiplied by one million. Each ply has a bottom-face and top-face row; global strain is continuous, while local ply stress can jump at an interface.” | `tabs[4]`; surface table, plots and caption. |
| 5 · Failure | Three criteria use different indices and load scales; Hashin appears in the table but does not control the displayed screen/load factor. | “A value of 1 marks the criterion’s limit, but the numbers are not interchangeable: use each criterion’s strength ratio to read its proportional load scale. Hashin reports a separate initiation mode; the summary screen and first-ply factor use Maximum Stress and Tsai–Wu.” | `tabs[5]`; table, `first_ply_limit`, captions and verdict. **Check:** verify current intended policy before any copy suggests Hashin controls the summary. |
| Compare | Candidates can have different ply counts and thicknesses, so a stiffness ranking may reward more material. | “Each candidate uses the same thickness per ply, but the total thickness can differ. A higher stiffness may therefore come from a thicker stack, as well as from its fibre arrangement.” | `tabs[6]`; candidate parser, thickness column and ranking caption. |
| Pressure vessel | First-ply, algorithm stop and netting values are model outputs with different assumptions; “burst” sounds measured. | “First-ply pressure marks calculated damage initiation; last-ply is where the chosen stiffness-degradation algorithm stops. Netting is a separate fibre-only equilibrium estimate, and none of these values is a measured or validated vessel burst pressure.” | `tabs[7]`; winding study, cylinder check and progressive section; `screen_cylinder`, `progressive_failure`, `cylinder_resultants`. |
| Manufacturing | Generic route/defect guidance is not derived from the active laminate calculation. | “This section gives general manufacturing background and does not calculate a process recommendation for the laminate above. Use it as context, not as a result from this model.” | `tabs[8]`; static route and defect selector/content. **Check:** confirm current text still has no calculation link before presenting this as a final on-screen label. |
| Applications | Illustrative aerospace load cases are separate from sidebar loads and from the pressure-vessel model. | “These examples use their own illustrative load cases. They do not use the sidebar load vector or predict pressure-vessel performance.” | `tabs[9]`; aerospace panel and spar-cap cases. |
| Verification | A single laminate benchmark can be mistaken for validation of every module. | “This page reports a laminate benchmark and selected test coverage. It does not validate pressure-vessel burst, dome, thermal, Hashin, progressive-failure or optimisation predictions against experiments.” | `tabs[10]`; hard-coded benchmark, test command and model-limit copy. **Check:** verify exact current listed coverage before updating the screen text. |

### Cross-cutting wording

- Hero/default inputs can look like a real tank specification. Suggested line: “The default cylinder is an illustrative teaching case; set its radius, ply count and pressure before interpreting the results.”
  Trace: hero/sidebar defaults and Pressure vessel inputs in `app.py`.
- Thermal controls live inside Failure. The page-level caption currently points viewers there; keep a concise “Thermal results are in Failure” navigation hint visible.
  Trace: top captions and thermal container under `tabs[5]`.
- Validation status is available in `validation_status()` and shown near the hero. Keep this status adjacent to vessel results when summarizing or exporting them.
  Trace: `st.warning(validation_status())`, `presentation.validation_status`. **Check:** status wording and source data can change; use the function’s current text.

## Plain-English glossary copy (15 terms maximum)

These definitions are two short sentences each and can be used to replace or refine the current 15-entry `GLOSSARY` in `ui_theme.py`. They describe current calculations and assumptions.

1. **Lamina / ply:** One fibre-reinforced layer with its own fibre direction and thickness. The app treats each listed ply as a layer in the laminate.
2. **Layup:** The ordered list of plies from the bottom face to the top face. A symmetric suffix mirrors the listed half about the mid-plane.
3. **Q / Q-bar:** Q is a ply’s stiffness in its fibre directions. Q-bar is that stiffness rotated into the laminate’s x-y directions.
4. **A, B, D:** A describes in-plane stiffness, B describes extension-bending coupling, and D describes bending stiffness. Their displayed units differ because they relate force, moment and curvature differently.
5. **Resultant:** A force or moment per unit width for the laminate. It comes from adding the stresses and their distance-from-mid-plane effects through the thickness.
6. **Microstrain (µε):** One microstrain is one millionth of unit strain. For example, 1000 µε equals 0.1% strain.
7. **Symmetric:** The plies mirror across the laminate mid-plane. In this CLT model, a symmetric stack has B = 0.
8. **Balanced:** Each +angle ply has a matching -angle ply with equal thickness and material. This pairing reduces in-plane extension-shear coupling.
9. **First-ply:** The first calculated ply-face limit reached as the load is applied. It marks predicted initiation, not failure of the whole laminate.
10. **Last-ply (model stop):** The pressure where the progressive-failure algorithm stops after reducing stiffness in failed plies. It depends on assumed degradation rules and is not a measured ultimate pressure.
11. **Tsai–Wu:** A quadratic criterion that combines stresses in different directions, including an assumed interaction term. Its failure index reaches 1 at the criterion limit; use R to read the proportional load scale.
12. **Hashin:** A criterion that checks separate fibre and matrix failure modes. Here it reports an initiation mode and uses an assumed transverse shear strength; it does not control the first-ply summary factor.
13. **Strength ratio (R):** R is the multiplier on a proportional load path that makes a selected failure criterion reach its limit. R above 1 means the entered load is below that limit under the model; R below 1 means it is already exceeded.
14. **Netting:** A separate equilibrium estimate that lets fibres carry the vessel-wall load. It omits matrix load sharing and the liner, so it is a reference rather than a validated burst prediction.
15. **Residual thermal stress:** Stress left in bonded plies after a temperature change because they cannot expand or contract independently. The calculation assumes a common stress-free reference temperature and constant material properties.

## Requested two-sentence screen drafts

The matching two-sentence entries above cover first-ply, last-ply, Tsai–Wu, Hashin, strength ratio, netting and residual thermal stress. All are tied to existing code: first-ply and criterion factors in `tabs[5]`; progressive stop and netting in `tabs[7]`; thermal recovery and common reference in the thermal block under `tabs[5]`.

**Source trace:** `app.py` (tab bodies, thermal block, and vessel/progressive UI); `ui_theme.py` (`GLOSSARY`); `presentation.py` (`validation_status`); `UX_INVENTORY.md` (screen-by-screen inventory). No mechanics change is proposed.