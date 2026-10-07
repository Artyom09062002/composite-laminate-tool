"""Thin-walled cylindrical pressure vessel: membrane resultants and netting theory.

Coordinates follow the rest of the app: x is the cylinder axis, y the hoop
direction, ply angles are measured from x (90 deg = hoop winding).

Thin-wall equilibrium of a closed cylinder of radius R under internal pressure p:
    Nx = p R / 2 (axial),  Ny = p R (hoop),  Nxy = 0.
Netting theory assumes the fibres carry all load and the matrix carries none.
For a +/-theta wind the fibres can balance Ny/Nx = 2 only when tan^2(theta) = 2,
i.e. theta = 54.74 deg.

Reference: e.g. Peters (ed.), "Composite Filament Winding", ASM International (2011);
any composites text treating netting analysis of filament-wound cylinders.
"""
from dataclasses import dataclass
import math

import numpy as np

from .failure import evaluate_failure, first_ply_limit
from .laminate import assemble_laminate_stiffness
from .response import recover_ply_surfaces

NETTING_ANGLE_DEG = math.degrees(math.atan(math.sqrt(2.0)))


@dataclass(frozen=True)
class FirstPly:
    """First-ply (CLT) failure of a wall under a unit load: pressure, location, criterion, mode."""
    pressure_pa: float
    ply: int
    surface: str
    criterion: str
    mode: str


def first_ply_under_unit_load(layup: list[dict], materials: list[dict], strengths, unit_loads: np.ndarray) -> FirstPly:
    """First-ply failure pressure of a wall whose unit-pressure resultants are ``unit_loads``.

    The CLT response is linear, so the first-ply load factor of the unit-pressure load case
    is the first-ply pressure in Pa. Shared by the cylinder (``cylinder_resultants(1, R)``) and
    the dome stations (``dome_resultants(1, r1, r2)``); ``strengths`` holds one StrengthAllowables
    per material, indexed like ``ply["mat"]``.
    """
    stiffness = assemble_laminate_stiffness(layup, materials)
    response = recover_ply_surfaces(stiffness, layup, materials, unit_loads)
    surface_strengths = [strengths[layup[p.ply - 1]["mat"]] for p in response.ply_surfaces]
    index, factor, criterion = first_ply_limit(response.ply_surfaces, surface_strengths)
    point = response.ply_surfaces[index]
    mode = evaluate_failure(point.local_stress, surface_strengths[index]).maximum_stress_mode
    return FirstPly(factor, point.ply, point.surface, criterion, mode)


def cylinder_resultants(pressure_pa: float, radius_m: float) -> np.ndarray:
    """Six-component load vector [Nx, Ny, Nxy, Mx, My, Mxy] for a closed thin cylinder."""
    if not (math.isfinite(radius_m) and radius_m > 0):
        raise ValueError("Radius must be positive and finite")
    return np.array([pressure_pa * radius_m / 2.0, pressure_pa * radius_m, 0.0, 0.0, 0.0, 0.0])


def netting_bound(layup: list[dict], fibre_strengths: list[float], radius_m: float) -> float:
    """Fibre-limit bound used for the winding-angle plot.

    Every ply k (thickness t_k, angle theta_k, fibre strength X_k) carries only
    fibre-direction stress, all at their strengths:
        p <= min(2 * sum(X_k t_k cos^2 theta_k), sum(X_k t_k sin^2 theta_k)) / R.
    For a single +/-theta wind this equals the netting burst pressure only at the
    netting angle; away from it the fibres alone cannot balance Nx and Ny, and the
    value is the pressure at which the more demanding direction reaches X (an upper bound).
    """
    axial = sum(x * ply["t"] * math.cos(math.radians(ply["theta"])) ** 2
                for ply, x in zip(layup, fibre_strengths))
    hoop = sum(x * ply["t"] * math.sin(math.radians(ply["theta"])) ** 2
               for ply, x in zip(layup, fibre_strengths))
    return min(2.0 * axial, hoop) / radius_m


def netting_pressure(layup: list[dict], fibre_strengths: list[float], radius_m: float) -> float:
    """Exact netting-theory burst pressure of a wall (fibres only, matrix carries nothing).

    Fibre stresses 0 <= s_k <= X_k must satisfy axial and hoop equilibrium:
        sum(s_k t_k cos^2) = pR/2  and  sum(s_k t_k sin^2) = pR.
    Eliminating p gives sum(s_k c_k) = 0 with c_k = t_k (3 cos^2 - 1), and
    pR = sum(s_k b_k) with b_k = t_k sin^2. This small linear programme is solved
    exactly: start with every ply at X_k and, if sum(X_k c_k) != 0, lower the plies on
    the over-supplied side in order of increasing b_k/|c_k| (least hoop capacity lost
    per unit of imbalance removed). Returns 0 when fibres alone cannot balance the
    loads (for example a single +/-theta wind away from 54.74 deg).
    """
    plies = []
    for ply, x in zip(layup, fibre_strengths):
        cos2 = math.cos(math.radians(ply["theta"])) ** 2
        plies.append({"x": float(x), "c": ply["t"] * (3.0 * cos2 - 1.0), "b": ply["t"] * (1.0 - cos2)})
    stress = [p["x"] for p in plies]
    scale = max(sum(abs(p["x"] * p["c"]) for p in plies), 1e-300)
    imbalance = sum(s * p["c"] for s, p in zip(stress, plies))
    if abs(imbalance) > 1e-12 * scale:
        sign = 1.0 if imbalance > 0 else -1.0
        donors = sorted((i for i, p in enumerate(plies) if sign * p["c"] > 0),
                        key=lambda i: plies[i]["b"] / abs(plies[i]["c"]))
        for i in donors:
            capacity = stress[i] * abs(plies[i]["c"])
            if capacity <= abs(imbalance) + 1e-12 * scale:
                stress[i] = 0.0
                imbalance -= sign * capacity
            else:
                stress[i] -= abs(imbalance) / abs(plies[i]["c"])
                imbalance = 0.0
            if abs(imbalance) <= 1e-12 * scale:
                break
        if abs(imbalance) > 1e-9 * scale:
            return 0.0
    return sum(s * p["b"] for s, p in zip(stress, plies)) / radius_m
