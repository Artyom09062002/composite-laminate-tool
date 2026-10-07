"""Maximum Stress, Tsai-Wu and Hashin ply failure checks.

Strengths must be supplied as positive magnitudes in Pa. The Tsai-Wu F12 term
uses the Tsai-Hahn assumption F12 = -0.5*sqrt(F11*F22) when no measured interaction term
is available.

Hashin (2D, plane stress, local axes; sigma1 along the fibres)
--------------------------------------------------------------
This is a plane-stress, Hashin-1980-inspired INITIATION criterion, not the complete 3D criterion: Hashin (1980) is posed in 3D,
and the 2D form drops sigma3, tau13 and tau23, so interlaminar failure is not assessed and the result is an initiation index on
nominal ply stresses, not a mechanism or a failure path. A result should be quoted with the parameters used: Xt, Xc, Yt, Yc,
S12 (``S``), the transverse shear strength S23 (``St``) and the shear factor alpha.

Four modes, each a quadratic failure index that equals 1 at failure (it is NOT a linear utilisation:
a stress at half the strength gives 0.25). Only the mode matching the sign of the normal stress is active.

    fibre tension      sigma1 >= 0:  FT = (sigma1/Xt)^2 + alpha (tau12/S)^2
    fibre compression  sigma1 <  0:  FC = (sigma1/Xc)^2
    matrix tension     sigma2 >= 0:  MT = (sigma2/Yt)^2 + (tau12/S)^2
    matrix compression sigma2 <  0:  MC = (sigma2/(2 St))^2 + [(Yc/(2 St))^2 - 1] sigma2/Yc + (tau12/S)^2

Shear contribution used: alpha = 1 in fibre tension (the Hashin 1980 form), no shear term in fibre compression (the original
has none), and the full (tau12/S)^2 in both matrix modes. alpha = 1 is a chosen model setting, not a universal material law:
how much longitudinal shear lowers the fibre-rupture strength should be validated with combined sigma1-tau12 tests, and
alpha = 0 (the Hashin-Rotem-type form, no shear in the fibre mode) is equally admissible. The restriction alpha in [0, 1] is a
programming choice, not part of the criterion. tau12 enters squared, so its sign never matters.

St is the transverse (out-of-plane) shear strength S23, an independent property that the five in-plane allowables do not
contain. It is the optional ``StrengthAllowables.St``. When it is absent the code uses St = Yc / (2 tan 53 deg), which is the
Mohr-Coulomb cohesion consistent with a transverse-compression fracture angle of 53 deg (Yc = 2 St tan(theta_fp)); the angle is a
typical value, not a measurement of the material, so this St is an ASSUMPTION, not material data. The check MC = 1 at
sigma2 = -Yc holds for ANY positive St and therefore does not validate it. For the T300/5208 reference data the default
(92.7 MPa) even exceeds S12 = 68 MPa. Supply a measured S23, or report the result as a sensitivity study over St;
``transverse_shear_strength_is_assumed`` tells which case applies. The active mode is the one with the largest index; a tie
(for example pure in-plane shear, where FT = MT for alpha = 1) is resolved in favour of the matrix mode.

Because the indices are quadratic or quadratic-plus-linear in the stress, the proportional load factor (strength ratio)
is obtained by solving index(lambda sigma) = 1 for lambda, never by dividing by the index. In pure fibre tension
(sigma1 = Xt) FT = 1 and the strength ratio equals the Maximum Stress ratio.

References: Hashin & Rotem, J. Compos. Mater. 7 (1973) 448-464; Hashin, J. Appl. Mech. 47 (1980) 329-334;
Puck & Schurmann, Compos. Sci. Technol. 58 (1998) 1045-1067 (fracture angle).
"""
from dataclasses import dataclass
import math
import numpy as np

