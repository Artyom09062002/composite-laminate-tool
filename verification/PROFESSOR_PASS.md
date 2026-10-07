# Professor-facing pass - 7 October 2026

Read-only review by the independent mechanics reviewer, verified and integrated by the parent. Numerical core and snapshot unchanged.

1. **Confirmed:** zero sidebar load was described as no stress anywhere. Summary now qualifies mechanical loading and points to thermal residual stress separately; infinite thermal load factor has no fictitious controlling face.
2. **Confirmed:** the exact proportional factor was called below the limit. It now means the initiation boundary; smaller factors lie below it.
3. **Confirmed:** quiz always accepted Decrease. It now compares the existing 0/90 study results for the entered card; edited cases with E1<E2, E1=E2 and E1>E2 are exercised. No new mechanics calculation was introduced.
4. **Confirmed:** universal stiffness-growth, monotonic-rotation and off-axis shear statements could be false under admissible edited inputs. Text now refers to entered properties, full compliance and possible coupling. Balance/symmetry alone does not force bend-twist terms either to vanish or to remain nonzero.
5. **Confirmed:** default progressive curve reaches about 79.94% calculated hoop strain. UI/PDF explicitly label large strains as linear-model extrapolation beyond small-strain CLT. Arrays are preserved, not clipped or presented as physical deformation.
6. **Confirmed:** current-layup netting omits shear equilibrium. For four +54.7356-degree plies the axial/hoop result is 3.333 MPa while positive fibre forces create a nonzero shear resultant. UI/PDF now explicitly qualify unbalanced walls; no new shear-equilibrium solver or changed pressure is introduced.
7. **Confirmed:** PDF accepted elastic/strength inputs but omitted them. Actual sidebar E1/E2/G12/nu12 and Xt/Xc/Yt/Yc/S are now printed, with separate named cards for other ply materials.
8. **Confirmed:** elastic/strength edits retain the selected CTE/reference provenance. Thermal block now discloses this combination is not a calibrated edited card.
9. **Confirmed:** study-wall count, current-stack count and sidebar/pressure load cases can be confused. A caption separates all three scopes; DEMO_ROUTE.md specifies the demonstration state and LIMITS_BEFORE_SHOW.md records limitations.

Synthetic edited cards used in regression tests are inputs for checking UI logic, not sourced engineering datasets. Demonstration numbers come from the existing v3 snapshot/benchmark. No new validation data, material, dependency, tab, mode or physics module.
