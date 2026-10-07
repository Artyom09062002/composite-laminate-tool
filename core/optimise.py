"""Reproducible fixed-mass cylinder layup screening, not a design optimiser.

Only one material, equal physical ply thicknesses, a closed thin cylinder and
mechanical membrane loading are considered. Fixed radius, ply count, thickness
and material imply fixed mass (rho * n * t per unit wall area); no density is
invented. Angles are measured from the cylinder axis, in degrees.

Search space: symmetric stacks described by the counts in one half and, for
odd counts, a centre ply. One canonical ordering represents each count vector.
Pristine B=0 and mirrored plies fail together under membrane loading in the
existing discount model, so this is a count search, not an ordering search.
Small spaces are exhausted. Larger spaces include homogeneous and balanced
single-angle anchors, sample balanced count vectors, then sample general count
vectors using Python's local Random(seed). No continuous/global optimum is
claimed. Unbalanced candidates allow the existing CLT shear response; end
restraints, liner load sharing, thermal effects and manufacturing are excluded.

Metrics deliberately remain separate:
* first_ply: the existing minimum Maximum Stress / Tsai-Wu initiation pressure;
* last_ply: existing Hashin progressive model stopping pressure, NOT burst;
* fibre_limit: existing netting projection bound, NOT a CLT fibre failure check.
The continuous fibre-only reference is theta=atan(sqrt(2)) and p=2*Xt*h/(3*R).
It is a different physical model, not an upper bound on matrix-bearing CLT.
"""

from dataclasses import dataclass
from itertools import combinations_with_replacement
import math
from numbers import Integral, Real
import random

from .failure import StrengthAllowables
from .progressive import DegradationRules, progressive_failure
from .vessel import NETTING_ANGLE_DEG, cylinder_resultants, first_ply_under_unit_load, netting_bound, netting_pressure

DEFAULT_ANGLES = (0.0, -15.0, 15.0, -30.0, 30.0, -45.0, 45.0,
                  -NETTING_ANGLE_DEG, NETTING_ANGLE_DEG, -60.0, 60.0, -75.0, 75.0, 90.0)
OBJECTIVES = ("first_ply", "last_ply", "fibre_limit")


@dataclass(frozen=True)
class LayupCandidate:
    """Pressures in Pa for an explicit bottom-to-top physical ply sequence."""
    angles_deg: tuple[float, ...]
    first_ply_pressure_pa: float
    last_ply_pressure_pa: float
    fibre_limit_pressure_pa: float
    netting_pressure_pa: float | None
    first_ply_criterion: str
    first_ply_mode: str
    hashin_first_ply_pressure_pa: float

    @property
    def counts(self) -> tuple[tuple[float, int], ...]:
        return tuple((a, self.angles_deg.count(a)) for a in sorted(set(self.angles_deg)))

    @property
    def balanced(self) -> bool:
        return all(abs(a) in (0.0, 90.0) or self.angles_deg.count(a) == self.angles_deg.count(-a)
                   for a in set(self.angles_deg))


@dataclass(frozen=True)
class OptimisationResult:
    ranked: tuple[LayupCandidate, ...]
    objective: str
    search_method: str
    total_count_vectors: int
    seed: int
    radius_m: float
    n_plies: int
    ply_thickness_m: float
    netting_optimum_pressure_pa: float
    netting_reference: LayupCandidate | None
    progressive_assumptions: str

    @property
    def evaluated_count(self) -> int:
        return len(self.ranked)

    @property
    def top_layups(self) -> tuple[LayupCandidate, ...]:
        return self.ranked[:5]

    @property
    def exhaustive(self) -> bool:
        return self.evaluated_count == self.total_count_vectors

    def top_for(self, objective: str, limit: int = 5) -> tuple[LayupCandidate, ...]:
        _check_objective(objective)
        if isinstance(limit, bool) or not isinstance(limit, Integral) or limit < 1:
            raise ValueError("limit must be a positive integer")
        return tuple(sorted(self.ranked, key=lambda c: _rank_key(c, objective))[:limit])


def _check_objective(objective: str) -> None:
    if objective not in OBJECTIVES:
        raise ValueError(f"objective must be one of {OBJECTIVES}")


