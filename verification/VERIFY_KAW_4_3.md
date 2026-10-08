# Verification: Kaw section 4.3

Source: [provided PDF](sources/Kaw_section4_3_worked_example.pdf), copied byte-for-byte from the supplied Downloads file. All 10 pages were read as text; numerical image tables on pp. 6–8 were inspected visually. The expanded A/B/D arithmetic on p. 4 is clipped at the right edge: those missing terms could not be read. The announced local stress table is absent. Only visible data are used; absent entries are NOT REPORTED.

The PDF identifies its material inputs as Table 2.1 (p. 1). The original book table itself was not supplied/read. No strength data are reported here. See [literal transcription](KAW_SOURCE_TRANSCRIPTION.md) for every visible input, matrix, table and result.

## Inputs and coordinate mapping

E1=38.6 GPa, E2=8.27 GPa, G12=4.14 GPa, ν12=0.26 (p. 1); each ply 5 mm; [30/-45/-60]; [Nx,Ny,Nxy,Mx,My,Mxy]=[1500,0,0,0,1500,0], N in N/m and M in N (pp. 1,5). No fitted values. h=0.015 m and coordinates [-0.0075,-0.0025,0.0025,0.0075] m (p. 3).

The source uses z downward and calls the ply-2 face at z=-0.0025 m Top. In the app the identical numeric coordinate and ply sequence use z upward, so that face is Bottom. This check identifies algebraic coordinates, angles and signed generalized loads with the source; it is not a physical reflection of a fixed specimen. A physical change z_app=-z_Kaw would also reverse ply order and signs of B, M and κ (and any corresponding axis handedness). No app convention is changed. Engineering shear γ12=2ε12 throughout.

## Comparison

Every computed value below uses Python float repr without decimal rounding. Source mantissas retain printed precision. Difference is 100(app-source)/abs(source); zeros use |app-source| with the quantity's units. Symmetric matrices show their six independent entries; A/B/D specify the entire ABD of p. 5. Hand values independently form Q and scalar Qbar polynomials, integrate A/B/D, solve the hand ABD, and transform strains/stresses. They share NumPy's linear solver, but no core stiffness/transformation implementation. Ply-load hand values instead multiply the *printed* midpoint σx by printed thickness.

