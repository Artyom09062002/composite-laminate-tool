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

## Remaining limitations

Strengths are literature values, not qualified allowables. `F₁₂ = −0.5√(F₁₁F₂₂)` is an assumption. Results are linear-elastic, first-ply CLT screening without residual thermal stresses, transverse shear or progressive damage.
