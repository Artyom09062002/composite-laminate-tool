"""Thermal loads, free expansion and residual ply stresses for linear CLT.

The material thermal-expansion vector is ``[alpha1, alpha2, alpha12]`` in
the principal material axes, with engineering shear convention.  The built-in
material records set ``alpha12 = 0``.  For a uniform temperature change dT,

    {N_T, M_T} = sum integral(Qbar alpha_bar dT {1, z}) dz

and equilibrium under an optional mechanical load is

    ABD {epsilon0, kappa} = {N_mech, M_mech} + {N_T, M_T}.

Recovered ply stress is ``Q (epsilon_local_total - alpha_local dT)``. CTE shear
is d(gamma)/dT, twice the tensor shear CTE. A reference temperature must be an
assumed or calibrated effective stress-free temperature, not automatically the
nominal cure temperature. Independently calibrated monolithic references do
not establish the stress-free state of a co-cured hybrid.

Properties are constant with temperature and dT is constant within each ply
(a scalar or one value per material, not a through-thickness temperature
profile). Moisture, creep/relaxation, cure chemistry, chemical shrinkage,
damage evolution, fibre-matrix microstresses and interlaminar stresses are
outside this model. Linear Kirchhoff kinematics do not determine the stable
large-deflection shape of a strongly warped unsymmetric laminate. With zero
mechanical loads the laminate is free to extend, shear and curve; tool/end
restraints need prescribed strain/curvature and reaction equilibrium.
"""

from dataclasses import dataclass
import math
from numbers import Real

import numpy as np

from .failure import StrengthAllowables, evaluate_failure, tsai_wu
from .lamina import compute_Q_matrix
from .laminate import LaminateStiffness
from .response import LaminateResponse, PlySurfaceResponse
from .transformations import transform_stress_strain

__all__ = [
    "ThermalResultants",
    "compute_thermal_resultants",
    "first_ply_mechanical_load_factor",
    "recover_thermal_response",
    "temperature_change_from_reference",
    "transform_cte",
]


@dataclass(frozen=True)
class ThermalResultants:
    """Thermal membrane forces [N/m], moments [N], and combined vector."""

    N: np.ndarray
    M: np.ndarray
    vector: np.ndarray


def _finite(value: Real, name: str) -> float:
    if not isinstance(value, Real) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite")
    return float(value)


def _local_cte(material: dict, index: int) -> np.ndarray:
    missing = {"alpha1", "alpha2"} - material.keys()
    if missing:
        raise ValueError(f"material {index} is missing thermal keys: {sorted(missing)}")
    return np.array([
        _finite(material["alpha1"], f"material {index} alpha1"),
        _finite(material["alpha2"], f"material {index} alpha2"),
        _finite(material.get("alpha12", 0.0), f"material {index} alpha12"),
    ])


def transform_cte(alpha1: float, alpha2: float, theta_deg: float, alpha12: float = 0.0) -> np.ndarray:
    """Transform principal-axis CTEs to global ``[alpha_x, alpha_y, alpha_xy]`` [1/K].

    ``alpha_xy`` is an engineering shear CTE.  The angle convention is the
    established app convention: material 1 is counter-clockwise from global x.
    """

    local = np.array([
        _finite(alpha1, "alpha1"),
        _finite(alpha2, "alpha2"),
        _finite(alpha12, "alpha12"),
    ])
    angle = _finite(theta_deg, "theta_deg")
    return transform_stress_strain(local, -angle, "strain")


def temperature_change_from_reference(reference_temperature_c: float, final_temperature_c: float) -> float:
    """Return ``dT = T_final - T_reference``; kelvin and Celsius increments are identical."""

    return _finite(final_temperature_c, "final_temperature_c") - _finite(
        reference_temperature_c, "reference_temperature_c"
    )