| Quantity | Source (page) | Hand check | App | Difference % or absolute |
|---|---|---|---|---|
| ν21 [-] | 0.0557 (p. 2) | 0.05570466321243523 | 0.05570466321243523 | 0.008372015144041475 % |
| Q11 [Pa] | 39.17*10^9 (p. 2) | 39167267860.937645 | 39167267860.937645 | -0.006975080577878584 % |
| Q12 [Pa] | 2.182*10^9 (p. 2) | 2181799465.1447697 | 2181799465.1447697 | -0.009190414996807122 % |
| Q22 [Pa] | 8.392*10^9 (p. 2) | 8391536404.402961 | 8391536404.402961 | -0.005524256399407401 % |
| Q66 [Pa] | 4.14*10^9 (p. 2) | 4140000000.0 | 4140000000.0 | 1.1517805753698672e-14 % |
| Q16 [Pa] | 0 (p. 2) | 0.0 | 0.0 | 0.0 absolute |
| Q26 [Pa] | 0 (p. 2) | 0.0 | 0.0 | 0.0 absolute |
| Qbar ply 1, 11 [Pa] | 26.48*10^9 (p. 2) | 26479233996.481903 | 26479233996.481903 | -0.002892762530577507 % |
| Qbar ply 1, 12 [Pa] | 7.176*10^9 (p. 2) | 7175900465.466845 | 7175900465.466844 | -0.001387047563494913 % |
| Qbar ply 1, 16 [Pa] | 9.546*10^9 (p. 2) | 9546486872.247854 | 9546486872.247854 | 0.005100274961808431 % |
| Qbar ply 1, 22 [Pa] | 11.09*10^9 (p. 2) | 11091368268.214558 | 11091368268.214554 | 0.012337855857113013 % |
| Qbar ply 1, 26 [Pa] | 3.780*10^9 (p. 2) | 3779795758.4555955 | 3779795758.4555955 | -0.005403215460436685 % |
| Qbar ply 1, 66 [Pa] | 9.134*10^9 (p. 2) | 9134101000.322075 | 9134101000.322073 | 0.0011057622298334003 % |
| Qbar ply 2, 11 [Pa] | 17.12*10^9 (p. 2) | 17120600798.907536 | 17120600798.90754 | 0.0035093394131860997 % |
| Qbar ply 2, 12 [Pa] | 8.841*10^9 (p. 2) | 8840600798.907536 | 8840600798.907536 | -0.004515338677349248 % |
| Qbar ply 2, 16 [Pa] | -7.694*10^9 (p. 2) | -7693932864.133673 | -7693932864.133672 | 0.0008725742959220099 % |
| Qbar ply 2, 22 [Pa] | 17.12*10^9 (p. 2) | 17120600798.907534 | 17120600798.907534 | 0.0035093394131526763 % |
| Qbar ply 2, 26 [Pa] | -7.694*10^9 (p. 2) | -7693932864.13367 | -7693932864.13367 | 0.0008725742959467999 % |
| Qbar ply 2, 66 [Pa] | 10.80*10^9 (p. 2) | 10798801333.762766 | 10798801333.762768 | -0.01109876145585378 % |
| Qbar ply 3, 11 [Pa] | 11.09*10^9 (p. 3) | 11091368268.214561 | 11091368268.21456 | 0.012337855857164608 % |
| Qbar ply 3, 12 [Pa] | 7.176*10^9 (p. 3) | 7175900465.4668455 | 7175900465.4668455 | -0.0013870475634683334 % |
| Qbar ply 3, 16 [Pa] | -3.780*10^9 (p. 3) | -3779795758.455598 | -3779795758.455599 | 0.005403215460348381 % |
| Qbar ply 3, 22 [Pa] | 26.48*10^9 (p. 3) | 26479233996.481895 | 26479233996.48189 | -0.002892762530620725 % |
| Qbar ply 3, 26 [Pa] | -9.546*10^9 (p. 3) | -9546486872.247856 | -9546486872.247854 | -0.005100274961808431 % |
| Qbar ply 3, 66 [Pa] | 9.134*10^9 (p. 3) | 9134101000.322079 | 9134101000.322079 | 0.001105762229896046 % |
| A11 [N/m] | 2.735*10^8 (p. 4) | 273456015.31802 | 273456015.31802 | -0.016082150632546196 % |
| A12 [N/m] | 1.160*10^8 (p. 4) | 115962008.64920613 | 115962008.64920613 | -0.032751164477459835 % |
| A16 [N/m] | -9.636*10^6 (p. 4) | -9636208.75170708 | -9636208.751707083 | -0.002166373049840331 % |
| A22 [N/m] | 2.735*10^8 (p. 4) | 273456015.3180199 | 273456015.31801987 | -0.016082150632589783 % |
| A26 [N/m] | -6.730*10^7 (p. 4) | -67303119.88962966 | -67303119.88962965 | -0.004635794397692624 % |
| A66 [N/m] | 1.453*10^8 (p. 4) | 145335016.6720346 | 145335016.6720346 | 0.02409956781458461 % |
| B11 [N] | -3.847*10^5 (p. 4) | -384696.6432066835 | -384696.6432066836 | 0.0008725742959116726 % |
| B12 [N] | 0 (p. 4) | 2.9103830456733704e-11 | 5.820766091346741e-11 | 5.820766091346741e-11 absolute |
| B16 [N] | -3.332*10^5 (p. 4) | -333157.0657675863 | -333157.06576758635 | 0.012885423893653167 % |
| B22 [N] | 3.847*10^5 (p. 4) | 384696.64320668345 | 384696.64320668345 | -0.0008725742959570646 % |
| B26 [N] | -3.332*10^5 (p. 4) | -333157.0657675863 | -333157.06576758623 | 0.012885423893688106 % |
| B66 [N] | 0 (p. 4) | 8.731149137020111e-11 | 1.4551915228366852e-10 | 1.4551915228366852e-10 absolute |
| D11 [N m] | 5.266*10^3 (p. 4) | 5266.025314999599 | 5266.025314999598 | 0.00048072540064313384 % |
| D12 [N m] | 2.036*10^3 (p. 4) | 2035.5626343858903 | 2035.56263438589 | -0.021481611694986337 % |
| D16 [N m] | 7.008*10^2 (p. 4) | 700.760954324642 | 700.760954324642 | -0.005571586095606602 % |
| D22 [N m] | 5.266*10^3 (p. 4) | 5266.025314999597 | 5266.025314999595 | 0.0004807254005913206 % |
| D26 [N m] | -8.611*10^2 (p. 4) | -861.0512223274277 | -861.0512223274275 | 0.005664577002967747 % |
| D66 [N m] | 2.586*10^3 (p. 4) | 2586.3065348139244 | 2586.306534813924 | 0.011853627761945772 % |
| εx0 [-] | 1.624*10^-4 (p. 5) | 0.00016236048308499525 | 0.0001623604830849953 | -0.02433307574181923 % |
| εy0 [-] | -3.532*10^-4 (p. 5) | -0.00035324942643100355 | -0.0003532494264310038 | -0.01399389326268462 % |
| γxy0 [-] | 4.908*10^-4 (p. 5) | 0.0004907720615009548 | 0.0004907720615009548 | -0.005692440718273767 % |
| κx [1/m] | -1.403*10^-1 (p. 5) | -0.1402803890196507 | -0.14028038901965076 | 0.013977890484140743 % |
| κy [1/m] | 4.210*10^-1 (p. 5) | 0.4210386989624327 | 0.42103869896243284 | 0.009192152596865509 % |
| κxy [1/m] | 1.536*10^-1 (p. 5) | 0.1535946725847576 | 0.15359467258475765 | -0.00346836929841646 % |
| ply 2 z=-0.0025 m global strain component 1 | 5.131*10^-4 (p. 5) | 0.000513061455634122 | 0.0005130614556341222 | -0.007512057274964602 % |
| ply 2 z=-0.0025 m global strain component 2 | -1.406*10^-3 (p. 5) | -0.0014058461738370852 | -0.0014058461738370859 | 0.010940694375109349 % |
| ply 2 z=-0.0025 m global strain component 3 | 1.068*10^-4 (p. 5) | 0.00010678538003906085 | 0.00010678538003906074 | -0.013689102003057025 % |
| ply 2 z=-0.0025 m global stress [Pa] component 1 | -4.466*10^6 (p. 6) | -4466203.9852385605 | -4466203.98523856 | -0.004567515417813348 % |
| ply 2 z=-0.0025 m global stress [Pa] component 2 | -2.035*10^7 (p. 6) | -20354759.157260153 | -20354759.15726016 | -0.023386522162952793 % |
| ply 2 z=-0.0025 m global stress [Pa] component 3 | 8.022*10^6 (p. 6) | 8022179.788370269 | 8022179.78837027 | 0.002241191352160085 % |
| ply 2 z=-0.0025 m local engineering strain component 1 | -4.998*10^-4 (p. 7) | -0.000499785049121012 | -0.000499785049121012 | 0.002991372346531699 % |
| ply 2 z=-0.0025 m local engineering strain component 2 | -3.930*10^-4 (p. 7) | -0.0003929996690819512 | -0.0003929996690819516 | 8.42030657477914e-05 % |
| ply 2 z=-0.0025 m local engineering strain component 3 | 1.919*10^-3 (p. 7) | 0.0019189076294712072 | 0.001918907629471208 | -0.004813472057948984 % |
| ply 2 z=-0.0025 m local stress [Pa] component 1 | -2.043*10^7 (p. 8) | -20432661.35961963 | -20432661.359619632 | -0.013026723542008631 % |
| ply 2 z=-0.0025 m local stress [Pa] component 2 | -4.388*10^6 (p. 8) | -4388301.782879086 | -4388301.78287909 | -0.006877458502505393 % |
| ply 2 z=-0.0025 m local stress [Pa] component 3 | 7.944*10^6 (p. 8) | 7944277.586010798 | 7944277.586010802 | 0.0034942851309366298 % |
| Nx ply 1 [N/m] | 12920 (p. 9) | 12920.0 | 12919.635826790141 | -0.0028186780948805225 % |
| Nx ply 2 [N/m] | -20595 (p. 9) | -20595.0 | -20595.97718942202 | -0.004744789618942381 % |
| Nx ply 3 [N/m] | 9175 (p. 9) | 9175.0 | 9176.341362631863 | 0.014619756205595379 % |
| Nx share ply 1 [%] | 861.33 (p. 10) | 861.3333333333334 | 861.3090551193428 | -0.0024316906014216896 % |
| Nx share ply 2 [%] | -1373 (p. 10) | -1373.0 | -1373.065145961468 | -0.004744789618939069 % |
| Nx share ply 3 [%] | 611.67 (p. 10) | 611.6666666666666 | 611.7560908421242 | 0.01407472037605828 % |

