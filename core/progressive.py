"""Progressive (ply-by-ply) failure of a laminate: a ply-discount SCREENING model, first-ply to termination load factor.

Method (load-controlled ply-discount analysis, linear between events)
---------------------------------------------------------------------
The laminate carries a load vector ``lambda * unit_loads``. With a fixed stiffness the response is linear, so the
load factor at which each ply/mode next reaches its Hashin limit is exact (``failure.hashin_load_factors``): there are
no fixed load increments, the load factor advances failure by failure.

1. Assemble ABD from the current ply properties and solve the unit load case; recover the local stress at the bottom
   and top face of every ply.
2. For every ply and every Hashin mode whose family (fibre / matrix) has NOT yet failed, take the load factor at
   which it reaches 1; the smallest is the next failure. If it is below the current load factor (the redistribution
   after the previous failure overloads a ply at once) the failure happens at the CURRENT load factor, so the
   load-factor history never decreases (see "What the load-factor history means"). Failures within 1e-9 (relative)
   of each other are applied together.
3. Degrade the failed ply (rules below), reassemble ABD and repeat.
4. TWO-LEVEL RESIDUAL-STIFFNESS TERMINATION RULE. Nothing caps the stress in a degraded ply. Instead the degraded ply
   is re-checked against its ORIGINAL strengths. If a mode of an already-failed family exceeds its strength again before
   the next new failure, that family is degraded ONE MORE time (an "escalation": listed in the history, not in the
   failure sequence). If a mode of a family that has already been degraded twice exceeds its strength, the analysis
   stops. It also stops when no ply carries a stress that could still cause failure. Any failures that occur at the
   same load factor as the stopping condition are recorded first and then the analysis stops. The stop is a discrete
   bookkeeping rule ("two degradations"), not the disappearance of the load path, an energy criterion or a measured
   residual strength.

What the stopping load factor is and is not
-------------------------------------------
``last_ply_load_factor`` is the load factor at which THIS algorithm stops for the chosen residual rules. It is an internal
index of the discount model, not a validated ultimate or burst load; every residual stiffness stays positive, so the
laminate always keeps a (shrinking) load path and no equilibrium or stability condition is checked. A burst or ultimate-load
claim needs correlation with tests of the corresponding structure.

What the load-factor history means
----------------------------------
The history is a sequence of linear-elastic equilibrium states of the degraded laminate with the applied load held at its
highest value so far: after a failure the redistributed state is evaluated at the same (or higher) load factor, never at a
lower one. Under load control this does not prove that a stable quasi-static path exists: a real structure may snap through,
snap back or grow damage dynamically. Steps where the redistribution had to be "held" because a ply was already beyond its
limit are flagged (``LoadStep.cascade``). Softening needs displacement control or arc-length methods and a stability
criterion, which are not implemented.

Degradation rules - MODEL ASSUMPTIONS, not material data
--------------------------------------------------------
    fibre failure (Fibre tension or Fibre compression):    E1  -> ``fibre_E1_factor`` * E1            (default 0.01)
                                                           E2  -> ``fibre_E2_factor`` * E2            (default 1: kept)
                                                           G12 -> ``fibre_G12_factor`` * G12          (default 1: kept)
    matrix failure (Matrix tension or Matrix compression): E2  -> ``matrix_E2_factor`` * E2,
                                                           G12 -> ``matrix_G12_factor`` * G12         (default 0.1 each)
A family at degradation level k (0 intact, 1 failed, 2 escalated) has its factors raised to the power k. nu12 is scaled
by the E1 factor, so S12 = -nu12/E1 is unchanged: the compliance matrix then grows only on its diagonal (S11 = 1/E1,
S22 = 1/E2, S66 = 1/G12), so a failure can never make Q stiffer in any direction and Q stays positive definite for any
factors in (0, 1] (holding nu21 or nu12 constant instead can stiffen the ply along the fibres or make the plane-stress
denominator non-positive). The factors are conventional, not measured, and are the same for tension and compression;
they depend on material, layup, thickness and purpose in practice. Without calibration the right way to report a result is a
range over reasonable factors (see ``validation/``), not one number. Keeping E2 and G12 after a fibre failure is a
simplification that can overstate the residual capacity of a ply that has broken across a band; set ``fibre_E2_factor``
and ``fibre_G12_factor`` below 1 to test it.

Shear-dominated fibre-tension initiation
----------------------------------------
With alpha > 0 the fibre-tension index contains the shear term, so in a shear-dominated state (for example pure in-plane
shear, sigma1 = 0, tau12 = S) the fibre-tension and matrix-tension indices reach 1 together although no fibre is loaded.
Applying the fibre rule (E1 x 0.01) there would remove the whole fibre stiffness of a ply whose fibres carry no stress.
Policy used (``shear_dominated_fibre='matrix'``, the default): when the fibre-tension index is reached while its own
normal-stress term (sigma1/Xt)^2 is smaller than its shear term alpha (tau12/S)^2, the event is recorded as
"Shear-dominated fibre tension" and applied as MATRIX damage. The initiation load factor is unchanged (Hashin's index is
not weakened); only the consequence is changed. ``'fibre'`` restores the literal rule. This is a modelling choice and has not
been validated against combined sigma1-tau12 tests.

Limits: delamination, interlaminar stresses, fibre-matrix interaction beyond Hashin, in-situ strength effects, nonlinear shear,
geometric nonlinearity, thermal stress, open holes and other stress concentrators, fatigue, impact, moisture/temperature,
manufacturing defects, fibre kinking, crack growth, leakage and loss of stability are not modelled. There is no fracture
energy or characteristic length: results are not mesh-objective and are meaningful only for a real ply-by-ply discretisation
(one computational ply per physical ply). Tests showed identical load factors for a physical ply split into sub-plies in the
membrane, unsymmetric and pure-bending cases tried, but the number of events and steps changes with the discretisation and
no general mesh-independence is claimed.
"""
from dataclasses import dataclass
import math

