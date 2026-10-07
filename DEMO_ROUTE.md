# Five-minute demonstration route

Technical operating guide for the existing app. This is not the user's personal A2 explanation or a substitute for A1-A4.

## Preparation

Open a fresh app session. Select **Graphite/Epoxy (T300/5208)**, reset to cited values, select **Axial tension (Nx = 100 kN/m)**, and apply **Quasi-isotropic [0/45/-45/90]s**. Confirm eight plies, 0.125 mm per ply and 1.000 mm total thickness. Use R = 100 mm and the default degradation factors in Pressure vessel. For the demonstration, set working pressure to **1 MPa**, explicitly as an illustrative input, not a recommended operating pressure.

The **16 wall plies** input controls the angle study, optimiser and dome, not the current eight-ply laminate. The green mechanical summary concerns sidebar loads, not working pressure. Keep these two load cases separate throughout.

## Main route: five minutes

| Time | Existing screen and action | Evidence to point to | Interpretation to establish |
|---|---|---|---|
| 0:00-0:30 | Top summary and validation banner | Cited teaching data; no like-for-like experimental comparison | This is an educational screening model. Numerical checks and experimental validation are separate. |
| 0:30-1:15 | Material & Q, then Layup & Q-bar; move the one-ply preview slider from 0 to 90 degrees | Q is in fibre axes; Q-bar is in laminate axes | The preview slider does not edit the actual stack. The entered properties determine the stiffness trend. |
| 1:15-2:00 | ABD, with the default eight-ply quasi-isotropic stack | A11 = A22 = 76.3682 MN/m; B approximately zero; D11 = 10.6907, D22 = 2.6533 N m | Symmetry removes extension-bending coupling. Quasi-isotropic membrane stiffness does not imply isotropic bending stiffness. |
| 2:00-2:45 | Failure; point to the governing face and criterion | Mechanical load factor 2.76119; Tsai-Wu, ply 4 bottom face | The factor scales the six sidebar loads proportionally to initiation. Hashin has a separate mode result; initiation is not whole-laminate collapse. |
| 2:45-4:15 | Pressure vessel: current-layup metrics, sequence and pressure-strain chart | Eight-ply cylinder: CLT/Hashin initiation 2.96314 MPa; model stop 6.02808 MPa; balanced netting reference 7.50000 MPa | These are three model outputs with different assumptions. The model stop is not burst pressure. The large calculated strain tail is linear-model extrapolation, not a physical deformation prediction. |
| 4:15-5:00 | Verification; then download the cylinder PDF | [0/90]s benchmark A11 approximately 48.039 MN/m, D11 approximately 1.671 N m; recorded test suite; limits | The benchmark checks an implemented laminate calculation. It does not validate a tank against experiments. The PDF separates mechanical laminate and pressure cases. |

Values above are calculated/reference-display values, not experimental measurements. Source: `tests/snapshot_v3.json`, the existing benchmark and current default material card. Display rounding explains small last-digit differences.

## Optional extensions, only if asked

- **Thermal, about one minute:** keep the default quasi-isotropic layup and sidebar load; choose Direct delta T = -100 C. Residual transverse stress magnitude is about 21.27 MPa; the mechanical first-ply factor with thermal preload is about 1.285. The thermal stress stays fixed while the mechanical load scales. This does not calculate temperature-dependent properties or manufacture/cure chemistry.
- **Dome, about one minute:** defaults r0/R = 0.5, depth/R = 1 give cylinder winding angle 30 degrees. The model has 15 membrane-valid stations out of 41; the weakest valid station is about 4.32 MPa. Shaded edge stations are excluded from the headline. This dome uses the separate 16-ply helical wall, not the current eight-ply laminate.
- **Optimiser, about one minute:** run the search before the meeting. Defaults evaluate 128 of 203,490 symmetric count vectors with seed 2026. The saved baseline top first-ply result is about 8.86 MPa, with model stop 20.10 MPa and fibre-only ideal 20.00 MPa. A sampled count search is not a global stacking-sequence or manufacturing optimum.

## Stop rules for the demonstration

Do not compare green mechanical status with working pressure; do not call model stop burst; do not interpret a large-strain tail as physical tank expansion; do not use axial/hoop netting as a complete solution for an unbalanced wall; do not describe a conditional paper case or an implied radius as validation. If a number is questioned, identify its inputs and model before giving an interpretation.
