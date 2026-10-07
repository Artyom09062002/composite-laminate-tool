"""Key numerical outputs of the v3 app, computed from core/ with the app's default inputs.

Used by tests/test_snapshot_v3.py (compare) and, with ``--write``, to regenerate
tests/snapshot_v3.json. Regenerate only for a confirmed error fix, with the reason in the commit.

Inputs mirror the app defaults: T300/5208 (materials/database.py), [0,45,-45,90]s with 0.125 mm plies,
Nx = 100 kN/m; vessel R = 100 mm, 16-ply +/-theta wall; dome r0/R = 0.5, hemisphere; thermal dT = -100 C and
cooling from the sourced 250 F reference to -196 C. Degradation factors are the app defaults (0.01, 0.1, 0.1).
"""
import json
import math
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import (StrengthAllowables, assemble_laminate_stiffness, recover_ply_surfaces, recover_thermal_response,
                  compute_thermal_resultants, first_ply_mechanical_load_factor, temperature_change_from_reference)
from core.dome import cylinder_winding_angle_deg, dome_stations
from core.optimise import optimise_cylinder
from core.progressive import DegradationRules, progressive_failure
from core.vessel import NETTING_ANGLE_DEG, cylinder_resultants
from materials import DEFAULT_MATERIALS
from workflow import angle_ply_wall, first_ply_limit, parse_layup, screen_cylinder

SNAPSHOT_PATH = pathlib.Path(__file__).with_name("snapshot_v3.json")
T300 = DEFAULT_MATERIALS["Graphite/Epoxy (T300/5208)"]
PLY_T = T300.ply_thickness  # 0.125 mm
RADIUS_M = 0.1
WALL_PLIES = 16


def _material():
    return T300.as_thermal_core_material()


def _strengths():
    return StrengthAllowables(**T300.as_strengths())


def _laminate():
    layup = parse_layup("[0,45,-45,90]s", PLY_T)
    return layup, assemble_laminate_stiffness(layup, [_material()])


def laminate_block():
    layup, stiffness = _laminate()
    loads = np.array([100e3, 0, 0, 0, 0, 0])
    response = recover_ply_surfaces(stiffness, layup, [_material()], loads)
    index, factor, criterion = first_ply_limit(response.ply_surfaces, [_strengths()] * len(response.ply_surfaces))
    point = response.ply_surfaces[index]
    return {
        "layup": "[0,45,-45,90]s", "ply_thickness_m": PLY_T, "unit_note": "A [N/m], B [N], D [N m], SI",
        "A": stiffness.A.tolist(), "B": stiffness.B.tolist(), "D": stiffness.D.tolist(),
        "load_Nx_N_per_m": 100e3, "midplane_strain": list(map(float, response.midplane_strain)),
        "curvature": list(map(float, response.curvature)),
        "first_ply_load_factor": float(factor), "first_ply_criterion": criterion,
        "first_ply_ply": int(point.ply), "first_ply_surface": point.surface,
    }


def _vessel_case(layup, label):
    materials, strengths = [_material()], [_strengths()]
    screen = screen_cylinder(layup, materials, strengths, RADIUS_M)
    progressive = progressive_failure(layup, materials, strengths, cylinder_resultants(1.0, RADIUS_M),
                                      DegradationRules(0.01, 0.1, 0.1))
    return {
        "label": label, "radius_m": RADIUS_M,
        "first_ply_clt_pa": float(screen.first_ply_pressure_pa), "first_ply_ply": screen.first_ply_ply,
        "first_ply_surface": screen.first_ply_surface, "first_ply_criterion": screen.first_ply_criterion,
        "first_ply_mode": screen.first_ply_mode,
        "first_ply_hashin_pa": float(progressive.first_ply_load_factor),
        "last_ply_model_stop_pa": float(progressive.last_ply_load_factor),
        "last_ply_collapse_reason": progressive.collapse_reason, "n_failure_events": len(progressive.events),
        "netting_pressure_pa": float(screen.netting_pressure_pa), "netting_bound_pa": float(screen.netting_bound_pa),
    }


def vessel_block():
    default_layup, _ = _laminate()
    netting_wall = angle_ply_wall(NETTING_ANGLE_DEG, WALL_PLIES, PLY_T)
    return {
        "netting_angle_deg": NETTING_ANGLE_DEG,
        "default_layup": _vessel_case(default_layup, "[0,45,-45,90]s, R = 100 mm (app default layup)"),
        "t300_5208_netting_angle": _vessel_case(netting_wall, "T300/5208 16-ply +/-54.7356 deg wall, R = 100 mm"),
    }