import numpy as np

from .failure import hashin_fibre_tension_is_shear_dominated, hashin_load_factors
from .laminate import assemble_laminate_stiffness
from .response import recover_ply_surfaces

ASSUMPTIONS = (
    "Degradation factors are model assumptions, not material data: "
    "fibre failure -> E1 x {fibre_E1_factor:g}{fibre_extra}; matrix failure -> E2 x {matrix_E2_factor:g} and G12 x {matrix_G12_factor:g}; "
    "a ply loaded beyond its original strength again is degraded a second time, and a third exceedance ends the analysis "
    "(two-level residual-stiffness termination rule, not a physical strength law); S12 = -nu12/E1 held constant (nu12 scaled with E1). "
    "Initiation: plane-stress Hashin-1980-inspired criterion (alpha = {alpha:g} in fibre tension; fibre-tension initiation dominated by "
    "its shear term is applied as matrix damage; transverse shear strength: {st_text}). "
    "Linear elastic between failures, load-controlled with the load factor never reduced (not a stability analysis), "
    "no delamination, no geometric nonlinearity, no fracture-energy regularisation. "
    "The stopping load factor is the end of this algorithm, not a validated ultimate or burst load."
)

SHEAR_DOMINATED_MODE = "Shear-dominated fibre tension"
_FAMILY = {"Fibre tension": "fibre", "Fibre compression": "fibre", "Matrix tension": "matrix", "Matrix compression": "matrix",
           SHEAR_DOMINATED_MODE: "matrix"}
_BATCH_RTOL = 1e-9


