# Section 4.3 worked example: source transcription

Source: `C:\Users\artyo\Downloads\Section4_3_worked_out_example_PPT.pdf` (10 PDF pages). This is a literal transcription of printed inputs and results; no values have been recalculated. Scientific notation follows the source's printed mantissa and exponent. PDF page numbers below refer to the 1-based page index.

## Problem and lamina inputs (PDF p. 1-3)

- Laminate: `[30/−45/−60]` glass/epoxy; three plies.
- Applied loads: `Nx = 1500 N/m`, `My = 1500 N` (other load components shown later as zero).
- Each lamina thickness: `5 mm`.
- `E1 = 38.6 GPa`; `E2 = 8.27 GPa`; `v12 = 0.26`; `G12 = 4.14 GPa`.
- Reciprocal relation: `v12/E1 = v21/E2`.
- Printed minor Poisson ratio result: `v21 = 0.0557` (p. 2). In the immediately following printed Q calculations, the denominator instead shows `(0.0057)(0.26)`; preserved as printed below.
- Printed Q calculations (p. 2): `Q11 = 38.6 × 10^9 / [1 − (0.0057)(0.26)] = 39.17 × 10^9 Pa`; `Q12 = (0.26)(8.27 × 10^9) / [1 − (0.0057)(0.26)] = 2.182 × 10^9 Pa`; `Q22 = 8.27 × 10^9 / [1 − (0.0057)(0.26)] = 8.392 × 10^9 Pa`; `Q66 = G12 = 4.14 × 10^9 Pa`.

Reduced stiffness matrix `[Q]` (entries are multiplied by `10^9 Pa`, p. 2):

```text
[ 39.17   2.182   0    ]
[  2.182  8.392   0    ]
[  0      0       4.14 ]
```

Transformed stiffness matrices `[Q̄]` (entries are multiplied by `10^9 Pa`):

- `30°` (p. 2):

```text
[ 26.48   7.176   9.546 ]
[  7.176 11.09    3.780 ]
[  9.546  3.780   9.134 ]
```

- `−45°` (p. 2):

```text
[ 17.12    8.841  −7.694 ]
[  8.841  17.12   −7.694 ]
[ −7.694  −7.694  10.80  ]
```

- `−60°` (p. 3):

```text
[ 11.09    7.176  −3.780 ]
[  7.176  26.48   −9.546 ]
[ −3.780  −9.546   9.134 ]
```

Geometry and coordinates (p. 3): `h = n × t = (3)(0.005) = 0.015 m`; `h0 = −h/2 = −0.015/2 = −0.0075 m`; `h1 = h0 + t = −0.0075 + 0.005 = −0.0025 m`; `h2 = h0 + 2t = −0.0075 + 2(0.005) = 0.0025 m`; `h3 = h/2 = 0.015/2 = 0.0075 m`.

## Laminate matrices (PDF p. 4-5)

The printed definitions are `Aij = Σ(k=1..3) [Q̄ij]k (hk − hk−1)`, `Bij = (1/2) Σ(k=1..3) [Q̄ij]k (hk² − hk−1²)`, and `Dij = (1/3) Σ(k=1..3) [Q̄ij]k (hk³ − hk−1³)` (PDF p. 4). The source gives the laminate stiffness matrices with units as shown. Rows and columns use the usual displayed 1, 2, 6 ordering.

`[A]` (p. 4, `Pa − m`):

```text
[  2.735 × 10^8   1.160 × 10^8  −9.636 × 10^6 ]
[  1.160 × 10^8   2.735 × 10^8  −6.730 × 10^7 ]
[ −9.636 × 10^6  −6.730 × 10^7   1.453 × 10^8 ]
```

`[B]` (p. 4, `Pa − m^2`):

```text
[ −3.847 × 10^5   0              −3.332 × 10^5 ]
[  0               3.847 × 10^5  −3.332 × 10^5 ]
[ −3.332 × 10^5  −3.332 × 10^5   0             ]
```

`[D]` (p. 4, `Pa − m^3`):

```text
[ 5.266 × 10^3   2.036 × 10^3   7.008 × 10^2 ]
[ 2.036 × 10^3   5.266 × 10^3  −8.611 × 10^2 ]
[ 7.008 × 10^2  −8.611 × 10^2   2.586 × 10^3 ]
```

The printed expanded matrix arithmetic on p. 4 is cut off at the right page edge in the terms for later plies (for example, the B and D terms end after `−(−0.`). Those clipped expressions are **NOT REPORTED / unreadable** here; the final matrices above are legible. The full block stiffness equation on p. 5 orders the loads as `[Nx, Ny, Nxy, Mx, My, Mxy]` and the unknowns as `[εx⁰, εy⁰, γxy⁰, κx, κy, κxy]`.

## Mid-plane solution and point values (PDF p. 5-6)

Applied load vector printed on p. 5:

```text
[Nx, Ny, Nxy, Mx, My, Mxy]ᵀ = [1500, 0, 0, 0, 1500, 0]ᵀ
```

Printed 6×6 ABD matrix on p. 5 (units inherited from the A, B, D blocks above):