@dataclass(frozen=True)
class StrengthAllowables:
    """Ply strengths [Pa]; ``St`` is the optional transverse shear strength used only by the Hashin matrix-compression mode."""
    Xt: float; Xc: float; Yt: float; Yc: float; S: float
    St: float | None = None

    def __post_init__(self) -> None:
        values = np.array([self.Xt, self.Xc, self.Yt, self.Yc, self.S], dtype=float)
        if not np.all(np.isfinite(values)) or np.any(values <= 0):
            raise ValueError("All five strengths must be finite, positive values in Pa")
        if self.St is not None and not (math.isfinite(self.St) and self.St > 0):
            raise ValueError("The transverse shear strength St must be finite and positive when given")

@dataclass(frozen=True)
class FailureResult:
    maximum_stress_utilization: float
    maximum_stress_mode: str
    tsai_wu_index: float
    hashin_index: float = 0.0           # quadratic index of the active Hashin mode (1 = failure)
    hashin_mode: str = "No load"        # one of HASHIN_MODES, or "No load"

def maximum_stress(stress: np.ndarray, strengths: StrengthAllowables) -> tuple[float, str]:
    s1, s2, t12 = _stress_vector(stress)
    candidates = [(abs(s1) / (strengths.Xt if s1 >= 0 else strengths.Xc), "Fibre tension" if s1 >= 0 else "Fibre compression"),
                  (abs(s2) / (strengths.Yt if s2 >= 0 else strengths.Yc), "Transverse tension" if s2 >= 0 else "Transverse compression"),
                  (abs(t12) / strengths.S, "In-plane shear")]
    return max(candidates, key=lambda item: item[0])

def _tsai_wu_terms(values: np.ndarray, strengths: StrengthAllowables) -> tuple[float, float]:
    """Return the quadratic part a and linear part b, so FI = a + b for this stress state."""
    s1, s2, t12 = values
    f1 = 1 / strengths.Xt - 1 / strengths.Xc
    f2 = 1 / strengths.Yt - 1 / strengths.Yc
    f11 = 1 / (strengths.Xt * strengths.Xc)
    f22 = 1 / (strengths.Yt * strengths.Yc)
    f66 = 1 / strengths.S**2
    f12 = -0.5 * math.sqrt(f11 * f22)  # Tsai-Hahn assumption, not measured interaction data
    a = f11*s1**2 + f22*s2**2 + f66*t12**2 + 2*f12*s1*s2
    b = f1*s1 + f2*s2
    return float(a), float(b)

def tsai_wu(stress: np.ndarray, strengths: StrengthAllowables) -> float:
    a, b = _tsai_wu_terms(_stress_vector(stress), strengths)
    return a + b

def evaluate_failure(stress: np.ndarray, strengths: StrengthAllowables) -> FailureResult:
    utilization, mode = maximum_stress(stress, strengths)
    hashin_result = hashin(stress, strengths)
    return FailureResult(utilization, mode, tsai_wu(stress, strengths), hashin_result.index, hashin_result.mode)

def tsai_wu_load_factor(stress: np.ndarray, strengths: StrengthAllowables) -> float:
    """Strength ratio R: the proportional load multiplier at which the Tsai-Wu index reaches 1.

    Solves a R^2 + b R = 1. The quadratic part a is computed directly (not by
    differencing), so tiny round-off stresses at the mid-plane cannot make it negative.
    """
    values = _stress_vector(stress)
    if not np.any(values):
        return math.inf
    a, b = _tsai_wu_terms(values, strengths)
    if a <= 0:
        return 1 / b if b > 0 else math.inf
    discriminant = math.sqrt(b * b + 4 * a)
    return 2 / (discriminant + b) if b >= 0 else (-b + discriminant) / (2 * a)

def _stress_vector(stress: np.ndarray) -> np.ndarray:
    values = np.asarray(stress, dtype=float)
    if values.shape != (3,) or not np.all(np.isfinite(values)):
        raise ValueError("Stress must be three finite values [sigma1, sigma2, tau12] in Pa")
    return values