@dataclass(frozen=True)
class DegradationRules:
    """Stiffness retained after a failure (fractions of the pristine value, in (0, 1]). Model assumptions.

    ``fibre_E2_factor`` and ``fibre_G12_factor`` default to 1 (a fibre failure removes only E1, the original rule); lower
    values test the simplification that a ply broken across its fibres keeps its transverse and shear stiffness.
    """
    fibre_E1_factor: float = 0.01
    matrix_E2_factor: float = 0.1
    matrix_G12_factor: float = 0.1
    fibre_E2_factor: float = 1.0
    fibre_G12_factor: float = 1.0

    def __post_init__(self) -> None:
        for name in ("fibre_E1_factor", "matrix_E2_factor", "matrix_G12_factor", "fibre_E2_factor", "fibre_G12_factor"):
            value = getattr(self, name)
            if not (math.isfinite(value) and 0.0 < value <= 1.0):
                raise ValueError(f"{name} must lie in (0, 1]")

    def statement(self, transverse_shear_assumed: bool | None = None, shear_factor: float = 1.0) -> str:
        """The assumption text. ``transverse_shear_assumed`` says whether Hashin used the assumed St (None: not known)."""
        extra = ""
        if self.fibre_E2_factor != 1.0 or self.fibre_G12_factor != 1.0:
            extra = f" and E2 x {self.fibre_E2_factor:g}, G12 x {self.fibre_G12_factor:g}"
        st_text = {None: "given or assumed Yc/(2 tan 53 deg), see the strengths",
                   True: "ASSUMED Yc/(2 tan 53 deg), not measured",
                   False: "as supplied"}[transverse_shear_assumed]
        return ASSUMPTIONS.format(**self.__dict__, fibre_extra=extra, alpha=shear_factor, st_text=st_text)


@dataclass(frozen=True)
class FailureEvent:
    """One Hashin failure: load factor, 1-based ply, face with the governing stress, mode and family."""
    step: int
    load_factor: float
    ply: int
    surface: str
    mode: str
    family: str          # "fibre" or "matrix"


@dataclass(frozen=True)
class LoadStep:
    """State after one batch of failures (step 0 = pristine at load factor 0)."""
    step: int
    load_factor: float
    failed_fibre_plies: int
    failed_matrix_plies: int
    stiffness_ratio: float            # secant stiffness along the load vector relative to the pristine laminate
    strain_before: np.ndarray         # mid-plane strain [ex, ey, gxy] at this load factor, stiffness before the failure
    strain_after: np.ndarray          # same load factor, degraded stiffness (the jump caused by the failure)
    kind: str = "failure"             # "failure" (new Hashin failures) or "escalation" (residual strength exceeded)
    escalations: tuple[tuple[int, str], ...] = ()   # (1-based ply, family) degraded a second time in an escalation step
    cascade: bool = False             # True: a ply was already beyond its limit after the previous step and the load factor was held


@dataclass(frozen=True)
class ProgressiveResult:
    """``events`` is the sequence of Hashin failures (one per ply and family, in order); ``history`` has one entry per
    step, including residual-strength escalations (see the module docstring). ``last_ply_load_factor`` is where this
    discount algorithm stops, not a validated ultimate load."""
    events: tuple[FailureEvent, ...]
    history: tuple[LoadStep, ...]
    first_ply_load_factor: float
    last_ply_load_factor: float
    final_strain: np.ndarray          # mid-plane strain at the stopping load factor
    collapse_reason: str
    rules: DegradationRules
    assumptions: str

    @property
    def cascade_steps(self) -> int:
        """Number of steps in which the load factor had to be held because a ply was already beyond its limit."""
        return sum(step.cascade for step in self.history)

    def load_strain_curve(self, component: int = 1) -> tuple[np.ndarray, np.ndarray]:
        """(load factor, mid-plane strain component) polyline: linear segments with a jump at each failure step."""
        load, strain = [0.0], [0.0]
        for step in self.history[1:]:
            load += [step.load_factor, step.load_factor]
            strain += [float(step.strain_before[component]), float(step.strain_after[component])]
        load.append(self.last_ply_load_factor)
        strain.append(float(self.final_strain[component]))
        return np.array(load), np.array(strain)


