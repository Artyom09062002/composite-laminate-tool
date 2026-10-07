# Engineering audit log

The code was written with AI coding assistants. An AI-written change was accepted only after it was checked against the hand-derived equations, limiting cases, a published worked example and automated tests. This file records what those checks found and what was changed.

## Confirmed

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

## Remaining limitations

Strengths are literature values, not qualified allowables. `F₁₂ = −0.5√(F₁₁F₂₂)` is an assumption. Results are linear-elastic, first-ply CLT screening without residual thermal stresses, transverse shear or progressive damage.
