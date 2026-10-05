# Composite Laminate Design & Analysis Tool

## Purpose

Build a transparent educational engineering application for Classical Lamination Theory (CLT), taking a user from material properties to lamina stiffness, orientation, laminate ABD stiffness, and engineering interpretation.

## Non-negotiable engineering conventions

- Store and calculate exclusively in SI units: Pa, m, N.
- Display may use GPa, MPa and mm, with explicit conversion only at the UI boundary.
- Plane-stress Voigt order is `[σ1, σ2, τ12]` and `[ε1, ε2, γ12]`; shear strain is engineering shear strain.
- A positive ply angle is counter-clockwise from the global x-axis to the material 1-axis.
- Ply lists run from the `−h/2` face to the `+h/2` face.
- Preserve validated equations in `core/`. Do not alter an equation, sign convention, or coordinate convention without an engineering justification and a regression test.
- Treat every source-controlled material set as reference/teaching data unless qualified allowables and provenance are supplied.

## Quality rules

- Add or update a focused test for every mechanics change.
- Keep UI inputs visibly separate from calculated outputs.
- Give a concise physical interpretation with significant engineering outputs.
- State model limitations instead of implying certification-level validity.