def degraded_material(material: dict, rules: DegradationRules, fibre_level: int, matrix_level: int) -> dict:
    """Ply material at the given degradation levels (0 intact, 1 failed, 2 escalated; ``bool`` also accepted).

    nu12 is scaled with E1 so that S12 = -nu12/E1 is unchanged (see the module docstring).
    """
    fl, ml = int(fibre_level), int(matrix_level)
    e1f = rules.fibre_E1_factor ** fl
    e2f = rules.matrix_E2_factor ** ml * rules.fibre_E2_factor ** fl
    gf = rules.matrix_G12_factor ** ml * rules.fibre_G12_factor ** fl
    return {**material, "E1": material["E1"] * e1f, "E2": material["E2"] * e2f, "G12": material["G12"] * gf,
            "v12": material["v12"] * e1f}


@dataclass(frozen=True)
class _Plan:
    """What the next step does. ``action``: 'exhausted', 'terminate', 'escalate' or 'fail'."""
    action: str
    load_factor: float = math.inf
    candidates: tuple = ()            # (ratio, ply index, surface, mode, family) applied in this step
    cascade: bool = False


def _plan_step(by_level: dict[int, list], load_factor: float) -> _Plan:
    """Choose the next step from the candidate failures grouped by the degradation level of their family.

    Level 0 = a first failure, 1 = an escalation (second degradation), 2 = the terminating exceedance. Ties are resolved
    consistently: everything within ``_BATCH_RTOL`` of the lowest load factor belongs to the same batch. When the
    terminating exceedance is part of the lowest batch, the new failures of that batch are returned with the 'terminate'
    action so that they are recorded before the analysis stops.
    """
    next_new = min((c[0] for c in by_level[0]), default=math.inf)
    next_escalation = min((c[0] for c in by_level[1]), default=math.inf)
    next_terminal = min((c[0] for c in by_level[2]), default=math.inf)
    lowest = min(next_new, next_escalation, next_terminal)
    if math.isinf(lowest):
        return _Plan("exhausted")
    cascade = lowest < load_factor * (1.0 - _BATCH_RTOL)
    reach = lowest * (1.0 + _BATCH_RTOL)
    if next_terminal <= reach:
        batch = tuple(c for c in by_level[0] if c[0] <= reach)
        return _Plan("terminate", max(load_factor, next_terminal), batch, cascade)
    if next_escalation <= min(next_new, reach):
        batch = tuple(c for c in by_level[1] if c[0] <= reach)
        return _Plan("escalate", max(load_factor, next_escalation), batch, cascade)
    return _Plan("fail", max(load_factor, next_new), tuple(c for c in by_level[0] if c[0] <= reach), cascade)