```text
[  2.735 × 10^8   1.160 × 10^8  −9.636 × 10^6  −3.847 × 10^5   0              −3.332 × 10^5 ]
[  1.160 × 10^8   2.735 × 10^8  −6.730 × 10^7   0               3.847 × 10^5  −3.332 × 10^5 ]
[ −9.636 × 10^6  −6.730 × 10^7   1.453 × 10^8  −3.332 × 10^5  −3.332 × 10^5   0             ]
[ −3.847 × 10^5   0              −3.332 × 10^5   5.266 × 10^3   2.036 × 10^3   7.008 × 10^2 ]
[  0               3.847 × 10^5  −3.332 × 10^5   2.036 × 10^3   5.266 × 10^3  −8.611 × 10^2 ]
[ −3.332 × 10^5  −3.332 × 10^5   0               7.008 × 10^2  −8.611 × 10^2   2.586 × 10^3 ]
```

Printed solution vector on p. 5:

```text
[εx⁰, εy⁰, γxy⁰, κx, κy, κxy]ᵀ
= [1.624 × 10^−4, −3.532 × 10^−4, 4.908 × 10^−4,
   −1.403 × 10^−1, 4.210 × 10^−1, 1.536 × 10^−1]ᵀ
```

For the top surface of the `−45°` ply, the source prints `z = h1 = −0.0025 m` and global strain vector (p. 5):

```text
[εx, εy, γxy]ᵀ = [5.131 × 10^−4, −1.406 × 10^−3, 1.068 × 10^−4]ᵀ
```

Top/middle/bottom global strain table (PDF p. 6; table headed `Ply #`, `Position`, `εx`, `εy`, `γxy`):

| Ply | Angle | Position | εx | εy | γxy |
|---:|:---:|:---|---:|---:|---:|
| 1 | 30° | Top | `1.214(10^−3)` | `−3.511(10^−3)` | `−6.612(10^−4)` |
| 1 | 30° | Middle | `8.638(10^−4)` | `−2.458(10^−3)` | `−2.772(10^−4)` |
| 1 | 30° | Bottom | `5.131(10^−4)` | `−1.406(10^−3)` | `1.068(10^−4)` |
| 2 | −45° | Top | `5.131(10^−4)` | `−1.406(10^−3)` | `1.068(10^−4)` |
| 2 | −45° | Middle | `1.624(10^−4)` | `−3.532(10^−4)` | `4.908(10^−4)` |
| 2 | −45° | Bottom | `−1.883(10^−4)` | `6.993(10^−4)` | `8.748(10^−4)` |
| 3 | −60° | Top | `−1.883(10^−4)` | `6.993(10^−4)` | `8.748(10^−4)` |
| 3 | −60° | Middle | `−5.390(10^−4)` | `1.752(10^−3)` | `1.259(10^−3)` |
| 3 | −60° | Bottom | `−8.897(10^−4)` | `2.805(10^−3)` | `1.643(10^−3)` |

The source defines the global strain relation as `[εx, εy, γxy]ᵀ = [εx⁰, εy⁰, γxy⁰]ᵀ + z[κx, κy, κxy]ᵀ` (p. 5).

## Global stress solution and table (PDF p. 6-7)

The source prints the global stress relation using `[Q̄]` (p. 6). At the top surface of the `−45°` ply it prints the matrix (entries multiplied by `10^9`) and strain vector shown above, yielding:

```text
[σx, σy, τxy]ᵀ = [−4.466 × 10^6, −2.035 × 10^7, 8.022 × 10^6]ᵀ Pa
```

Top/middle/bottom global stress table (PDF p. 7; table headed `Ply #`, `Position`, `σx`, `σy`, `τxy`):

| Ply | Angle | Position | σx | σy | τxy |
|---:|:---:|:---|---:|---:|---:|
| 1 | 30° | Top | `6.512(10^5)` | `−3.273(10^7)` | `−7.717(10^6)` |
| 1 | 30° | Middle | `2.584(10^6)` | `−2.212(10^7)` | `−3.579(10^6)` |
| 1 | 30° | Bottom | `4.517(10^6)` | `−1.151(10^7)` | `5.595(10^5)` |
| 2 | −45° | Top | `−4.466(10^6)` | `−2.035(10^7)` | `8.022(10^6)` |
| 2 | −45° | Middle | `−4.119(10^6)` | `−8.388(10^6)` | `6.768(10^6)` |
| 2 | −45° | Bottom | `−3.772(10^6)` | `3.578(10^6)` | `5.515(10^6)` |
| 3 | −60° | Top | `−3.769(10^5)` | `8.816(10^6)` | `2.026(10^6)` |
| 3 | −60° | Middle | `1.835(10^6)` | `3.051(10^7)` | `−3.190(10^6)` |
| 3 | −60° | Bottom | `4.047(10^6)` | `5.220(10^7)` | `−8.406(10^6)` |

## Local strain transform and table (PDF p. 7-8)

The transformation matrix is printed (p. 7) as

```text
[ c²    s²     2sc ]
[ s²    c²    −2sc ]
[−sc     sc   c²−s²]
```