# --------------------------------------------------------------------------------------------------------------
# Hashin (2D)
# --------------------------------------------------------------------------------------------------------------
HASHIN_MODES = ("Fibre tension", "Fibre compression", "Matrix tension", "Matrix compression")
HASHIN_FRACTURE_ANGLE_DEG = 53.0   # Mohr-Coulomb fracture angle behind the default transverse shear strength (assumption)
_TIE_ORDER = ("Matrix tension", "Matrix compression", "Fibre tension", "Fibre compression")   # matrix wins a tie


def transverse_shear_strength_is_assumed(strengths: StrengthAllowables) -> bool:
    """True when no S23 was supplied, so Hashin matrix compression uses the assumed Yc / (2 tan 53 deg)."""
    return strengths.St is None


def hashin_fibre_tension_is_shear_dominated(stress: np.ndarray, strengths: StrengthAllowables,
                                            shear_factor: float = 1.0) -> bool:
    """True when the fibre-tension index is driven more by its shear term than by sigma1: (sigma1/Xt)^2 < alpha (tau12/S)^2.

    Used by the progressive model to avoid applying fibre-rupture damage where the fibres carry no significant stress
    (pure shear with alpha = 1). It does not change the Hashin index or its load factor.
    """
    s1, _, t12 = _stress_vector(stress)
    return bool(s1 >= 0.0 and (s1 / strengths.Xt) ** 2 < shear_factor * (t12 / strengths.S) ** 2)


def hashin_transverse_shear_strength(strengths: StrengthAllowables) -> float:
    """St used by the matrix-compression mode: the given ``St``, else Yc / (2 tan 53 deg) [Pa] (an assumption)."""
    if strengths.St is not None:
        return float(strengths.St)
    return strengths.Yc / (2.0 * math.tan(math.radians(HASHIN_FRACTURE_ANGLE_DEG)))


@dataclass(frozen=True)
class HashinResult:
    """Hashin failure indices (1 = failure; inactive tension/compression partners are 0), active mode, strength ratio."""
    fibre_tension: float
    fibre_compression: float
    matrix_tension: float
    matrix_compression: float
    index: float          # largest of the four
    mode: str             # its name, or "No load"
    load_factor: float    # proportional multiplier at which the first mode reaches 1 (inf when unloaded)

    @property
    def indices(self) -> dict[str, float]:
        return dict(zip(HASHIN_MODES, (self.fibre_tension, self.fibre_compression,
                                       self.matrix_tension, self.matrix_compression)))


def _hashin_indices(values: np.ndarray, strengths: StrengthAllowables, shear_factor: float) -> dict[str, float]:
    s1, s2, t12 = values
    st = hashin_transverse_shear_strength(strengths)
    shear = (t12 / strengths.S) ** 2
    result = dict.fromkeys(HASHIN_MODES, 0.0)
    if s1 >= 0:
        result["Fibre tension"] = (s1 / strengths.Xt) ** 2 + shear_factor * shear
    else:
        result["Fibre compression"] = (s1 / strengths.Xc) ** 2
    if s2 >= 0:
        result["Matrix tension"] = (s2 / strengths.Yt) ** 2 + shear
    else:
        result["Matrix compression"] = ((s2 / (2.0 * st)) ** 2
                                        + ((strengths.Yc / (2.0 * st)) ** 2 - 1.0) * s2 / strengths.Yc + shear)
    return result


