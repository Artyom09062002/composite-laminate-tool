
# STATE (max 10 lines, updated at the end of every Claude session)

- Done: v2 pushed (commit 38b7327): engineering constants, PDF export, pressure-vessel tab, 43 tests. SPEC.md and ACCEPTANCE.md written.
- Done: C2 dome module core/dome.py, tests/test_dome.py (19), Dome subsection in the Pressure vessel tab; 62 tests pass. first_ply_limit moved to core/failure.py (re-exported by workflow); core.vessel.first_ply_under_unit_load shared by screen_cylinder and the dome.
- C1 output is in validation/ (data.json, README.md), not committed here; per its README no case is fully usable (inner radius NOT REPORTED in all four sources), three are CONDITIONAL.
- Next: G3 (independent review of core/dome.py), then C3 (progressive failure + Hashin).
- Open issues: validation cases have UNSOURCED gaps (geometry); progressive failure, thermal, optimiser not started; isotensoid dome profile not implemented; dome model is helical plies only, membrane theory, no slippage.
