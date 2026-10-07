# ACCEPTANCE: tests that must pass per module

## Existing (v2): 43 tests passing
Unidirectional stack recovers E1/E2/G12/nu12; quasi-isotropic Ex=Ey and Gxy=Ex/(2(1+nu)); [0/90]s matches published A11, D11; netting angle 54.74 deg and burst formula; exact netting for hoop+helical walls; first-ply pressure brings the governing criterion to 1.

## Dome (C2)
- Winding angle = 90 deg at r = r0; alpha(R) = asin(r0/R).
- Hemisphere: N_phi = N_theta = pR/2.
- Thickness grows monotonically toward the pole; at r -> R it equals the cylinder value.
- Dome function at r = R reproduces the cylinder first-ply pressure.

## Progressive failure and Hashin (C3)
- Unidirectional ply under tension fails at Xt (last ply).
- [0/90]s uniaxial: matrix failure first, fibre failure last.
- Load factor non-decreasing until final failure.
- Hashin and Max Stress agree in pure fibre tension.

## Validation (C4)
- Every case has geometry, layup, lamina properties and measured burst pressure with source and page.
- Results file lists predicted first-ply, last-ply, netting vs measured; no parameter tuned to fit.

## Thermal (C5)
- Unidirectional ply recovers alpha1 and alpha2.
- Symmetric laminate: zero curvature after uniform dT.
- Quasi-isotropic laminate: equal expansion in x and y.
- [0/90]s cooling: tensile transverse stress in the 0 plies (sign check), zero net force.

## Optimiser (C6)
- One allowed angle returns that angle.
- Fibre-limited optimum for a thin cylinder lies near the netting angle.
- Deterministic (fixed seed).