Ny_k and Nxy_k: NOT REPORTED in part (e). These app predictions are not source comparisons:

| Ply | Nx_k [N/m] | Ny_k [N/m] | Nxy_k [N/m] |
|---|---|---|---|
| 1 | 12919.635826790141 | -110584.93449398309 | -17892.500646723372 |
| 2 | -20595.97718942202 | -41942.22744338437 | 33842.183534598094 |
| 3 | 9176.341362631863 | 152527.16193736743 | -15949.682887874726 |

Sum of app ply forces [N/m]: [1499.9999999999836, -2.9103830456733704e-11, -3.637978807091713e-12]. Applied N: [1500,0,0] N/m. Residual [N/m]: [-1.6370904631912708e-11, -2.9103830456733704e-11, -3.637978807091713e-12].

## All printed through-thickness tables

z, not the source's Top/Bottom words, selects each point. Strain units are dimensionless; global stresses are Pa.

| Quantity | Source (page) | Hand check | App | Difference % or absolute |
|---|---|---|---|---|
| ply 1, z=-0.0075 m, global strain component 1 | 1.214(10^−3) (p. 6) | 0.0012144634007323755 | 0.001214463400732376 | 0.03817139475913599 % |
| ply 1, z=-0.0075 m, global strain component 2 | −3.511(10^−3) (p. 6) | -0.0035110396686492485 | -0.0035110396686492498 | -0.0011298390558114268 % |
| ply 1, z=-0.0075 m, global strain component 3 | −6.612(10^−4) (p. 6) | -0.000661187982884727 | -0.0006611879828847274 | 0.0018174705493957067 % |
| ply 1, z=-0.005 m, global strain component 1 | 8.638(10^−4) (p. 6) | 0.0008637624281832487 | 0.0008637624281832492 | -0.004349596752823687 % |
| ply 1, z=-0.005 m, global strain component 2 | −2.458(10^−3) (p. 6) | -0.002458442921243167 | -0.002458442921243168 | -0.018019578648003486 % |
| ply 1, z=-0.005 m, global strain component 3 | −2.772(10^−4) (p. 6) | -0.0002772013014228331 | -0.00027720130142283345 | -0.00046948875664931075 % |
| ply 1, z=-0.0025 m, global strain component 1 | 5.131(10^−4) (p. 6) | 0.000513061455634122 | 0.0005130614556341222 | -0.007512057274964602 % |
| ply 1, z=-0.0025 m, global strain component 2 | −1.406(10^−3) (p. 6) | -0.0014058461738370852 | -0.0014058461738370859 | 0.010940694375109349 % |
| ply 1, z=-0.0025 m, global strain component 3 | 1.068(10^−4) (p. 6) | 0.00010678538003906085 | 0.00010678538003906069 | -0.013689102003107785 % |
| ply 2, z=-0.0025 m, global strain component 1 | 5.131(10^−4) (p. 6) | 0.000513061455634122 | 0.0005130614556341222 | -0.007512057274964602 % |
| ply 2, z=-0.0025 m, global strain component 2 | −1.406(10^−3) (p. 6) | -0.0014058461738370852 | -0.0014058461738370859 | 0.010940694375109349 % |
| ply 2, z=-0.0025 m, global strain component 3 | 1.068(10^−4) (p. 6) | 0.00010678538003906085 | 0.00010678538003906069 | -0.013689102003107785 % |
| ply 2, z=0.0 m, global strain component 1 | 1.624(10^−4) (p. 6) | 0.00016236048308499525 | 0.0001623604830849953 | -0.02433307574181923 % |
| ply 2, z=0.0 m, global strain component 2 | −3.532(10^−4) (p. 6) | -0.00035324942643100355 | -0.0003532494264310038 | -0.01399389326268462 % |
| ply 2, z=0.0 m, global strain component 3 | 4.908(10^−4) (p. 6) | 0.0004907720615009548 | 0.0004907720615009548 | -0.005692440718273767 % |
| ply 2, z=0.0025 m, global strain component 1 | −1.883(10^−4) (p. 6) | -0.0001883404894641315 | -0.0001883404894641316 | -0.02150263628869495 % |
| ply 2, z=0.0025 m, global strain component 2 | 6.993(10^−4) (p. 6) | 0.0006993473209750782 | 0.0006993473209750783 | 0.006766906203104747 % |
| ply 2, z=0.0025 m, global strain component 3 | 8.748(10^−4) (p. 6) | 0.0008747587429628488 | 0.000874758742962849 | -0.004716167941357876 % |
| ply 3, z=0.0025 m, global strain component 1 | −1.883(10^−4) (p. 6) | -0.0001883404894641315 | -0.0001883404894641316 | -0.02150263628869495 % |
| ply 3, z=0.0025 m, global strain component 2 | 6.993(10^−4) (p. 6) | 0.0006993473209750782 | 0.0006993473209750783 | 0.006766906203104747 % |
| ply 3, z=0.0025 m, global strain component 3 | 8.748(10^−4) (p. 6) | 0.0008747587429628488 | 0.000874758742962849 | -0.004716167941357876 % |
| ply 3, z=0.005 m, global strain component 1 | −5.390(10^−4) (p. 6) | -0.0005390414620132582 | -0.0005390414620132585 | -0.007692395780794739 % |
| ply 3, z=0.005 m, global strain component 2 | 1.752(10^−3) (p. 6) | 0.00175194406838116 | 0.0017519440683811606 | -0.003192443997686722 % |
| ply 3, z=0.005 m, global strain component 3 | 1.259(10^−3) (p. 6) | 0.0012587454244247427 | 0.001258745424424743 | -0.02022045871777784 % |
| ply 3, z=0.0075 m, global strain component 1 | −8.897(10^−4) (p. 6) | -0.000889742434562385 | -0.0008897424345623854 | -0.0047695360666885 % |
| ply 3, z=0.0075 m, global strain component 2 | 2.805(10^−3) (p. 6) | 0.002804540815787241 | 0.0028045408157872423 | -0.016370203663381742 % |
| ply 3, z=0.0075 m, global strain component 3 | 1.643(10^−3) (p. 6) | 0.0016427321058866367 | 0.0016427321058866372 | -0.016305180362931694 % |
| ply 1, z=-0.0075 m, global stress component 1 | 6.512(10^5) (p. 7) | 651166.9769259576 | 651166.9769259609 | -0.005071110878246568 % |
| ply 1, z=-0.0075 m, global stress component 2 | −3.273(10^7) (p. 7) | -32726521.019940432 | -32726521.019940436 | 0.010629331071078869 % |
| ply 1, z=-0.0075 m, global stress component 3 | −7.717(10^6) (p. 7) | -7716511.751280981 | -7716511.75128098 | 0.006326923921469682 % |
| ply 1, z=-0.005 m, global stress component 1 | 2.584(10^6) (p. 7) | 2583927.165358031 | 2583927.1653580354 | -0.002818678094606829 % |
| ply 1, z=-0.005 m, global stress component 2 | −2.212(10^7) (p. 7) | -22116986.89879661 | -22116986.898796614 | 0.013621614843532845 % |
| ply 1, z=-0.005 m, global stress component 3 | −3.579(10^6) (p. 7) | -3578500.1293446743 | -3578500.1293446724 | 0.013966768799317398 % |
| ply 1, z=-0.0025 m, global stress component 1 | 4.517(10^6) (p. 7) | 4516687.353790105 | 4516687.353790105 | -0.006921545492465785 % |
| ply 1, z=-0.0025 m, global stress component 2 | −1.151(10^7) (p. 7) | -11507452.77765279 | -11507452.77765279 | 0.02213051561432867 % |
| ply 1, z=-0.0025 m, global stress component 3 | 5.595(10^5) (p. 7) | 559511.4925916367 | 559511.4925916363 | 0.002054082508714099 % |
| ply 2, z=-0.0025 m, global stress component 1 | −4.466(10^6) (p. 7) | -4466203.9852385605 | -4466203.985238559 | -0.004567515417792494 % |
| ply 2, z=-0.0025 m, global stress component 2 | −2.035(10^7) (p. 7) | -20354759.157260153 | -20354759.15726016 | -0.023386522162952793 % |
| ply 2, z=-0.0025 m, global stress component 3 | 8.022(10^6) (p. 7) | 8022179.788370269 | 8022179.78837027 | 0.002241191352160085 % |
| ply 2, z=0.0 m, global stress component 1 | −4.119(10^6) (p. 7) | -4119195.437884404 | -4119195.4378844043 | -0.004744789618944501 % |
| ply 2, z=0.0 m, global stress component 2 | −8.388(10^6) (p. 7) | -8388445.488676872 | -8388445.488676877 | -0.005311023806351466 % |
| ply 2, z=0.0 m, global stress component 3 | 6.768(10^6) (p. 7) | 6768436.706919616 | 6768436.706919619 | 0.006452525408080411 % |
| ply 2, z=0.0025 m, global stress component 1 | −3.772(10^6) (p. 7) | -3772186.8905302477 | -3772186.89053025 | -0.004954680017233172 % |
| ply 2, z=0.0025 m, global stress component 2 | 3.578(10^6) (p. 7) | 3577868.17990641 | 3577868.1799064106 | -0.003684183722453024 % |
| ply 2, z=0.0025 m, global stress component 3 | 5.515(10^6) (p. 7) | 5514693.625468963 | 5514693.625468967 | -0.005555295213661811 % |
| ply 3, z=0.0025 m, global stress component 1 | −3.769(10^5) (p. 7) | -376916.3486773378 | -376916.3486773395 | -0.00433766976372989 % |
| ply 3, z=0.0025 m, global stress component 2 | 8.816(10^6) (p. 7) | 8815795.894821038 | 8815795.894821038 | -0.002315167637948393 % |
| ply 3, z=0.0025 m, global stress component 3 | 2.026(10^6) (p. 7) | 2025713.2735291251 | 2025713.273529126 | -0.014152343083597788 % |
| ply 3, z=0.005 m, global stress component 1 | 1.835(10^6) (p. 7) | 1835268.272526374 | 1835268.2725263732 | 0.014619756205621549 % |
| ply 3, z=0.005 m, global stress component 2 | 3.051(10^7) (p. 7) | 30505432.38747348 | 30505432.387473494 | -0.014970870293366717 % |
| ply 3, z=0.005 m, global stress component 3 | −3.190(10^6) (p. 7) | -3189936.5775749455 | -3189936.5775749455 | 0.001988163794811266 % |
| ply 3, z=0.0075 m, global stress component 1 | 4.047(10^6) (p. 7) | 4047452.893730079 | 4047452.893730083 | 0.01119085075570745 % |
| ply 3, z=0.0075 m, global stress component 2 | 5.220(10^7) (p. 7) | 52195068.8801259 | 52195068.88012592 | -0.009446589797092923 % |
| ply 3, z=0.0075 m, global stress component 3 | −8.406(10^6) (p. 7) | -8405586.428679006 | -8405586.42867901 | 0.004919953854271955 % |
| ply 1, z=-0.0075 m, local strain component 1 | −2.532(10^−4) (p. 8) | -0.00025321516154061226 | -0.0002532151615406124 | -0.005987970226064287 % |
| ply 1, z=-0.0075 m, local strain component 2 | −2.043(10^−3) (p. 8) | -0.0020433611063762607 | -0.002043361106376262 | -0.017675299865976674 % |
| ply 1, z=-0.0075 m, local strain component 3 | −4.423(10^−3) (p. 8) | -0.004422999695188189 | -0.00442299969518819 | 6.891517284046872e-06 % |
| ply 1, z=-0.005 m, local strain component 1 | −8.682(10^−5) (p. 8) | -8.682059367049553e-05 | -8.682059367049552e-05 | -0.0006837946273993158 % |
| ply 1, z=-0.005 m, local strain component 2 | −1.508(10^−3) (p. 8) | -0.001507859899389423 | -0.0015078598993894235 | 0.009290491417542875 % |
| ply 1, z=-0.005 m, local strain component 3 | −3.016(10^−3) (p. 8) | -0.0030157148799032506 | -0.0030157148799032515 | 0.009453584109700278 % |
| ply 1, z=-0.0025 m, local strain component 1 | 7.957(10^−5) (p. 8) | 7.95739741996215e-05 | 7.957397419962144e-05 | 0.004994595477488992 % |
| ply 1, z=-0.0025 m, local strain component 2 | −9.724(10^−4) (p. 8) | -0.0009723586924025847 | -0.0009723586924025852 | 0.004248004670390129 % |
| ply 1, z=-0.0025 m, local strain component 3 | −1.608(10^−3) (p. 8) | -0.0016084300646183117 | -0.0016084300646183125 | -0.026745312084109785 % |
| ply 2, z=-0.0025 m, local strain component 1 | −4.998(10^−4) (p. 8) | -0.0004997850491210119 | -0.000499785049121012 | 0.002991372346531699 % |
| ply 2, z=-0.0025 m, local strain component 2 | −3.930(10^−4) (p. 8) | -0.00039299966908195135 | -0.0003929996690819516 | 8.42030657477914e-05 % |
| ply 2, z=-0.0025 m, local strain component 3 | 1.919(10^−3) (p. 8) | 0.0019189076294712072 | 0.001918907629471208 | -0.004813472057948984 % |
| ply 2, z=0.0 m, local strain component 1 | −3.408(10^−4) (p. 8) | -0.00034083050242348154 | -0.00034083050242348164 | -0.008950241631941046 % |
| ply 2, z=0.0 m, local strain component 2 | 1.499(10^−4) (p. 8) | 0.00014994155907747323 | 0.00014994155907747313 | 0.02772453467185717 % |
| ply 2, z=0.0 m, local strain component 3 | 5.156(10^−4) (p. 8) | 0.0005156099095159989 | 0.0005156099095159993 | 0.0019219387120503475 % |
| ply 2, z=0.0025 m, local strain component 1 | −1.819(10^−4) (p. 8) | -0.00018187595572595114 | -0.0001818759557259512 | 0.013218402445743894 % |
| ply 2, z=0.0025 m, local strain component 2 | 6.929(10^−4) (p. 8) | 0.0006928827872368979 | 0.000692882787236898 | -0.00248416266446951 % |
| ply 2, z=0.0025 m, local strain component 3 | −8.877(10^−4) (p. 8) | -0.0008876878104392095 | -0.0008876878104392097 | 0.0013731621933448562 % |
| ply 3, z=0.0025 m, local strain component 1 | 9.864(10^−5) (p. 8) | 9.864372157109111e-05 | 9.864372157109107e-05 | 0.003772882290198577 % |
| ply 3, z=0.0025 m, local strain component 2 | 4.124(10^−4) (p. 8) | 0.0004123631099398557 | 0.00041236310993985573 | -0.008945213420044737 % |
| ply 3, z=0.0025 m, local strain component 3 | −1.206(10^−3) (p. 8) | -0.0012061395659515653 | -0.0012061395659515655 | -0.011572632799790358 % |
| ply 3, z=0.005 m, local strain component 1 | 6.341(10^−4) (p. 8) | 0.0006341449285579289 | 0.0006341449285579291 | 0.007085405760771006 % |
| ply 3, z=0.005 m, local strain component 2 | 5.788(10^−4) (p. 8) | 0.0005787576778099729 | 0.000578757677809973 | -0.0073120577102722415 % |
| ply 3, z=0.005 m, local strain component 3 | −2.613(10^−3) (p. 8) | -0.0026134243812365038 | -0.0026134243812365046 | -0.016241149502670325 % |
| ply 3, z=0.0075 m, local strain component 1 | 1.170(10^−3) (p. 8) | 0.001169646135544766 | 0.001169646135544767 | -0.030244825233599927 % |
| ply 3, z=0.0075 m, local strain component 2 | 7.452(10^−4) (p. 8) | 0.00074515224568009 | 0.0007451522456800902 | -0.006408255489773588 % |
| ply 3, z=0.0075 m, local strain component 3 | −4.021(10^−3) (p. 8) | -0.004020709196521441 | -0.004020709196521444 | 0.007232118342608063 % |