def hashin_load_factors(stress: np.ndarray, strengths: StrengthAllowables, shear_factor: float = 1.0) -> dict[str, float]:
    """Per-mode strength ratio: the multiplier lambda on this stress state at which each active mode reaches 1.

    Solves index(lambda * sigma) = 1: a lambda^2 = 1 for the three modes without a linear term, and
    A lambda^2 + B lambda = 1 for matrix compression. Inactive modes (wrong stress sign) and unloaded modes give inf.
    """
    values = _stress_vector(stress)
    _check_shear_factor(shear_factor)
    s1, s2, t12 = values
    st = hashin_transverse_shear_strength(strengths)
    shear = (t12 / strengths.S) ** 2
    ratios = dict.fromkeys(HASHIN_MODES, math.inf)

    def quadratic(a: float) -> float:
        return 1.0 / math.sqrt(a) if a > 0 else math.inf

    if s1 >= 0:
        ratios["Fibre tension"] = quadratic((s1 / strengths.Xt) ** 2 + shear_factor * shear)
    else:
        ratios["Fibre compression"] = quadratic((s1 / strengths.Xc) ** 2)
    if s2 >= 0:
        ratios["Matrix tension"] = quadratic((s2 / strengths.Yt) ** 2 + shear)
    else:
        a = (s2 / (2.0 * st)) ** 2 + shear
        b = ((strengths.Yc / (2.0 * st)) ** 2 - 1.0) * s2 / strengths.Yc
        if a > 0:
            ratios["Matrix compression"] = (-b + math.sqrt(b * b + 4.0 * a)) / (2.0 * a)
    return ratios


def _check_shear_factor(shear_factor: float) -> None:
    if not (math.isfinite(shear_factor) and 0.0 <= shear_factor <= 1.0):
        raise ValueError("The fibre-tension shear factor alpha must lie in [0, 1] (a software restriction, not part of the criterion)")


def hashin(stress: np.ndarray, strengths: StrengthAllowables, shear_factor: float = 1.0) -> HashinResult:
    """2D Hashin failure indices and the active mode for the local stress ``[sigma1, sigma2, tau12]`` [Pa].

    ``shear_factor`` is alpha in the fibre-tension mode (1 = Hashin 1980, 0 = Hashin-Rotem). The formulas and the
    shear contribution are documented in the module docstring.
    """
    values = _stress_vector(stress)
    _check_shear_factor(shear_factor)
    indices = _hashin_indices(values, strengths, shear_factor)
    top = max(indices.values())
    if top <= 0.0:
        return HashinResult(0.0, 0.0, 0.0, 0.0, 0.0, "No load", math.inf)
    mode = next(name for name in _TIE_ORDER if indices[name] >= top * (1.0 - 1e-12))
    load_factor = min(hashin_load_factors(values, strengths, shear_factor).values())
    return HashinResult(indices["Fibre tension"], indices["Fibre compression"], indices["Matrix tension"],
                        indices["Matrix compression"], top, mode, load_factor)


def first_ply_limit(surfaces, strengths):
    """Return ``(index, load_factor, criterion)`` of the first ply surface to reach a limit.

    ``load_factor`` is the proportional multiplier on the entered load vector at which
    Maximum Stress or Tsai-Wu first reaches 1 (``math.inf`` when nothing is loaded).
    ``index`` is the position in ``surfaces``; criterion is "No load" when unbounded.
    ``strengths`` is one StrengthAllowables for all surfaces, or a list with one per surface
    (hybrid laminates, where each ply's material has its own allowables).

    Moved here from ``workflow`` unchanged so that ``core.vessel`` and ``core.dome`` can use it
    without importing the UI-side module; ``workflow.first_ply_limit`` still resolves to this function.
    """
    per_surface = (list(strengths) if isinstance(strengths, (list, tuple))
                   else [strengths] * len(surfaces))
    thresholds = []
    for point, allow in zip(surfaces, per_surface):
        util = evaluate_failure(point.local_stress, allow).maximum_stress_utilization
        thresholds.append((1 / util if util else math.inf,
                           tsai_wu_load_factor(point.local_stress, allow)))
    index = min(range(len(thresholds)), key=lambda i: min(thresholds[i]))
    factor = min(thresholds[index])
    if not math.isfinite(factor):
        return index, factor, "No load"
    return index, factor, ("Maximum Stress" if thresholds[index][0] <= thresholds[index][1] else "Tsai–Wu")