with `s = sin(−45°)` and `c = cos(−45°)`. The strain transform uses `[ε1, ε2, γ12/2]ᵀ = [T][εx, εy, γxy/2]ᵀ`. For the top surface of ply `−45°`, the printed output is `[ε1, ε2, γ12/2]ᵀ = [−4.998 × 10^−4, −3.930 × 10^−4, 1.919 × 10^−3]ᵀ` (p. 7).

Top/middle/bottom local strain table (PDF p. 8; headed `Ply #`, `Position`, `ε1`, `ε2`, `γ12`):

| Ply | Angle | Position | ε1 | ε2 | γ12 |
|---:|:---:|:---|---:|---:|---:|
| 1 | 30° | Top | `−2.532(10^−4)` | `−2.043(10^−3)` | `−4.423(10^−3)` |
| 1 | 30° | Middle | `−8.682(10^−5)` | `−1.508(10^−3)` | `−3.016(10^−3)` |
| 1 | 30° | Bottom | `7.957(10^−5)` | `−9.724(10^−4)` | `−1.608(10^−3)` |
| 2 | −45° | Top | `−4.998(10^−4)` | `−3.930(10^−4)` | `1.919(10^−3)` |
| 2 | −45° | Middle | `−3.408(10^−4)` | `1.499(10^−4)` | `5.156(10^−4)` |
| 2 | −45° | Bottom | `−1.819(10^−4)` | `6.929(10^−4)` | `−8.877(10^−4)` |
| 3 | −60° | Top | `9.864(10^−5)` | `4.124(10^−4)` | `−1.206(10^−3)` |
| 3 | −60° | Middle | `6.341(10^−4)` | `5.788(10^−4)` | `−2.613(10^−3)` |
| 3 | −60° | Bottom | `1.170(10^−3)` | `7.452(10^−4)` | `−4.021(10^−3)` |

## Local stress transform and point result (PDF p. 8)

The source prints `[σ1, σ2, τ12]ᵀ = [T][σx, σy, τxy]ᵀ` using the same displayed `[T]` matrix above. For the top surface of the `−45°` ply it prints:

```text
[σ1, σ2, τ12]ᵀ = [−2.043 × 10^7, −4.388 × 10^6, 7.944 × 10^6]ᵀ
```

The table introduced at the end of p. 8 appears as an embedded image at the top of PDF p. 9. It was missed in the initial text-only extraction of that page and was subsequently read visually during presentation preparation.

Top/middle/bottom local stress table (PDF p. 9; stresses in Pa):

| Ply | Angle | Position | σ1 | σ2 | τ12 |
|---:|:---:|:---|---:|---:|---:|
| 1 | 30° | Top | `−1.438(10^7)` | `−1.770(10^7)` | `−1.831(10^7)` |
| 1 | 30° | Middle | `−6.690(10^6)` | `−1.284(10^7)` | `−1.249(10^7)` |
| 1 | 30° | Bottom | `9.952(10^5)` | `−7.986(10^6)` | `−6.659(10^6)` |
| 2 | −45° | Top | `−2.043(10^7)` | `−4.388(10^6)` | `7.944(10^6)` |
| 2 | −45° | Middle | `−1.302(10^7)` | `5.146(10^5)` | `2.135(10^6)` |
| 2 | −45° | Bottom | `−5.612(10^6)` | `5.418(10^6)` | `−3.675(10^6)` |
| 3 | −60° | Top | `4.763(10^6)` | `3.676(10^6)` | `−4.993(10^6)` |
| 3 | −60° | Middle | `2.610(10^7)` | `6.240(10^6)` | `−1.082(10^7)` |
| 3 | −60° | Bottom | `4.744(10^7)` | `8.805(10^6)` | `−1.665(10^7)` |

## Load carried by each ply (PDF p. 9-10)

The source defines `Nₓᵏ = (σx^mid)k × t` (p. 9), with `k` the ply number. Printed calculations:

- `30°` ply: `(2.584 × 10^6) × (5 × 10^−3) = 12920 N/m`.
- `−45°` ply: `(−4.119 × 10^6) × (5 × 10^−3) = −20595 N/m`.
- `−60°` ply: `(1.835 × 10^6) × (5 × 10^−3) = 9175 N/m`.
- Printed sum: `Nx = Nₓ¹ + Nₓ² + Nₓ³ = 12920 + (−20595) + 9175 = 1500 N/m`.

The printed percentage formula is `Nₓᵏ% = Nₓᵏ/Nx × 100%` (p. 10). Printed results:

- `30°` ply: `12920/1500 × 100 = 861.33%`.
- `−45°` ply: `−20595/1500 × 100 = −1373%`.
- `−60°` ply: `9175/1500 × 100 = 611.67%`.

## Readability notes

- Pages 5-8 were rendered and visually inspected. The tables above were transcribed from their rendered images.
- The p. 4 expanded A/B/D arithmetic is horizontally clipped at the right edge, as described above; final A/B/D matrix values are readable.
- Correction after visual inspection of p. 9: the local stress table is present there as an image; the initial assertion that it was absent was incorrect. Doc2 image11.png reproduces the same table.