def _temperature_changes(delta_temperature, materials: list) -> np.ndarray:
    if isinstance(delta_temperature, Real):
        return np.full(len(materials), _finite(delta_temperature, "delta_temperature"), dtype=float)
    values = np.asarray(delta_temperature, dtype=float)
    if values.shape != (len(materials),) or not np.all(np.isfinite(values)):
        raise ValueError("delta_temperature must be finite or contain one finite value per material")
    return values


def compute_thermal_resultants(
    stiffness: LaminateStiffness,
    layup: list,
    materials: list,
    delta_temperature,
) -> ThermalResultants:
    """Integrate equivalent ``N_T`` [N/m] and ``M_T`` [N], with constant dT per material.

    These are eigenstrain-induced equivalent loads, not external reactions.
    Actual external resultants equal ABD @ [epsilon0, kappa] - [N_T, M_T].
    """

    dT_by_material = _temperature_changes(delta_temperature, materials)
    if len(layup) != len(stiffness.qbars):
        raise ValueError("layup length does not match the assembled laminate")
    N = np.zeros(3, dtype=float)
    M = np.zeros(3, dtype=float)
    for index, (ply, qbar) in enumerate(zip(layup, stiffness.qbars)):
        material_index = ply["mat"]
        if not 0 <= material_index < len(materials):
            raise ValueError(f"ply {index} mat index {material_index} is out of range")
        alpha_local = _local_cte(materials[material_index], material_index)
        alpha_global = transform_cte(*alpha_local[:2], ply["theta"], alpha_local[2])
        dT = dT_by_material[material_index]
        z0, z1 = stiffness.z[index], stiffness.z[index + 1]
        thermal_stress = qbar @ alpha_global * dT
        N += thermal_stress * (z1 - z0)
        M += 0.5 * thermal_stress * (z1**2 - z0**2)
    vector = np.concatenate((N, M))
    return ThermalResultants(N=N, M=M, vector=vector)


def recover_thermal_response(
    stiffness: LaminateStiffness,
    layup: list,
    materials: list,
    delta_temperature,
    mechanical_loads: np.ndarray | None = None,
) -> LaminateResponse:
    """Recover total strains and local stresses for thermal plus optional mechanical loading.

    With ``mechanical_loads=None`` this is the free laminate response to dT,
    including self-equilibrated residual ply stresses.
    """

    dT_by_material = _temperature_changes(delta_temperature, materials)
    loads = np.zeros(6, dtype=float) if mechanical_loads is None else np.asarray(mechanical_loads, dtype=float)
    if loads.shape != (6,) or not np.all(np.isfinite(loads)):
        raise ValueError("mechanical_loads must be six finite values [Nx, Ny, Nxy, Mx, My, Mxy]")
    thermal = compute_thermal_resultants(stiffness, layup, materials, dT_by_material)
    solution = np.linalg.solve(stiffness.ABD, loads + thermal.vector)
    midplane, curvature = solution[:3], solution[3:]
    surfaces = []
    for index, ply in enumerate(layup):
        material = materials[ply["mat"]]
        alpha_local = _local_cte(material, ply["mat"])
        dT = dT_by_material[ply["mat"]]
        q = compute_Q_matrix(material["E1"], material["E2"], material["G12"], material["v12"])
        for surface, z in (("Bottom", stiffness.z[index]), ("Top", stiffness.z[index + 1])):
            global_strain = midplane + z * curvature
            local_strain = transform_stress_strain(global_strain, ply["theta"], "strain")
            local_stress = q @ (local_strain - alpha_local * dT)
            surfaces.append(PlySurfaceResponse(
                index + 1, float(ply["theta"]), surface, float(z),
                global_strain, local_strain, local_stress,
            ))
    return LaminateResponse(midplane, curvature, tuple(surfaces))


