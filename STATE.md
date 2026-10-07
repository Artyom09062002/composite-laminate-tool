# STATE (max 10 lines, updated at the end of every Claude session)

- Done (C4): Hashin / progressive-failure review verified (verification/REVIEW_C4.md): 3 defects fixed (pure-shear fibre damage, stop/new-failure batching, limitations), 6 wording or labelling fixes (assumed S_T, "last-ply" = model stop, termination rule, held steps), 3 partly confirmed; formulas unchanged.
- Done (C4): validation harness validation/run_validation.py -> results.json, tables and chart in validation/README.md; Report No. 2 in reports/ (3 pages).
- Result: no like-for-like comparison possible (inner radius NOT REPORTED in every source; Type III liner not modelled). Kangal glass: netting 0.26 of the measured total, 0.92 and 1.05 of the gain over the bare liner (plausibility only). Last-ply moves 64-243 bar with the unsourced stack order.
- Tests: 120 passing (with streamlit and reportlab installed).
- Next: read radius/dome from the paper figures and re-run; prefer a Type IV case (Luders CSV burst); then thermal (C5) and optimiser (C6).
- Open: degradation factors, S_T and the shear-dominated policy are assumptions; progressive failure is cylinder only; free-plate CLT for unsymmetric walls; isotensoid dome profile not implemented; C1 data unverified against the original PDFs.
