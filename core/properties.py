"""Equivalent engineering constants of a laminate from its ABD matrix.

The constants describe the laminate as a homogeneous plate of thickness h that
is free to bend (they use the compliance ``ABD^-1``, so extension-bending
coupling of unsymmetric stacks is included). For symmetric laminates the
membrane block reduces to ``A^-1``.

Reference: A. K. Kaw, "Mechanics of Composite Materials", 2nd ed., CRC Press (2006),
Section 4.4 (in-plane and flexural moduli of a laminate). Using ABD^-1 rather than
A^-1 and D^-1 for unsymmetric stacks is this app's choice (apparent constants with
curvature free to develop).
"""
from dataclasses import dataclass

import numpy as np

from .laminate import LaminateStiffness


@dataclass(frozen=True)
class EngineeringConstants:
    """In-plane (membrane) and flexural constants in Pa; Poisson ratios are dimensionless."""
    Ex: float
    Ey: float
    Gxy: float
    nu_xy: float
    nu_yx: float
    Ex_flex: float
    Ey_flex: float


def engineering_constants(stiffness: LaminateStiffness) -> EngineeringConstants:
    h = float(stiffness.z[-1] - stiffness.z[0])
    compliance = np.linalg.inv(stiffness.ABD)
    a = compliance[:3, :3]
    d = compliance[3:, 3:]
    return EngineeringConstants(
        Ex=1.0 / (h * a[0, 0]),
        Ey=1.0 / (h * a[1, 1]),
        Gxy=1.0 / (h * a[2, 2]),
        nu_xy=-a[0, 1] / a[0, 0],
        nu_yx=-a[0, 1] / a[1, 1],
        Ex_flex=12.0 / (h**3 * d[0, 0]),
        Ey_flex=12.0 / (h**3 * d[1, 1]),
    )
