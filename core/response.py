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
