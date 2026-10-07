# ACCEPTANCE: tests that must pass per module

## Existing (v2): 43 tests passing (98 in the whole suite after C3)
Unidirectional stack recovers E1/E2/G12/nu12; quasi-isotropic Ex=Ey and Gxy=Ex/(2(1+nu)); [0/90]s matches published A11, D11; netting angle 54.74 deg and burst formula; exact netting for hoop+helical walls; first-ply pressure brings the governing criterion to 1.

## Dome (C2): passing (19 tests in tests/test_dome.py; full suite 62, 1 skipped = PDF report without reportlab)
- Winding angle = 90 deg at r = r0; alpha(R) = asin(r0/R); r sin(alpha) = r0 along the dome; r < r0 rejected.
- Hemisphere: N_phi = N_theta = pR/2 at every station.
- Ellipsoid: r1, r2 agree with the curvature of z(r) derived independently; a 2:1 head has N_theta = -pR at the equator.
- Thickness grows monotonically toward the pole; at r = R it equals the cylinder wall; equals sqrt((R^2-r0^2)/(r^2-r0^2)); t r cos(alpha) is constant.
- Limit r -> R: alpha, thickness and N_phi equal the cylinder values. N_theta equals the cylinder value only for a straight meridian (r1 -> infinity); a hemisphere gives pR/2 against pR (membrane jump at the junction, tested as such).
- First-ply: the shared code path with r1 -> infinity reproduces screen_cylinder exactly; at every station the first-ply pressure brings the governing criterion to 1.
- Not implemented: isotensoid profile. Simplifications: helical plies only, no slippage, constant band width and fibre volume, membrane theory.

## Progressive failure and Hashin (C3): passing (tests/test_hashin.py, tests/test_progressive.py, tests/test_app_pressure_vessel.py)
- Unidirectional ply under tension fails at Xt (last ply): Nx = Xt h to 1e-9; also glass, and Xc in compression.
- [0/90]s uniaxial: matrix failure first (the 90 deg plies), fibre failure last (the 0 deg plies); last-ply load between 2 t Xt and 2 t (Xt + Yt).
- Load factor non-decreasing until final failure (event and history; standard layups x 7 load cases and 150 seeded random hybrid layups); stiffness never increases after a failure.
- Hashin and Max Stress agree in pure fibre tension and compression (same strength ratio, index = utilisation squared, same mode).
- Hashin: each mode equals 1 at its pure strength; strength ratio solves index(R sigma) = 1; shear contribution and Hashin-Rotem variant tested; matrix compression with the assumed or given transverse shear strength.
- Degradation rules documented as assumptions; nu12 scales with E1 (S12 constant), so Q never stiffens and stays positive definite.
- Pressure vessel tab shows first-ply (CLT), first-ply (Hashin), last-ply and the netting estimate; the degradation factors are editable.

## Independent dome review (G3 / C3): see verification/REVIEW_C3.md
- 10 comments verified; confirmed and fixed: 1 (wording), 3, 7, 10 (edge zones flagged and excluded from the headline; boss reaction stated). Equations unchanged.

## Independent Hashin / progressive-failure review (G4 / C4): see verification/REVIEW_C4.md; passing (tests/test_review_c4.py)
- 12 comments verified; 3 confirmed as defects, 6 as wording or labelling, 3 partly confirmed; Hashin formulas and the load-factor solver unchanged.
- Pure in-plane shear with alpha = 1 degrades the matrix only (no fibre failure); the first-failure load factor is the same for both policies.
- Stopping exceedance and new failures at the same load factor are one batch (pure step-planning tests); held steps are flagged (cascade).
- Assumptions are stated in every result: assumed transverse shear strength, two-level residual-stiffness termination rule, not a stability analysis.

## Validation (C4): executed, NOT passed as a comparison
- The runner writes validation/results.json with predicted first-ply, last-ply and netting for every case; no parameter tuned to fit; sensitivities are labelled.
- Criterion "every case has geometry, layup, lamina properties and measured burst with source" is NOT met: the inner radius is NOT REPORTED in all four sources and the Type III liner properties are UNSOURCED. Such cases are listed with the missing items and are not scored.

## Thermal (C5)
- Unidirectional ply recovers alpha1 and alpha2.
- Symmetric laminate: zero curvature after uniform dT.
- Quasi-isotropic laminate: equal expansion in x and y.
- [0/90]s cooling: tensile transverse stress in the 0 plies (sign check), zero net force.

## Optimiser (C6)
- One allowed angle returns that angle.
- Fibre-limited optimum for a thin cylinder lies near the netting angle.
- Deterministic (fixed seed).
