# STATE (v4 refinement)

## Public repository file audit — 2026-10-08

- Reviewed the 109 tracked files and removed seven redundant/generated files from the public tree: the GitHub copy of the presentation (the user supplied a separate OneDrive link), three saved `output/pdf/` examples, two full test logs and `verification/benchmark_results.json`. Their local copies remain; `.gitignore` prevents accidental re-addition.
- Retained the app, fonts, cited material/validation data, tests, reference comparisons, the runtime-read `verification/qa_results.json`, and report deliverables. The four source documents in `verification/sources/` remain untracked and ignored. Replaced a local user-profile path in the public Kaw transcription/review.
- No mechanics or UI source was changed. Full suite before cleanup: 175 tests, OK (152.916 s). Full suite after cleanup: 175 tests, OK (152.466 s).

## Primary-source correction during presentation preparation — 2026-10-08

- Visual rereading of the supplied Kaw PDF page 9 found the full local stress table as an embedded image. The earlier claims that this table was absent and its page was NOT REPORTED were incorrect; text extraction had omitted the image. Doc2 image11.png reproduces the same table.
- Source transcription, reference provenance, Verification caption, report generator and README now identify PDF p. 9. All 27 values still agree within printed precision; no mechanics equation or numeric reference value was changed. Earlier source-absence entries below are superseded by this correction.
- Reran the source-comparison generator and the complete suite after the correction: 175 tests, OK, no skips (92.643 s). A separate fresh run before the metadata correction also passed 175 tests (94.407 s). Presentation outputs are stored in the task workspace, not published as copies of the supplied PDF/Word documents.

## Cloud publication and hosting choice — 2026-10-08

- User explicitly authorized push after local source exclusion. Pushed ba5496e to origin/main; remote HEAD matched the local commit. The four verification/sources/ documents were not in the pushed tree.
- Public app https://composite-laminate-tool.streamlit.app/ was asleep; woke it and verified the new sidebar SI labels and Kaw Verification section in the cloud. Switching its reference angle from 30 to -45 refreshed Qbar successfully. Only the verification report download is present in the public section; local PDF/Doc2 source downloads are absent.
- User chose to retain free Streamlit Community Cloud. This hosting is independent of the PC; per current official documentation it sleeps after 12 hours without traffic and viewers can wake it. No paid host or keepalive automation was created. README explains the public/local URL distinction and links the hosting rule.

## Local reference documents excluded from Git — 2026-10-08

- At the user's request, the four files in verification/sources/ are kept only on disk: Kaw_section4_3_worked_example.pdf, Roylance_netting.pdf, Roylance_pressure_vessels.pdf and Doc2.docx. The whole directory is ignored and removed from the amended commit's tracked tree; no source document was deleted locally and no push was performed.
- Numeric reference data, VERIFY_*.md reports, source/page provenance and official Roylance links remain tracked. The Verification page computes from verification/kaw_reference.json and only offers source-document downloads when those local files are present. The previous entry about source documents being included in commit preparation is superseded by this exclusion.

## Commit and repository cleanup — 2026-10-08

