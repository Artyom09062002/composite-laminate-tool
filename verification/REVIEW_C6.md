# C6 review: thermal provenance and cylinder optimiser

## Source check

- NASA-CR-162921 full text: https://ntrs.nasa.gov/api/citations/19800012968/downloads/19800012968.txt. The report says Pagano/Hahn suggest a stress-free temperature of 250 °F, considerably below 350 °F cure, and uses the Hahn approximation at 250 °F in residual-stress calculations. It does not support the former claim of a measured 250–300 °F range.
- MIT Roylance, *Laminated Composite Plates*: https://web.mit.edu/course/3/3.11/www/modules/laminates.pdf.

## Prior review points and disposition

1. Thermal-reference provenance was partially confirmed. The measured-range wording is corrected; 250 °F is described as the report's approximation. Treating cure temperature as stress-free remains an explicit assumption where measurement is unavailable.
2. Different material stress-free references in a hybrid are not an algebraic error. The thermal scenario uses one user-assumed common reference for all plies; material-specific values are not combined algebraically.
3. Constant properties at cryogenic temperatures are a model limitation, not a confirmed equation error. No temperature-dependent material model is added.
4. Rejected as an equation defect: `transform_cte` uses the inverse engineering-strain transform, with `alpha_xy = 2cs(alpha1-alpha2)` for alpha12=0. Independent tensor rotation with alpha12/2 and arbitrary positive/negative angles confirms the factor and sign.
5. Rejected as an equation defect: `compute_thermal_resultants` uses N_T = sum(Qbar alpha_bar dT (z1-z0)) and M_T = 1/2 sum(Qbar alpha_bar dT (z1^2-z0^2)). These are exact for the implemented piecewise-constant eigenstrain. They are equivalent loads, not external reactions.
6. Rejected as an equation defect: dT = T_final - T_reference is negative during cooling, and external resultants equal ABD [epsilon0,kappa] - [N_T,M_T]. Moving the equivalent thermal loads to the right requires the implemented plus sign. Reversing an unsymmetric stack reverses thermal curvature.
7. Rejected as an equation defect: local stress is Q [T_strain(theta)(epsilon0+z kappa) - alpha_local dT]. Stored strains are total strains, with free thermal strain subtracted exactly once. Integration of recovered stresses reproduces both external force AND moment for free and mechanically loaded unsymmetric hybrids.
8. Expanding limits and adding independent regression checks were accepted; the primary agent owns those changes and final audit.

## Optimiser method and physical interpretation

- `core/optimise.py` fixes one material, physical ply count and ply thickness. At fixed cylinder geometry this fixes mass without requiring or inventing density. It searches symmetric half-stack count vectors and a centre ply for odd counts; one canonical mirrored ordering represents each vector. This is not a search of all arbitrary stacking sequences.
- Exhaustive when the space fits the budget; otherwise homogeneous/balanced single-angle anchors plus seeded uniform weak count compositions (stars and bars), balanced sampling followed by general sampling. Local Python Random(seed), canonical angle sorting and deterministic tie breaking make results reproducible. Pressures equal at 12 significant digits favour balanced candidates nearest the netting angle.
- First-ply pressure uses the existing minimum Maximum Stress/Tsai-Wu; last-ply pressure is the existing Hashin discount model stop with the supplied rules. Both are evaluated for every candidate and can be ranked independently. Last-ply is not a verified burst prediction.
- The fibre-limited metric is explicitly the netting projection bound, not a CLT fibre-rupture criterion. The independent continuous reference is theta = atan(sqrt(2)), p = 2Xt h/(3R), with a balanced symmetric +/-theta CLT/progressive comparison when n is divisible by four. The reference may be outside the allowed discrete set. Other mixtures can tie the ideal fibre capacity.
- Unbalanced candidates may shear in the current CLT model. Their candidate exact netting pressure is `None`: the existing axial/hoop netting solver omits shear equilibrium for arbitrary unbalanced stacks. The projection bound is still an upper estimate but may be unattainable. No netting-only upper bound on matrix-bearing CLT is claimed.
- UI search is button-run and cached; changing radius, ply count/thickness, material, angle set, budget or discount rules hides stale results. The block states screening, not design, and excludes thermal preload, liner, end restraints, winding feasibility and stability.

## Verification (7 October 2026)

- `python -m unittest discover -s tests -v`: **144 tests passed**, including 10 optimiser mechanics/search checks, 2 optimiser UI checks and 12 thermal checks. This verifies implemented behaviour, not experimental validity.
- `git diff --check`: no whitespace errors.
- Independent sample using the built-in T300/5208 record, R=0.1 m, n=16, t=0.000125 m, default rules, seed=2026: 128 of 203,490 symmetric count vectors evaluated. The +/-54.735610317-degree candidate ranked first for both first-ply and last-ply: 8.860010 MPa and 20.100103 MPa. Continuous netting reference: 20.000000 MPa. The model stop slightly above netting reflects retained matrix stiffness in a different model, not validation or a netting-equilibrium error.
- Engineering conclusions and subagent documentation edits were checked by the primary agent. Existing user files and old output PDFs were preserved; they are historical artefacts, not regenerated C6 results.