def _rank_key(candidate: LayupCandidate, objective: str) -> tuple:
    metric = {"first_ply": candidate.first_ply_pressure_pa,
              "last_ply": candidate.last_ply_pressure_pa,
              "fibre_limit": candidate.fibre_limit_pressure_pa}[objective]
    # Differences beyond 12 significant digits are numerical ties. Prefer a
    # balanced stack nearest the continuous single-angle reference, then angles.
    distance = sum((abs(a) - NETTING_ANGLE_DEG) ** 2 for a in candidate.angles_deg)
    return (-float(f"{metric:.12g}"), not candidate.balanced, distance, candidate.angles_deg)


def _symmetric(half: tuple, centre: tuple = ()) -> tuple:
    return half + centre + half[::-1]


def _compositions(total: int, bins: int, rng: random.Random) -> tuple[int, ...]:
    """Uniform weak composition via stars and bars, not biased angle draws."""
    bars = [-1, *sorted(rng.sample(range(total + bins - 1), bins - 1)), total + bins - 1]
    return tuple(bars[i + 1] - bars[i] - 1 for i in range(bins))


def _candidate_angles(angles: tuple, n: int, budget: int, seed: int) -> tuple[tuple, int, str]:
    half_size = n // 2
    centres = angles if n % 2 else (None,)
    total = math.comb(half_size + len(angles) - 1, len(angles) - 1) * len(centres)

    def exhaustive_sequences():
        for half in combinations_with_replacement(angles, half_size):
            for centre in centres:
                yield _symmetric(half, () if centre is None else (centre,))

    if total <= budget:
        return tuple(exhaustive_sequences()), total, "exhaustive symmetric count search"

    rng = random.Random(int(seed))
    candidates = {tuple([a] * n) for a in angles}
    pairs = [(a, -a) for a in angles if 0 < a < 90 and -a in angles]
    if n % 4 == 0:
        for pair in pairs:
            candidates.add(_symmetric(tuple(sorted(pair * (n // 4)))))
    if budget < len(candidates):
        raise ValueError(f"max_candidates must be at least {len(candidates)} to include the search anchors")
    if len(candidates) == budget:
        return tuple(sorted(candidates)), total, "anchored seeded symmetric count search"

    # Spend up to half the remaining budget on balanced, symmetric four-ply
    # blocks when the allowed angles and physical ply count permit them.
    blocks = [(a, a) for a in angles if abs(a) in (0.0, 90.0)] + pairs
    if n % 4 == 0 and blocks:
        block_count = n // 4
        balanced_total = math.comb(block_count + len(blocks) - 1, len(blocks) - 1)
        target = min(budget, len(candidates) + (budget - len(candidates)) // 2)
        if balanced_total <= target:
            for choice in combinations_with_replacement(range(len(blocks)), block_count):
                half = tuple(sorted(a for i in choice for a in blocks[i]))
                if len(candidates) < target:
                    candidates.add(_symmetric(half))
        else:
            for _ in range(20 * budget):
                counts = _compositions(block_count, len(blocks), rng)
                half = tuple(sorted(a for block, count in zip(blocks, counts) for _ in range(count) for a in block))
                candidates.add(_symmetric(half))
                if len(candidates) >= target:
                    break

    for _ in range(20 * budget):
        if len(candidates) >= budget:
            break
        counts = _compositions(half_size, len(angles), rng)
        half = tuple(a for a, count in zip(angles, counts) for _ in range(count))
        centre = (rng.choice(angles),) if n % 2 else ()
        candidates.add(_symmetric(half, centre))
        if len(candidates) >= budget:
            break
    # A bounded deterministic fallback avoids returning fewer candidates when
    # a nearly exhausted space produces repeated random draws.
    if len(candidates) < budget:
        for sequence in exhaustive_sequences():
            candidates.add(sequence)
            if len(candidates) >= budget:
                break
    return tuple(sorted(candidates)), total, "anchored seeded symmetric count search"


def _evaluate(sequence: tuple, thickness: float, material: dict, strengths: StrengthAllowables,
              radius: float, rules: DegradationRules) -> LayupCandidate:
    layup = [{"theta": a, "t": thickness, "mat": 0} for a in sequence]
    unit = cylinder_resultants(1.0, radius)
    first = first_ply_under_unit_load(layup, [material], [strengths], unit)
    progressive = progressive_failure(layup, [material], [strengths], unit, rules)
    fibre_strengths = [strengths.Xt] * len(layup)
    balanced = all(abs(a) in (0.0, 90.0) or sequence.count(a) == sequence.count(-a) for a in set(sequence))
    candidate = LayupCandidate(sequence, first.pressure_pa, progressive.last_ply_load_factor,
                              netting_bound(layup, fibre_strengths, radius),
                              netting_pressure(layup, fibre_strengths, radius) if balanced else None,
                              first.criterion, first.mode, progressive.first_ply_load_factor)
    if not all(math.isfinite(p) and p > 0 for p in (candidate.first_ply_pressure_pa,
                                                  candidate.last_ply_pressure_pa,
                                                  candidate.hashin_first_ply_pressure_pa)):
        raise ValueError("A candidate returned a non-finite or non-positive mechanical pressure")
    return candidate


def optimise_cylinder(radius_m: float, n_plies: int, ply_thickness_m: float,
                      material: dict, strengths: StrengthAllowables,
                      allowed_angles=DEFAULT_ANGLES, *, objective: str = "first_ply",
                      max_candidates: int = 128, seed: int = 2026,
                      rules: DegradationRules | None = None) -> OptimisationResult:
    """Rank evaluated symmetric cylinder walls at fixed mass; return top five.

    All candidate angles come from ``allowed_angles``; the continuous netting
    reference is separate and may be outside that set. All candidates receive
    both first-ply and last-ply evaluations, allowing ``top_for`` to rank either.
    ``max_candidates`` bounds evaluations, except for one optional netting
    reference. Single allowed angles and odd physical ply counts are supported.
    A balanced symmetric +/-netting reference requires a multiple of four plies.
    Material properties, strengths and discount rules are supplied, not inferred.
    Candidate exact netting pressures are reported only for balanced stacks:
    the existing axial/hoop netting solver does not enforce shear equilibrium
    for arbitrary unbalanced stacks. The projection bound remains an upper
    bound there, not an attainable fibre-only pressure. Ranking treats pressures
    equal to 12 significant digits as ties (balanced, nearest netting, angles).
    """
    _check_objective(objective)
    for name, value in (("radius_m", radius_m), ("ply_thickness_m", ply_thickness_m)):
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be positive and finite")
    for name, value in (("n_plies", n_plies), ("max_candidates", max_candidates)):
        if isinstance(value, bool) or not isinstance(value, Integral) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, Integral):
        raise ValueError("seed must be an integer")
    if not isinstance(strengths, StrengthAllowables):
        raise ValueError("strengths must be a StrengthAllowables record in Pa")
    raw_angles = tuple(allowed_angles)
    if not raw_angles or any(isinstance(a, bool) or not isinstance(a, Real)
                             or not math.isfinite(a) or not -90 <= a <= 90 for a in raw_angles):
        raise ValueError("allowed_angles must contain finite degree values in [-90, 90]")
    angles = tuple(sorted({float(a) for a in raw_angles}))
    sequences, total, method = _candidate_angles(angles, int(n_plies), int(max_candidates), int(seed))
    rules = rules or DegradationRules()
    candidates = tuple(_evaluate(s, ply_thickness_m, material, strengths, radius_m, rules) for s in sequences)
    reference = None
    if n_plies % 4 == 0:
        half = tuple(sorted((NETTING_ANGLE_DEG, -NETTING_ANGLE_DEG) * (n_plies // 4)))
        sequence = _symmetric(half)
        reference = next((c for c in candidates if c.angles_deg == sequence), None)
        if reference is None:
            reference = _evaluate(sequence, ply_thickness_m, material, strengths, radius_m, rules)
    return OptimisationResult(tuple(sorted(candidates, key=lambda c: _rank_key(c, objective))),
                              objective, method, total, int(seed), float(radius_m), int(n_plies),
                              float(ply_thickness_m), 2 * strengths.Xt * n_plies * ply_thickness_m / (3 * radius_m),
                              reference, rules.statement(strengths.St is None))