- User explicitly requested committing all current work and cleaning old unnecessary files; this supersedes the earlier uncommitted-only instruction. All supplied sources, new guide, reference comparisons, tests and code changes are included in the commit preparation.
- Moved ignored `_local/` and its associated `node_modules/` to `C:\Work\composite-engineering-app-archive\2026-10-08-cleanup\`: 442 files, 26087643 bytes, SHA256 checked before/after; manifest.json retained there. Generated Python/pytest caches and the empty `_kaw_render` directory were also moved out after testing. Direct deletion was policy-blocked; no cache/source file was permanently deleted. See verification/CLEANUP_2026-10-08.md.
- Current sources, report artifacts, active tests/snapshot, existing Russian PDF guide, .git history and .venv preserved. README now documents sidebar SI loads and the Kaw/Doc2 Verification page; older audit/report dates are retained as historical evidence.
- Before cleanup: 175 tests passed (49.702 s). After cleanup, `python verification/run_refine_qa.py`: 175 tests passed, 0 failures/errors/skips (97.665 s); qa_results.json and qa_test_log.txt refreshed. Validated equations remain unchanged. Local commit requested; no push requested.

## Verification page from Doc2 — 2026-10-08

- Inspected all 12 images in the supplied Doc2.docx. Verification now presents fixed Kaw source/app Qbar and full ABD matrices, midplane strains/curvatures, local strain/stress at both boundaries and each midpoint, and integrated ply forces/shares. Sidebar inputs do not alter this benchmark.
- All 27 local stress values in the additional source table match fresh core predictions within printed-digit tolerances. No current mechanics defect was found. The full stress table is sourced to Doc2 image11.png; its original publication page is NOT REPORTED. Its absence from the earlier provided PDF remains correctly documented in the PDF-only report.
- Full suite before this UI change: 171 tests, OK (53.081 s). Final full suite: 175 tests, OK, no skips (44.542 s), including AppTest angle switching and sidebar independence. Local browser inspection confirms rendering; temporary preview runs at http://localhost:8502.
- Updated: app.py (Verification renderer and scoped vessel-dataset status), STATE.md. Created: verification_view.py, verification/kaw_reference.json, verification/sources/Doc2.docx, tests/test_verification_view.py, verification/VERIFY_DOC2_COMPARISON.md. Q/Qbar/ABD/transformations/failure/vessel mechanics unchanged; no commits or push.
- Doc2 copy SHA256 matches the supplied file: 1A0D3EA2879952C732F21DFF99213343A3A9DB276852240FDFBE7AF38FEDB910. Extracted working images remain in ignored _local/doc2_review/.

## Kaw / ply forces / vessel explanation — 2026-10-08

- Full suite before changes: `python -m unittest discover -s tests -q`, 163 tests, OK, no skips (77.901 s). Final full suite: 171 tests, OK, no skips (77.422 s), including Streamlit AppTest. Intermediate 170-test run also passed before the requested sidebar-unit follow-up.
- Added exact global mechanical ply-force integration and per-ply force/share table; zero applied components show n/a. Existing Q/Qbar/ABD/transforms/failure/progressive/vessel equations unchanged.
- Sidebar forces now N/m, moments N·m/m (= N). Preset physical loads and existing-session loads are preserved; AppTest checks conversion once and presets. Pressure vessel received the requested burst-validation caption only.
- Kaw: all printed stiffness, strain and stress values agree within their last-digit precision; part (e) forces agree within 2.5 N/m propagated from printed midpoint stress precision. Documented Poisson-substitution typo, clipped A/B/D expansions, and engineering shear mislabel. Source copy SHA256: BDD4ACF691D512DB40A925EA084DC134BEC4627D6AB4E3CB1D6A314F84FC732F (matches supplied Downloads PDF).
- Vessel: reproduced Roylance's worked equilibrium angle; no comparable fully specified numerical netting pressure/thickness answer found in the inspected sources. The other published numerical bottle example uses strain-compatible fibre netting, unlike the app's pressure-bound solver; no forced comparison or tuning. Default-input core outputs are illustrative, not external strength validation.
- Still unvalidated by this work: strengths/failure criteria, progressive/model-stop pressure, experimental burst pressure, liner and local dome/end effects. No files deleted, no commit or push.

Changed tracked files:

- [app.py](app.py)
- [core/response.py](core/response.py)
- [.gitignore](.gitignore) — whitelist only the new Russian guide; other docs remain ignored.
- [STATE.md](STATE.md)

Created deliverables:

- [tests/test_ply_force_resultants.py](tests/test_ply_force_resultants.py)
- [tests/test_app_ply_forces.py](tests/test_app_ply_forces.py)
- [docs/PRESSURE_VESSEL_EXPLAINED_RU.md](docs/PRESSURE_VESSEL_EXPLAINED_RU.md)
- [verification/KAW_SOURCE_TRANSCRIPTION.md](verification/KAW_SOURCE_TRANSCRIPTION.md)
- [verification/VERIFY_KAW_4_3.md](verification/VERIFY_KAW_4_3.md)
- [verification/VERIFY_VESSEL_EXAMPLE.md](verification/VERIFY_VESSEL_EXAMPLE.md)
- [verification/verify_kaw_vessel.py](verification/verify_kaw_vessel.py)
- [verification/kaw_vessel_results.json](verification/kaw_vessel_results.json)
- [verification/sources/Kaw_section4_3_worked_example.pdf](verification/sources/Kaw_section4_3_worked_example.pdf)
- [verification/sources/Roylance_pressure_vessels.pdf](verification/sources/Roylance_pressure_vessels.pdf)
- [verification/sources/Roylance_netting.pdf](verification/sources/Roylance_netting.pdf)

Ignored working evidence is retained in `_local/kaw_review/` (rendered PDF PNGs and script output); no source files were removed. All deliverables remain uncommitted.

## Earlier status

- R0: baseline 116a072; v3 snapshot retained; core/, source material values, validation numbers and dependencies unchanged.
- R0b/R1: independent thermal/optimiser numerical review and clarity inventory saved in verification/; no confirmed equation defect.
- R2/R3: shared style, 15-term glossary, visible unscored-validation status, model limits, coloured initiation events and dome edge shading.
- R4: existing one-page PDF export covers mechanical summary and cylinder pressures/curve; 4/16/40-ply page/number tests pass; Report No. 2 wording/wrapping corrected.
- R5/G2 + professor pass: input/text fixes, custom-card quiz, thermal/mechanical scope, unbalanced netting and large-strain qualifiers; current suite 163 passed, 0 skipped; snapshot unchanged.
- R7: professor pass deployed; all eleven local/live tabs and PDF download checked; PDFs are one page with identical extracted text; DEMO_ROUTE.md and LIMITS_BEFORE_SHOW.md ready.
- Deferred: optional R6 awaits original pages (A5); personal A1-A5 remain user's work; no experimental burst validation, liner/boss, temperature-dependent properties or stability model.
- After presentation: step-by-step navigation, failure animation, separate two-layup screen/report generator, new physics/tabs only after rescoping; isotensoid, fatigue, permeation, moisture, creep and 3D FE remain out of scope.