def progressive_failure(layup: list[dict], materials: list[dict], strengths, unit_loads: np.ndarray,
                        rules: DegradationRules | None = None, shear_factor: float = 1.0,
                        shear_dominated_fibre: str = "matrix") -> ProgressiveResult:
    """First-ply to termination load factors of a laminate under ``lambda * unit_loads`` (see the module docstring).

    ``unit_loads`` is the 6-vector [Nx, Ny, Nxy, Mx, My, Mxy] of the reference load case (for a pressure vessel,
    the resultants at 1 Pa, so the load factors are pressures in Pa); ``strengths`` holds one StrengthAllowables per
    material, indexed like ``ply["mat"]``. ``shear_dominated_fibre`` is 'matrix' (default) or 'fibre' (literal rule).
    """
    rules = rules or DegradationRules()
    if shear_dominated_fibre not in ("matrix", "fibre"):
        raise ValueError("shear_dominated_fibre must be 'matrix' or 'fibre'")
    unit = np.asarray(unit_loads, dtype=float)
    if unit.shape != (6,) or not np.all(np.isfinite(unit)) or not np.any(unit):
        raise ValueError("unit_loads must be a finite, nonzero length-6 vector [Nx, Ny, Nxy, Mx, My, Mxy]")
    count = len(layup)
    assemble_laminate_stiffness(layup, materials)          # validates the layup and materials once, up front
    ply_strengths = [strengths[ply["mat"]] for ply in layup]
    st_assumed = any(s.St is None for s in ply_strengths)
    statement = rules.statement(st_assumed, shear_factor)
    level = {"fibre": [0] * count, "matrix": [0] * count}

    def response():
        ply_materials = [degraded_material(materials[ply["mat"]], rules, level["fibre"][i], level["matrix"][i])
                         for i, ply in enumerate(layup)]
        ply_layup = [{"theta": ply["theta"], "t": ply["t"], "mat": i} for i, ply in enumerate(layup)]
        stiffness = assemble_laminate_stiffness(ply_layup, ply_materials)
        return recover_ply_surfaces(stiffness, ply_layup, ply_materials, unit)

    def compliance(state) -> float:                         # unit . strain: inverse of the secant stiffness along the load
        return float(unit[:3] @ state.midplane_strain + unit[3:] @ state.curvature)

    state = response()
    base_compliance = compliance(state)
    events: list[FailureEvent] = []
    history = [LoadStep(0, 0.0, 0, 0, 1.0, np.zeros(3), np.zeros(3))]
    load_factor = 0.0

    def record(step, plan, kind):
        """Apply the plan's candidates, rebuild the response and append the history entry."""
        nonlocal state, load_factor
        load_factor = plan.load_factor
        before = load_factor * state.midplane_strain
        escalations = ()
        if kind == "failure":
            chosen: dict[tuple[int, str], tuple] = {}        # one event per (ply, family): its lowest-ratio mode
            for candidate in plan.candidates:
                key = (candidate[1], candidate[4])
                if key not in chosen or candidate[0] < chosen[key][0]:
                    chosen[key] = candidate
            for _, index, surface, mode, family in sorted(chosen.values(), key=lambda c: (c[1], c[4])):
                events.append(FailureEvent(step, load_factor, index + 1, surface, mode, family))
                level[family][index] = 1
        else:
            hit = sorted({(c[1], c[4]) for c in plan.candidates})
            for index, family in hit:
                level[family][index] = 2
            escalations = tuple((index + 1, family) for index, family in hit)
        state = response()
        history.append(LoadStep(step, load_factor, sum(v > 0 for v in level["fibre"]), sum(v > 0 for v in level["matrix"]),
                                base_compliance / compliance(state), before, load_factor * state.midplane_strain,
                                kind, escalations, plan.cascade))

    for step in range(1, 4 * count + 2):
        by_level = {0: [], 1: [], 2: []}                    # candidates by the degradation level of their family
        for point in state.ply_surfaces:
            index = point.ply - 1
            for mode, ratio in hashin_load_factors(point.local_stress, ply_strengths[index], shear_factor).items():
                if (mode == "Fibre tension" and shear_dominated_fibre == "matrix"
                        and hashin_fibre_tension_is_shear_dominated(point.local_stress, ply_strengths[index], shear_factor)):
                    mode = SHEAR_DOMINATED_MODE              # shear drives the index: matrix damage, not fibre rupture
                family = _FAMILY[mode]
                by_level[level[family][index]].append((ratio, index, point.surface, mode, family))
        plan = _plan_step(by_level, load_factor)
        if plan.action == "exhausted":
            return _finish(events, history, load_factor, state, rules, statement,
                           "no ply carries a stress that can still cause failure")
        if plan.action == "terminate":
            if plan.candidates:                              # failures at the same load factor are recorded before stopping
                record(step, plan, "failure")
            reason = ("a family that is already degraded twice would exceed its strength again (two-level residual-stiffness "
                      "termination rule): the algorithm stops")
            return _finish(events, history, plan.load_factor, state, rules, statement, reason)
        record(step, plan, "escalation" if plan.action == "escalate" else "failure")
    raise RuntimeError("progressive failure did not terminate")                    # at most 2 flags per family and ply


def _finish(events, history, last_load_factor, state, rules, statement, reason) -> ProgressiveResult:
    if not events:
        raise ValueError("The laminate carries no load that can cause failure")
    return ProgressiveResult(
        events=tuple(events), history=tuple(history), first_ply_load_factor=events[0].load_factor,
        last_ply_load_factor=float(last_load_factor), final_strain=float(last_load_factor) * state.midplane_strain,
        collapse_reason=reason, rules=rules, assumptions=statement)
