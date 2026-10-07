# SPEC: Composite Laminate Tool, v3 scope

**Goal.** An educational tool that shows composites understanding (Classical Lamination Theory, failure, filament winding) with a hydrogen pressure-vessel focus. Not a certified design tool.

**Status (v4 refinement, 7 October 2026):** All five v3 modules exist. Numerical verification is distinct from experimental validation: no current burst case supports a like-for-like comparison. v4 refines existing texts, status labels, charts, export and input handling; it adds no physics, dependencies, tabs or modes. Stage evidence is in `verification/AUDIT.md`; optional source-page work R6 and the user's A1-A5 are separate.

**v3 scope** (in this order):
1. Geodesic dome winding: Clairaut angle, thickness build-up, membrane resultants, first-ply pressure along the dome.
2. Progressive failure to last ply, plus a Hashin criterion next to Max Stress and Tsai-Wu.
3. Validation against published burst-test data (only sourced numbers; mismatches reported as they are).
4. Thermal stresses: cure cooling and cryogenic dT.
5. Simple, reproducible layup optimisation for a cylinder wall.

**Non-goals.** Certified design, liner and boss detail, fatigue, permeation, moisture, creep, temperature-dependent properties, 3D FE.

**Principles.** SI units. No data without a source (mark UNSOURCED). Equations change only with an engineering reason and a regression test. Honest limits stated in the app and in every report.