def _positive_tsai_wu_root(thermal_stress: np.ndarray, mechanical_stress: np.ndarray,
                            strengths: StrengthAllowables) -> float:
    """First non-negative lambda satisfying FI(thermal + lambda*mechanical) = 1."""

    f0 = tsai_wu(thermal_stress, strengths)
    if f0 >= 1.0:
        return 0.0
    # Expand the existing Tsai-Wu polynomial analytically: differencing FI
    # loses the quadratic coefficient for a small mechanical load/preload.
    f11 = 1.0 / (strengths.Xt * strengths.Xc)
    f22 = 1.0 / (strengths.Yt * strengths.Yc)
    f12 = -0.5 * math.sqrt(f11 * f22)
    quadratic = np.array([[f11, f12, 0.0], [f12, f22, 0.0],
                          [0.0, 0.0, 1.0 / strengths.S**2]])
    linear = np.array([1.0 / strengths.Xt - 1.0 / strengths.Xc,
                       1.0 / strengths.Yt - 1.0 / strengths.Yc, 0.0])
    a = float(mechanical_stress @ quadratic @ mechanical_stress)
    b = float((2.0 * quadratic @ thermal_stress + linear) @ mechanical_stress)
    c = f0 - 1.0
    if a <= 0.0:
        return -c / b if b > 0.0 else math.inf
    discriminant = b * b - 4.0 * a * c
    if discriminant < 0.0:
        return math.inf
    root = math.sqrt(max(discriminant, 0.0))
    return -2.0 * c / (b + root) if b >= 0.0 else (-b + root) / (2.0 * a)


def _positive_max_stress_root(thermal_stress: np.ndarray, mechanical_stress: np.ndarray,
                              strengths: StrengthAllowables) -> float:
    if evaluate_failure(thermal_stress, strengths).maximum_stress_utilization >= 1.0:
        return 0.0
    limits = ((strengths.Xt, -strengths.Xc), (strengths.Yt, -strengths.Yc), (strengths.S, -strengths.S))
    candidates = []
    for initial, increment, component_limits in zip(thermal_stress, mechanical_stress, limits):
        if increment == 0.0:
            continue
        for limit in component_limits:
            factor = (limit - initial) / increment
            if factor >= 0.0:
                candidates.append(float(factor))
    return min(candidates, default=math.inf)


def first_ply_mechanical_load_factor(
    thermal_response: LaminateResponse,
    mechanical_response: LaminateResponse,
    strengths,
) -> tuple[int, float, str]:
    """First-ply factor on mechanical load with the thermal residual stress held fixed.

    ``thermal_response`` is recovered with dT and zero mechanical load.
    ``mechanical_response`` is recovered with the mechanical load and dT=0.
    Strengths may be one record for every surface or a per-surface list.
    """

    thermal_surfaces = thermal_response.ply_surfaces
    mechanical_surfaces = mechanical_response.ply_surfaces
    if len(thermal_surfaces) != len(mechanical_surfaces) or not thermal_surfaces:
        raise ValueError("thermal and mechanical responses must contain matching ply surfaces")
    per_surface = list(strengths) if isinstance(strengths, (list, tuple)) else [strengths] * len(thermal_surfaces)
    if len(per_surface) != len(thermal_surfaces):
        raise ValueError("strengths length must match the number of ply surfaces")
    thresholds = []
    for thermal_point, mechanical_point, allow in zip(thermal_surfaces, mechanical_surfaces, per_surface):
        maximum = _positive_max_stress_root(thermal_point.local_stress, mechanical_point.local_stress, allow)
        tsai = _positive_tsai_wu_root(thermal_point.local_stress, mechanical_point.local_stress, allow)
        thresholds.append((maximum, tsai))
    index = min(range(len(thresholds)), key=lambda i: min(thresholds[i]))
    maximum, tsai = thresholds[index]
    factor = min(maximum, tsai)
    if not math.isfinite(factor):
        return index, factor, "No mechanical load"
    return index, factor, "Maximum Stress" if maximum <= tsai else "Tsai–Wu"
