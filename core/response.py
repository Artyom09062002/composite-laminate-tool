"""Linear CLT response and ply stress recovery in the established conventions."""
from dataclasses import dataclass
import numpy as np
from .lamina import compute_Q_matrix
from .transformations import transform_stress_strain
from .laminate import LaminateStiffness

@dataclass(frozen=True)
class PlySurfaceResponse:
    ply: int
    angle_deg: float
    surface: str
    z: float
    global_strain: np.ndarray
    local_strain: np.ndarray
    local_stress: np.ndarray

@dataclass(frozen=True)
class LaminateResponse:
    midplane_strain: np.ndarray
    curvature: np.ndarray
    ply_surfaces: tuple[PlySurfaceResponse, ...]

def solve_laminate_response(stiffness: LaminateStiffness, loads: np.ndarray) -> LaminateResponse:
    """Solve ``[eps0, kappa] = ABD^-1 [N, M]`` and recover each ply surface."""
    loads = np.asarray(loads, dtype=float)
    if loads.shape != (6,):
        raise ValueError("loads must be a length-6 vector [Nx, Ny, Nxy, Mx, My, Mxy]")
    if not np.all(np.isfinite(loads)):
        raise ValueError("loads must contain finite values")
    solution = np.linalg.solve(stiffness.ABD, loads)
    return LaminateResponse(solution[:3], solution[3:], ())

def recover_ply_surfaces(stiffness: LaminateStiffness, layup: list, materials: list, loads: np.ndarray) -> LaminateResponse:
    """Return strains and local stresses at bottom/top of every ply."""
    if len(layup) != len(stiffness.qbars):
        raise ValueError("layup length does not match the assembled laminate")
    base = solve_laminate_response(stiffness, loads)
    surfaces = []
    for index, ply in enumerate(layup):
        material = materials[ply["mat"]]
        q = compute_Q_matrix(material["E1"], material["E2"], material["G12"], material["v12"])
        for surface, z in (("Bottom", stiffness.z[index]), ("Top", stiffness.z[index + 1])):
            global_strain = base.midplane_strain + z * base.curvature
            local_strain = transform_stress_strain(global_strain, ply["theta"], "strain")
            local_stress = q @ local_strain
            surfaces.append(PlySurfaceResponse(index + 1, float(ply["theta"]), surface, float(z), global_strain, local_strain, local_stress))
    return LaminateResponse(base.midplane_strain, base.curvature, tuple(surfaces))


def ply_force_resultants(stiffness: LaminateStiffness, layup: list, materials: list,
                         loads: np.ndarray) -> np.ndarray:
    """Exact per-ply global [Nx, Ny, Nxy] integrals [N/m], shape (n_plies, 3).

    Inputs must describe the same assembled laminate, as for surface recovery.
    Reuse its Q-bars and mechanical ABD solution; no thermal eigenstrain is
    included. Rows follow the established -h/2 to +h/2 ply order. Moments
    affect these forces through curvature, even if applied N is zero.
    """
    if len(layup) != len(stiffness.qbars):
        raise ValueError("layup length does not match the assembled laminate")
    for ply in layup:
        materials[ply["mat"]]  # same material-index contract as surface recovery
    base = solve_laminate_response(stiffness, loads)
    return np.array([
        qbar @ (base.midplane_strain * (z1 - z0)
                + base.curvature * (z1**2 - z0**2) / 2.0)
        for qbar, z0, z1 in zip(stiffness.qbars, stiffness.z[:-1], stiffness.z[1:])
    ])
