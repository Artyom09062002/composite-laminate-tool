"""Maximum Stress and Tsai-Wu first-ply failure checks.

Strengths must be supplied as positive magnitudes in Pa. The Tsai-Wu F12 term
uses the Tsai-Hahn assumption F12 = -0.5*sqrt(F11*F22) when no measured interaction term
is available.
"""
from dataclasses import dataclass
import math
import numpy as np

@dataclass(frozen=True)
class StrengthAllowables:
    Xt: float; Xc: float; Yt: float; Yc: float; S: float

    def __post_init__(self) -> None:
        values = np.array([self.Xt, self.Xc, self.Yt, self.Yc, self.S], dtype=float)
        if not np.all(np.isfinite(values)) or np.any(values <= 0):
            raise ValueError("All five strengths must be finite, positive values in Pa")

@dataclass(frozen=True)
class FailureResult:
    maximum_stress_utilization: float
    maximum_stress_mode: str
    tsai_wu_index: float

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
    return FailureResult(utilization, mode, tsai_wu(stress, strengths))

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
