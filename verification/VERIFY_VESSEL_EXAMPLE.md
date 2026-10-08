# Verification: published filament-wound vessel examples

## Sources read and available comparisons

1. David Roylance, *Pressure Vessels*, MIT, August 23, 2001: [official PDF](https://web.mit.edu/course/3/3.11/www/modules/pv.pdf), local copy `sources/Roylance_pressure_vessels.pdf`. All 10 pages read as extracted text; Example 1 p. 4 / Figure 6 is the worked filament-winding angle derivation. Printed input is the closed-cylinder hoop/axial equilibrium relationship, with symbolic p,r,b,n,T. Printed answer: tan²α=2, α=54.7°. Numerical radius, pressure, thickness, fibre strength, netting failure pressure: NOT REPORTED in Example 1. Other numerical examples concern isotropic/compound cylinders, so they are not used to check composite netting strength.
2. David K. Roylance, *Netting Analysis for Filament-Wound Pressure Vessels*, AMMRC TN 76-3, August 1976: [official PDF](https://web.mit.edu/roylance/www/netting.pdf), local copy `sources/Roylance_netting.pdf`. This is an image-only scan; all 9 PDF pages visually inspected. Printed pp. 5–6 (PDF pp. 6–7) show a worked Kevlar bottle with measured burst and predicted strains/stresses. The faint calculator output on printed p. 6 is not fully legible and has not been used to extract extra numbers; no exact data are inferred from graphs.

## Like-for-like check: Example 1, angle

Independent hand equilibrium: for balanced ±θ, Nx=σf h cos²θ and Ny=σf h sin²θ [N/m]. Closed-end pressure gives Ny/Nx=2 [-], hence atan(sqrt(2)) in radians, converted to degrees. No material, radius or thickness can change that ratio within these assumptions.

| Quantity | Source | Hand (computed, unrounded) | App core (unrounded) | Difference |
|---|---|---|---|---|
| Ny/Nx [-] | 2, p. 3 eqs. (2),(3); p. 4 Example 1 | 2 | 2.0 | 0 absolute |
| tan²α [-] | 2, p. 4 Example 1 | 2 | 2.0000000000000004 | 4.440892098500626e-16 absolute |
| α [deg] | 54.7, p. 4 Example 1 / Figure 6 | 54.735610317245346 | 54.735610317245346 | 0.035610317245343026 deg; 0.06510112841927426 % |
| Nx, Ny [N/m] numerical | NOT REPORTED in Example 1 | NOT REPORTED | NOT COMPARABLE | n/a |
| Required thickness [m] | NOT REPORTED in Example 1 | NOT REPORTED | NOT COMPARABLE | n/a |
| Netting pressure [Pa] | NOT REPORTED in Example 1 | NOT REPORTED | NOT COMPARABLE | n/a |

Angle agrees within half of the source's last printed unit (0.05 degree). `(p,R)=(1 Pa,1 m)` in the ratio check is an explicitly chosen algebraic test of `cylinder_resultants`, not an input attributed to Roylance.

## Why the second published worked example is not an app strength validation

Printed pp. 5–6 use diameter 6 inch, length 14 inch, ±25° helical winding plus hoops, Ah=0.0232 in²/in, Aα1=0.0155 in²/in, Aα2=0, and measured burst 3042 psig. The p. 6 table prints netting hoop/axial strains 1.84%/1.89%, hoop/helical fibre stresses 351/358 ksi; gauge-derived values are 1.25%/0.69% and 238/160 ksi. These are not fitted inputs for this app.

That note obtains fibre stress and strain through a common fibre modulus and strain compatibility, equations (2)–(4),(9)–(15). The app's `netting_pressure` maximizes pressure subject to axial/hoop force equilibrium and supplied fibre strength limits; it does not predict those strains or implement the note's compatibility solution. Fibre area per width is not composite wall thickness without fibre volume fraction. No qualified Xt or fully specified CLT material/layup is supplied by the read example for this implementation. Treating measured burst as Xt, converting its fibre areas into laminate thickness, or using the source's predicted stresses as fitted strengths would manufacture a validation. No such conversion/tuning was made.

Thus a published worked filament-winding angle example is reproduced. Among the inspected sources, no fully specified numerical worked pressure/thickness answer was found that can be compared to the app's netting pressure like for like. The numeric bottle example is documented but not forced into a comparison. No external pressure, CLT failure pressure, progressive/model-stop pressure, liner or dome validation is claimed.

## Internal default-input arithmetic (not external validation)

See [Russian guide](../docs/PRESSURE_VESSEL_EXPLAINED_RU.md), including the independent hand formulas and the default example. The reproducible script `verify_kaw_vessel.py` runs existing core/workflow methods:

| Quantity | Source of inputs | Hand (computed) | App | Difference |
|---|---|---|---|---|
| Nx [N/m] | app defaults p=10.0 MPa, R=100.0 mm | 500000.0 | 500000.0 | 0 absolute |
| Ny [N/m] | same defaults | 1000000.0 | 1000000.0 | 0 absolute |
| Netting p at balanced optimal ±θ [Pa] | 16 default plies; t=0.000125 m; existing dataset Xt=1500000000.0 Pa | 19999999.999999996 | 20000000.0 | 3.725290298461914e-09 Pa |

Run `python verification/verify_kaw_vessel.py`. Computed values are serialized without decimal formatting in `kaw_vessel_results.json`. The source PDFs and this note distinguish printed evidence from app-default predictions.
