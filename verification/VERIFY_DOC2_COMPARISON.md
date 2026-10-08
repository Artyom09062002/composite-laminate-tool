# Doc2 comparison evidence

Source: verification/sources/Doc2.docx, copied byte-for-byte from the supplied Downloads file. SHA256: 1A0D3EA2879952C732F21DFF99213343A3A9DB276852240FDFBE7AF38FEDB910.

All 12 embedded images were inspected. Images 1, 2, 6, 8, 10 and 11 contain reference values; images 3, 4, 5, 7, 9 and 12 are app screenshots used as a presentation reference. Screenshot display digits are not substituted for fresh core predictions. Original publication page of the local stress table in image11.png: NOT REPORTED. The local strain table is also present in the supplied Kaw PDF p. 8.

Verification now displays fixed Kaw inputs, source/app Qbar and ABD matrices, midplane solution, local strain/stress on boundaries and midpoints, and ply force shares. Values are paired by numeric z, not by the words Top and Bottom. No stiffness, transformation or failure equation was changed.

## Full local stress table from Doc2 image11.png

| Ply | z [m] | Quantity | Source [Pa] | App [Pa] | Difference [Pa] | Check |
|---|---|---|---|---|---|---|
| 1 | -0.0075 | sigma1 | -1.438e7 | -14375950.227501117 | 4049.772498883307 | Within source precision |
| 1 | -0.0075 | sigma2 | -1.770e7 | -17699403.81551337 | 596.184486631304 | Within source precision |
| 1 | -0.0075 | tau12 | -1.831e7 | -18311218.73807911 | -1218.7380791082978 | Within source precision |
| 1 | -0.004999999999999999 | sigma1 | -6.690e6 | -6690373.370139015 | -373.3701390149072 | Within source precision |
| 1 | -0.004999999999999999 | sigma2 | -1.284e7 | -12842686.363299573 | -2686.3632995728403 | Within source precision |
| 1 | -0.004999999999999999 | tau12 | -1.249e7 | -12485059.60279946 | 4940.397200539708 | Within source precision |
| 1 | -0.0024999999999999996 | sigma1 | 9.952e5 | 995203.4872230868 | 3.487223086762242 | Within source precision |
| 1 | -0.0024999999999999996 | sigma2 | -7.986e6 | -7985968.911085777 | 31.08891422301531 | Within source precision |
| 1 | -0.0024999999999999996 | tau12 | -6.659e6 | -6658900.467519814 | 99.53248018585145 | Within source precision |
| 2 | -0.0024999999999999996 | sigma1 | -2.043e7 | -20432661.35961964 | -2661.359619639814 | Within source precision |
| 2 | -0.0024999999999999996 | sigma2 | -4.388e6 | -4388301.78287909 | -301.7828790899366 | Within source precision |
| 2 | -0.0024999999999999996 | tau12 | 7.944e6 | 7944277.5860108035 | 277.5860108034685 | Within source precision |
| 2 | 4.336808689942018e-19 | sigma1 | -1.302e7 | -13022257.170200262 | -2257.1702002622187 | Within source precision |
| 2 | 4.336808689942018e-19 | sigma2 | 5.146e5 | 514616.2436389788 | 16.243638978805393 | Within source precision |
| 2 | 4.336808689942018e-19 | tau12 | 2.135e6 | 2134625.025396236 | -374.9746037637815 | Within source precision |
| 2 | 0.0025000000000000005 | sigma1 | -5.612e6 | -5611852.980780883 | 147.01921911723912 | Within source precision |
| 2 | 0.0025000000000000005 | sigma2 | 5.418e6 | 5417534.270157048 | -465.7298429524526 | Within source precision |
| 2 | 0.0025000000000000005 | tau12 | -3.675e6 | -3675027.535218331 | -27.5352183310315 | Within source precision |
| 3 | 0.0025000000000000005 | sigma1 | 4.763e6 | 4763298.678286892 | 298.67828689236194 | Within source precision |
| 3 | 0.0025000000000000005 | sigma2 | 3.676e6 | 3675580.867856816 | -419.132143184077 | Within source precision |
| 3 | 0.0025000000000000005 | tau12 | -4.993e6 | -4993417.803039482 | -417.8030394818634 | Within source precision |
| 3 | 0.005 | sigma1 | 2.610e7 | 26100457.4713778 | 457.4713778011501 | Within source precision |
| 3 | 0.005 | sigma2 | 6.240e6 | 6240243.188622065 | 243.18862206488848 | Within source precision |
| 3 | 0.005 | tau12 | -1.082e7 | -10819576.93831913 | 423.06168087013066 | Within source precision |
| 3 | 0.0075 | sigma1 | 4.744e7 | 47437616.26446871 | -2383.7355312928557 | Within source precision |
| 3 | 0.0075 | sigma2 | 8.805e6 | 8804905.509387314 | -94.49061268568039 | Within source precision |
| 3 | 0.0075 | tau12 | -1.665e7 | -16645736.073598778 | 4263.926401222125 | Within source precision |

All 27 printed local stress components agree within half a unit of their last printed digit. At ply 2, z=-0.0025 m, current core tau12 is positive, consistent with the reference table. No current mechanics defect was found.

Full suite immediately before the Verification page change: 171 tests passed. Final suite: 175 tests passed, no skips, including AppTest angle switching, midpoint pairing, zero-reference differences and sidebar independence. Local browser inspection confirms the new section renders.

New files for this follow-up: verification_view.py, verification/kaw_reference.json, verification/sources/Doc2.docx, tests/test_verification_view.py, verification/VERIFY_DOC2_COMPARISON.md. Updated: app.py, STATE.md. Changes remain uncommitted.