def dome_block():
    r0 = 0.5 * RADIUS_M
    alpha0 = cylinder_winding_angle_deg(r0, RADIUS_M)
    layup = angle_ply_wall(alpha0, WALL_PLIES, PLY_T)
    result = dome_stations(layup, [_material()], [_strengths()], r0, RADIUS_M, aspect_ratio=1.0)
    weakest = result.weakest_valid_index()
    return {
        "r0_over_R": 0.5, "dome_depth_over_R": 1.0, "alpha0_deg": float(alpha0),
        "thickness_cylinder_m": float(result.thickness_m[0]), "thickness_last_station_m": float(result.thickness_m[-1]),
        "n_stations": int(len(result.radius_m)), "n_membrane_valid": int(result.membrane_valid.sum()),
        "bending_zone_m": float(result.bending_zone_m),
        "weakest_valid_index": weakest, "weakest_valid_first_ply_pa": float(result.first_ply_pressure_pa[weakest]),
        "weakest_valid_mode": result.first_ply_mode[weakest],
        "cylinder_first_ply_pa": float(screen_cylinder(layup, [_material()], [_strengths()], RADIUS_M).first_ply_pressure_pa),
        "first_ply_pressure_pa_by_station": result.first_ply_pressure_pa.tolist(),
        "alpha_deg_by_station": result.alpha_deg.tolist(),
    }


def thermal_block():
    layup, stiffness = _laminate()
    materials = [_material()]
    strengths = [_strengths()] * (2 * len(layup))
    loads = np.array([100e3, 0, 0, 0, 0, 0])
    mechanical = recover_ply_surfaces(stiffness, layup, materials, loads)
    cases = {
        "direct_dT_minus_100C": -100.0,
        "cool_from_reference_to_minus_196C": temperature_change_from_reference(T300.thermal_reference_temperature_c, -196.0),
    }
    out = {"thermal_reference_c": T300.thermal_reference_temperature_c, "alpha1": T300.alpha1, "alpha2": T300.alpha2,
           "cases": {}}
    for name, dT in cases.items():
        resultants = compute_thermal_resultants(stiffness, layup, materials, dT)
        free = recover_thermal_response(stiffness, layup, materials, dT)
        index, factor, criterion = first_ply_mechanical_load_factor(free, mechanical, strengths)
        out["cases"][name] = {
            "delta_T_c": float(dT), "N_T_N_per_m": resultants.N.tolist(), "M_T_N": resultants.M.tolist(),
            "free_midplane_strain": list(map(float, free.midplane_strain)), "free_curvature": list(map(float, free.curvature)),
            "max_abs_residual_sigma2_pa": float(max(abs(p.local_stress[1]) for p in free.ply_surfaces)),
            "first_ply_factor_with_thermal_preload": float(factor), "first_ply_criterion": criterion,
        }
    return out


def optimiser_block():
    result = optimise_cylinder(RADIUS_M, WALL_PLIES, PLY_T, _material(), _strengths(), max_candidates=128, seed=2026)
    out = {"seed": 2026, "max_candidates": 128, "evaluated": result.evaluated_count,
           "total_count_vectors": result.total_count_vectors, "netting_optimum_pressure_pa": float(result.netting_optimum_pressure_pa)}
    for objective in ("first_ply", "last_ply", "fibre_limit"):
        best = result.top_for(objective, 1)[0]
        out[f"best_{objective}"] = {
            "angles_deg": list(best.angles_deg), "first_ply_pa": float(best.first_ply_pressure_pa),
            "last_ply_pa": float(best.last_ply_pressure_pa), "fibre_limit_pa": float(best.fibre_limit_pressure_pa)}
    return out


def compute():
    return {
        "_about": "Key outputs of the v3 app at the app defaults (T300/5208, SI). Produced by tests/snapshot_v3_values.py; "
                  "compared by tests/test_snapshot_v3.py. Not validated against measurements: a regression guard, not a reference.",
        "material": T300.name,
        "laminate_example": laminate_block(), "vessel": vessel_block(), "dome": dome_block(),
        "thermal": thermal_block(), "optimiser": optimiser_block(),
    }


if __name__ == "__main__":
    if "--write" in sys.argv:
        SNAPSHOT_PATH.write_text(json.dumps(compute(), indent=1, sort_keys=False) + "\n", encoding="utf-8")
        print("wrote", SNAPSHOT_PATH)
    else:
        print(json.dumps(compute(), indent=1))
