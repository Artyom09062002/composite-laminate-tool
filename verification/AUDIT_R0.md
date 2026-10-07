# R0 audit of the final (ChatGPT-built) version: 7 October 2026

Scope: report only. No equation, default or number in `core/` was changed. Baseline for comparison: commit d7046ff (C3+C4, last state with its own review files), SPEC.md and ACCEPTANCE.md.

## State found
- The project folder already held the final files; no other source copy was found, so nothing was copied. Local HEAD = 977979a (C5); C6 (optimiser, thermal review fixes) was uncommitted. `origin/main` = d7046ff (C4), so GitHub and the live app were two stages behind until this commit.
- Tests: `python -m unittest discover -s tests` = 144/144 passing before this task (Windows venv; 1 skip because reportlab was not installed in the venv, 7 skips on a machine without streamlit). After installing the already-required reportlab: 146/146, 0 skipped (144 + 2 snapshot tests). `pytest` from the project root also collects the ignored `_local/old_files` (4 obsolete-name failures per STATE.md); not re-run here (pytest is not installed in the venv).

## Against SPEC.md
- All five v3 items exist: dome (C2), progressive + Hashin (C3), validation harness (C4, executed, not passed), thermal (C5), optimiser (C6). No module outside the SPEC scope.
- New or changed files since C4 under `core/`: `thermal.py` (new, C5; later change is docstring-only), `optimise.py` (new, C6), `__init__.py` (exports). All other `core/*.py` are AST-identical to d7046ff (docstrings ignored): no equation, default or numerical change.
- `materials/database.py`: since C4 only thermal fields were added (CTE, reference temperature); no mechanical value changed; the later edits are provenance wording only. `validation/data.json`: note text only.

## Changed numbers or behaviour
- No number in `core/` changed. One behaviour change in `app.py`: thermal "cool from reference to final" now uses one user-editable common stress-free temperature (default: the first material's reference) instead of each material's own reference. Identical for a single-material laminate; different for hybrids. Documented in README and REVIEW_C6.md. Optimiser UI (about 100 lines) added to the Pressure vessel tab.

## Tests removed
- None. Test functions by commit: 43 (v2) -> 62 (C2) -> 120 (C4) -> 128 (C5) -> 144 (C6) -> 146 (this task). No test line was deleted or edited in any commit since 5080855. Skip conditions are the only weakening: app tests need streamlit and the PDF test needs reportlab (a silent skip hides them).

## Findings to decide later (not fixed)
1. Wording vs ACCEPTANCE C6: the vessel tab calls the netting value an "upper bound/upper estimate", while ACCEPTANCE C6 says it is not an upper bound on matrix-bearing CLT. Evidence (default T300/5208, 16-ply +/-54.74 deg, R = 100 mm): netting 20.000 MPa, last-ply model stop 20.101 MPa (see tests/snapshot_v3.json). The last-ply value depends on the assumed residual stiffness (E1 x 0.01), so it can pass the fibre-only value.
2. Report No. 2 still contains two points from the earlier review (verification/REVIEW_THROUGH_G5_2026-10-07.txt): "three usable" cases (reports/make_report_2.py line 106) while `strict_usable_cases` is empty, and "inconsistent with the burst values" for the Kartav radius (line 122). The PDF table wrapping was not re-checked.
3. The validation outcome (no like-for-like comparison possible) is nowhere in `app.py`; the app shows last-ply and netting numbers without their validation status.
4. ACCEPTANCE.md keeps historic test counts (43, 98, 144) next to the current count; label them by stage.
5. Untracked stray files not committed: `reports/Report_2_..._and_validation-1.pdf` (older text), two `*.page2.png`, `output/pdf/C5_thermal_laminates-1.png`.
6. Not checked in R0: original publications and DOIs behind validation/data.json, physical correctness of every formula, visual layout of every tab.
