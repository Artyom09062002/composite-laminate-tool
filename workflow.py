"""Input handling and design screening shared by the UI and tests.

The validated CLT equations remain in ``core``. This module only prepares
inputs and summarizes their outputs for interactive exploration.
"""

from dataclasses import dataclass
import math
import re

import numpy as np

from core import StrengthAllowables, assemble_laminate_stiffness, evaluate_failure, recover_ply_surfaces, tsai_wu_load_factor


def parse_layup(text: str, thickness_m: float) -> list[dict]:
    """Parse comma/slash separated angles, with optional symmetric ``s`` suffix."""
    if not math.isfinite(thickness_m) or thickness_m <= 0:
        raise ValueError("Ply thickness must be positive and finite")
    expression = text.strip()
    symmetric = expression.lower().endswith("s")
    if symmetric:
        expression = expression[:-1].strip()
    if expression.startswith("[") != expression.endswith("]"):
        raise ValueError("Close the layup brackets or omit both brackets")
    expression = expression.strip("[] ")
    pieces = re.split(r"[,/]", expression)
    if not pieces or any(not part.strip() for part in pieces):
        raise ValueError("Enter angles such as [0, 45, -45, 90]s")
    try:
        angles = [float(part.strip()) for part in pieces]
    except ValueError as exc:
        raise ValueError("Every ply angle must be a number in degrees") from exc
    if not all(math.isfinite(angle) for angle in angles):
        raise ValueError("Every ply angle must be finite")
    if symmetric:
        angles += list(reversed(angles))
    if len(angles) > 100:
        raise ValueError("Use at most 100 plies in the interactive tool")
    return [{"theta": angle, "t": thickness_m, "mat": 0} for angle in angles]


def editor_to_layup(rows, material_names: list[str] | None = None) -> list[dict]:
    """Validate all rows; never silently omit a malformed ply.

    If ``material_names`` is given, an optional ``"Material"`` cell selects the ply's
    material by name (its position in the list becomes ``mat``); a blank cell means 0.
    """
    if not 1 <= len(rows) <= 100:
        raise ValueError("The layup must contain between 1 and 100 plies")
    result = []
    for index, row in enumerate(rows, start=1):
        try:
            angle = float(row["Angle [deg]"])
            thickness_mm = float(row["Thickness [mm]"])
        except (TypeError, ValueError, KeyError) as exc:
            raise ValueError(f"Ply {index}: enter an angle and thickness") from exc
        if not math.isfinite(angle) or not math.isfinite(thickness_mm) or thickness_mm <= 0:
            raise ValueError(f"Ply {index}: angle must be finite and thickness positive")
        mat = 0
        name = row.get("Material") if material_names is not None else None
        if isinstance(name, str) and name:
            if name not in material_names:
                raise ValueError(f"Ply {index}: unknown material '{name}'")
            mat = material_names.index(name)
        result.append({"theta": angle, "t": thickness_mm * 1e-3, "mat": mat})
    return result


def _canonical(angle: float) -> float:
    normalized = ((float(angle) + 90.0) % 180.0) - 90.0
    return 0.0 if abs(normalized) < 1e-10 else normalized


def is_symmetric(layup: list[dict]) -> bool:
    return all(
        math.isclose(_canonical(left["theta"]), _canonical(right["theta"]), abs_tol=1e-8)
        and math.isclose(float(left["t"]), float(right["t"]), rel_tol=1e-8, abs_tol=1e-12)
        and left["mat"] == right["mat"]
        for left, right in zip(layup, reversed(layup))
    )


def is_balanced(layup: list[dict]) -> bool:
    """Check matching +theta/-theta total thickness of the same material for each off-axis family."""
    by_angle: dict[tuple[float, int], float] = {}
    for ply in layup:
        angle = _canonical(ply["theta"])
        if math.isclose(angle, 0.0, abs_tol=1e-8) or math.isclose(abs(angle), 90.0, abs_tol=1e-8):
            continue
        key = (round(angle, 8), ply["mat"])
        by_angle[key] = by_angle.get(key, 0.0) + float(ply["t"])
    return all(math.isclose(value, by_angle.get((-angle, mat), 0.0), rel_tol=1e-8, abs_tol=1e-12)
               for (angle, mat), value in by_angle.items())


def first_ply_limit(surfaces, strengths):
    """Return ``(index, load_factor, criterion)`` of the first ply surface to reach a limit.

    ``load_factor`` is the proportional multiplier on the entered load vector at which
    Maximum Stress or Tsai-Wu first reaches 1 (``math.inf`` when nothing is loaded).
    ``index`` is the position in ``surfaces``; criterion is "No load" when unbounded.
    ``strengths`` is one StrengthAllowables for all surfaces, or a list with one per surface
    (hybrid laminates, where each ply's material has its own allowables).
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


@dataclass(frozen=True)
class DesignSummary:
    name: str
    layup: str
    plies: int
    thickness_m: float
    A11: float
    A66: float
    D11: float
    B_norm: float
    epsilon_x: float
    gamma_xy: float
    max_stress_pa: float
    max_utilization: float
    max_tsai_wu: float
    min_tsai_wu_ratio: float
    critical_ply: int | None
    critical_surface: str
    critical_criterion: str
    first_ply_load_factor: float


def assess_design(name: str, layup_text: str, thickness_m: float, material: dict,
                  strengths: StrengthAllowables, loads: np.ndarray) -> DesignSummary:
    layup = parse_layup(layup_text, thickness_m)
    stiffness = assemble_laminate_stiffness(layup, [material])
    response = recover_ply_surfaces(stiffness, layup, [material], loads)
    failures = [evaluate_failure(p.local_stress, strengths) for p in response.ply_surfaces]
    critical_index, load_factor, criterion = first_ply_limit(response.ply_surfaces, strengths)
    critical = response.ply_surfaces[critical_index] if math.isfinite(load_factor) else None
    return DesignSummary(
        name=name, layup=layup_text, plies=len(layup),
        thickness_m=sum(float(ply["t"]) for ply in layup),
        A11=float(stiffness.A[0, 0]), A66=float(stiffness.A[2, 2]),
        D11=float(stiffness.D[0, 0]),
        B_norm=float(np.max(np.abs(stiffness.B))),
        epsilon_x=float(response.midplane_strain[0]),
        gamma_xy=float(response.midplane_strain[2]),
        max_stress_pa=max(float(np.max(np.abs(p.local_stress))) for p in response.ply_surfaces),
        max_utilization=max(f.maximum_stress_utilization for f in failures),
        max_tsai_wu=max(f.tsai_wu_index for f in failures),
        min_tsai_wu_ratio=min(tsai_wu_load_factor(p.local_stress, strengths) for p in response.ply_surfaces),
        critical_ply=critical.ply if critical else None,
        critical_surface=critical.surface if critical else "—",
        critical_criterion=criterion,
        first_ply_load_factor=load_factor,
    )
