# R5 workflow input robustness

7 October 2026. Scope: workflow.py input preparation only; mechanics equations and snapshot values are unchanged.

Confirmed fixes:
- Editor material selections previously accepted malformed numeric/object cells as the first material. They now raise a ply-specific ValueError. Missing/None/NaN/blank cells still mean material 0, preserving the documented default. An empty available-material list is rejected.
- Extreme finite angles are reduced modulo 180 degrees before trigonometry at the parser/editor/angle-wall boundary. Angles within +/-360 degrees keep their entered value, including ordinary default +/-45 and 90 degree labels. Canonical reduction now reduces before adding offsets, avoiding loss of the 90 degree offset at very large floats.
- Angle-ply wall construction now rejects nonfinite angles, zero/negative/nonfinite thickness and noninteger/invalid counts. The shared helper continues to permit >100 plies because existing dome engineering studies use 200; the interactive parser/editor retain their 100-ply cap.
- Positive editor thickness that underflows to zero during mm-to-m conversion is rejected before reaching core.

Verified existing behavior: empty stack rejection, exactly 100 plies accepted, >100 rejected including after symmetric expansion, one-ply finite stiffness, missing angle/thickness rejection, all nonfinite angle/thickness values rejected. Tests compare extreme-angle stiffness against independently reduced finite-angle input, and preserve the standard [0/45/-45/90]s sequence.

Focused verification: `.venv\Scripts\python.exe -m unittest discover -s tests -p test_refine_inputs.py -v`: 8/8 passing (0.053 s). Full verification: `.venv\Scripts\python.exe -m unittest discover -s tests -v`: 161/161 passing, zero skipped (27.772 s). The historical full log is kept locally rather than in the public repository. This includes the unchanged v3 snapshot regression.

UI integration: existing app parser/editor handlers catch ValueError. No UI source changes required for these boundaries. Optional material blank defaults remain intentional, rather than silently deleting a ply. No dependencies, new mechanics features or snapshot regeneration.