## Printed inconsistencies and precision

* p. 2: reciprocal relation gives ν21=0.05570466321243523. Printed 0.0557 is consistent with that precision; denominator substitutions print 0.0057. Using that erroneous substitution gives Q11=38657290103.93403 Pa, incompatible with printed 39.17*10^9 Pa. The final Q is consistent with the reciprocal relation, not that substitution.
* p. 4: the visible A expansion shows two terms and a trailing continuation clipped at the right edge. The complete three-ply A11 sum from printed Qbars is 273450000.0 N/m, agreeing with printed 2.735*10^8 N/m. A third term is required; the visible two-term expression alone does not equal the result. It cannot be established whether the clipped original was complete. B/D expansions have the same clipping.
* p. 7: multiplying the displayed tensor-strain T by the printed vector gives the third component 0.00095955. That is γ12/2. Doubling gives 0.0019191, consistent with printed 1.919*10^-3 and the γ12 header on p. 8. Conclusion: the p. 7 numerical result's third entry is engineering γ12 mislabelled as γ12/2. App γ12=0.001918907629471208; G12γ12=7944277.586010802 Pa agrees with p. 8 τ12. Changing the app convention would create a factor-of-two error.
* p. 9 uses rounded midpoint stresses before multiplying by thickness. Therefore printed integer forces and p. 10 percentages do not have independent integer/last-decimal precision. Tests use the propagated half-unit from 0.001 MPa midpoint precision: 0.0005 MPa times 0.005 m = 2.5 N/m. No parameter is tuned.
* All reported Q, Qbar, A/B/D, midplane solution, point strain/stress and through-thickness table entries agree within half a unit of their last printed digit. No literal half-unit exceptions were found for these quantities. Zero B12/B66 agree by absolute floating-point residual. Nx for plies 2 and 3 differs by more than half of the integer unit printed in part (e), but agrees within 2.5 N/m from the actual precision of the source midpoint stresses. Their literal integer digits are not an independent accuracy claim.

Literal half-unit exceptions (excluding ply-load propagated tolerances):

None for stiffness/strain/stress; per-ply loads use propagated source precision as explained above.

## Scope and rerun

This case checks linear mechanical stiffness assembly, extension–bending coupling, engineering-shear transforms, global/local stress recovery at known coordinates, and exact integrated ply-force equilibrium. It does not validate strength allowables, any failure criterion, progressive failure, pressure vessels or burst strength.

Run `python verification/verify_kaw_vessel.py` and `python -m unittest discover -s tests -q`. Focused tests cover printed ABD and per-ply Nx within source-digit tolerances, mixed-material equilibrium with membrane/moment/combined loading, and exact midpoint integration. Printed detailed strain/stress comparisons are reported above, not silently fitted or forced to pass.
