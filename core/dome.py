"""Geodesic dome winding of a filament-wound pressure vessel: angle, thickness, membrane loads.

Angle convention
----------------
The winding angle alpha is measured from the MERIDIAN: the vessel axis on the cylinder and the
local meridional tangent on the dome. alpha = 0 is a fibre along the meridian, alpha = 90 deg a
fibre along the parallel circle (hoop). This is the convention of the rest of the app (local x =
axis/meridian, local y = hoop, 90 deg = hoop winding), so the plies of a dome station go to the
CLT code unchanged, and the station load vector is [N_phi, N_theta, 0, 0, 0, 0] in (x, y) order.

Symbols (SI: m, N/m, Pa; angles in degrees at the interface)
    R       cylinder radius = equatorial radius of the dome
    r0      polar opening radius (0 < r0 < R) = radius of the turnaround circle of the geodesic;
            r  radius of the parallel circle (r0 <= r <= R). The dome is truncated at r0: it has a
            polar OPENING (boss), not a geometric pole. r0 = 0 is excluded (Clairaut degenerates).
    alpha0  winding angle on the cylinder;  alpha(r)  winding angle on the dome
    k = b/R dome aspect ratio: dome depth b (semi-axis along the axis) over R.
            k = 1 hemisphere, k = 0.5 the "2:1" ellipsoidal head
    r1      meridional radius of curvature of the dome surface
    r2      circumferential radius of curvature = length of the surface normal from the surface
            to the axis of revolution (r2 = r / sin(phi), phi = angle between normal and axis)
    N_phi   meridional membrane resultant;  N_theta  circumferential (hoop) membrane resultant

Equations
---------
Geodesic path (Clairaut, valid on every surface of revolution, so independent of the dome shape):
    r sin(alpha) = r0   ->   alpha0 = asin(r0 / R),   alpha = 90 deg at r = r0.
No fibre reaches r < r0.

Thickness build-up for a constant fibre band width and fibre volume (per ply, so the whole wall):
    t(r) = t_cyl R cos(alpha0) / (r cos(alpha)) = t_cyl sqrt((R^2 - r0^2) / (r^2 - r0^2)),
which grows monotonically toward the polar opening and is infinite at r = r0.

Membrane equilibrium of a shell of revolution under internal pressure p, CLOSED by a pressure-tight boss:
    N_phi = p r2 / 2,    N_theta = p r2 (1 - r2 / (2 r1)).
N_phi comes from the axial balance of the cap beyond a parallel circle r, 2 pi r N_phi sin(phi) = p pi r^2, with the
pressure acting on the whole projected disc. For a dome truncated at r0 this holds only if the boss/liner seals the
opening and passes the axial reaction p pi r0^2 into the shell edge at r = r0 (the model assumes so). With an open
pole, or another axial reaction at the boss, N_phi gets an edge-force term (dF / (2 pi r sin(phi))) that is NOT modelled.
Hemisphere (r1 = r2 = R): N_phi = N_theta = pR/2. Cylinder (r1 -> infinity): pR/2 and pR.
Ellipsoid, parametrised by r = R cos(t), z = b sin(t), with Q = R^2 sin^2(t) + b^2 cos^2(t):
    r2 = R sqrt(Q) / b,   r1 = Q^(3/2) / (R b).
For k < 1/sqrt(2) the hoop resultant N_theta is compressive near the equator (membrane theory).

Where the membrane + CLT numbers are NOT a strength prediction
----------------------------------------------------------------
The thickness law diverges at r0 and N_theta jumps at the cylinder/dome junction (the curvature jumps); both are
artefacts of the idealisation, resolved in a real part by bending/shear boundary layers (junction) and by finite tow
width, boss and slip (opening). The stations are still computed, but ``DomeStations.membrane_valid`` is False within one
bending decay length of either edge (``bending_zone_length_m``: pi / beta, beta = (3 (1 - nu^2))^(1/4) / sqrt(R h), an
isotropic thin-shell ORDER-OF-MAGNITUDE estimate with nu = 0.3 and the cylinder wall thickness h, which understates the
zone at the opening where the wall is thicker). Strength headlines must use ``weakest_valid_index``; a first-ply value at
a flagged station needs a shell-bending or finite-element transition analysis before it can be quoted.

Model limits (simplifications)
------------------------------
Only helical plies are modelled: hoop plies are not geodesic and are assumed to end at the
cylinder/dome junction. No fibre slippage (stability of the geodesic path under friction is not
checked). Constant band width and constant fibre volume fraction, hence the thickness
singularity at r0 (real parts have finite bands, a boss and slip). Membrane theory only: no
bending, and N_theta jumps at the cylinder/dome junction unless r1 -> infinity. No liner,
boss or openings reinforcement. The isotensoid dome profile is not implemented.

Reference: e.g. Peters (ed.), "Composite Filament Winding", ASM International (2011);
Vasiliev, "Composite Pressure Vessels", Bull Ridge (2009); any text on shells of revolution.
"""
from dataclasses import dataclass
import math

import numpy as np

from .vessel import first_ply_under_unit_load


def _check_radii(r0: float, radius_m: float) -> None:
    if not (math.isfinite(radius_m) and radius_m > 0):
        raise ValueError("Cylinder radius R must be positive and finite")
    if not (math.isfinite(r0) and 0 < r0 < radius_m):
        raise ValueError("Polar opening radius must satisfy 0 < r0 < R")


def clairaut_angle_deg(r: float, r0: float) -> float:
    """Geodesic winding angle [deg, from the meridian] at parallel radius r: sin(alpha) = r0 / r."""
    if not (math.isfinite(r) and math.isfinite(r0) and r0 > 0):
        raise ValueError("r and the polar opening radius r0 must be finite, with r0 > 0")
    if r < r0:
        raise ValueError(f"r = {r:g} m lies inside the polar opening r0 = {r0:g} m: no fibre reaches it")
    return math.degrees(math.asin(r0 / r))


def cylinder_winding_angle_deg(r0: float, radius_m: float) -> float:
    """Winding angle on the cylinder, alpha0 = asin(r0 / R) [deg]."""
    _check_radii(r0, radius_m)
    return clairaut_angle_deg(radius_m, r0)


def _cos_alpha(r: float, r0: float) -> float:
    """cos(alpha) = sqrt(1 - (r0/r)^2), exactly zero at r = r0 (no round-off from cos(pi/2))."""
    return math.sqrt(max(0.0, 1.0 - (r0 / r) ** 2))


def bending_zone_length_m(radius_m: float, thickness_m: float, poisson_ratio: float = 0.3) -> float:
    """Meridional decay length pi / beta of shell-bending edge effects, beta = (3 (1 - nu^2))^(1/4) / sqrt(R h) [m].

    Isotropic thin-shell estimate (Timoshenko & Woinowsky-Krieger); for an orthotropic helical wall it is an
    order-of-magnitude indicator only, which is why nu is an input and not derived from the laminate.
    """
    if not (math.isfinite(radius_m) and radius_m > 0 and math.isfinite(thickness_m) and thickness_m > 0):
        raise ValueError("Radius and thickness must be positive and finite")
    if not (math.isfinite(poisson_ratio) and -1.0 < poisson_ratio < 1.0):
        raise ValueError("Poisson's ratio must lie in (-1, 1)")
    beta = (3.0 * (1.0 - poisson_ratio ** 2)) ** 0.25 / math.sqrt(radius_m * thickness_m)
    return math.pi / beta


def meridian_arc_length_m(r, radius_m: float, aspect_ratio: float) -> np.ndarray:
    """Meridional arc length [m] from the junction (r = R) to parallel radius ``r`` on the ellipsoidal dome.

    With r = R cos(t), z = b sin(t): ds = sqrt(R^2 sin^2 t + b^2 cos^2 t) dt (trapezoid rule, 4000 intervals).
    """
    if not (math.isfinite(radius_m) and radius_m > 0 and math.isfinite(aspect_ratio) and aspect_ratio > 0):
        raise ValueError("Radius and aspect ratio must be positive and finite")
    radii = np.atleast_1d(np.asarray(r, dtype=float))
    if not (np.all(np.isfinite(radii)) and np.all(radii > 0) and np.all(radii <= radius_m)):
        raise ValueError("r must satisfy 0 < r <= R")
    depth = aspect_ratio * radius_m
    t_end = np.arccos(np.clip(radii / radius_m, -1.0, 1.0))
    grid = np.linspace(0.0, float(t_end.max()), 4001)
    speed = np.sqrt(radius_m ** 2 * np.sin(grid) ** 2 + depth ** 2 * np.cos(grid) ** 2)
    cumulative = np.concatenate(([0.0], np.cumsum(0.5 * (speed[1:] + speed[:-1]) * np.diff(grid))))
    return np.interp(t_end, grid, cumulative)


def thickness_factor(r: float, r0: float, radius_m: float) -> float:
    """t(r) / t_cyl = R cos(alpha0) / (r cos(alpha)); infinite at r = r0, 1 at r = R."""
    _check_radii(r0, radius_m)
    clairaut_angle_deg(r, r0)  # rejects r < r0
    if r > radius_m:
        raise ValueError("r must not exceed the cylinder radius R on the dome")
    cos_a = _cos_alpha(r, r0)
    if cos_a == 0.0:
        return math.inf
    return radius_m * _cos_alpha(radius_m, r0) / (r * cos_a)


def ellipsoid_dome_geometry(r: float, radius_m: float, aspect_ratio: float) -> tuple[float, float, float]:
    """``(z, r1, r2)`` at parallel radius r of a dome with equatorial radius R and depth b = k R.

    z is the axial distance from the cylinder/dome junction [m]; r1 and r2 are the meridional and
    circumferential radii of curvature [m]. ``aspect_ratio`` k = 1 is a hemisphere.
    """
    if not (math.isfinite(aspect_ratio) and aspect_ratio > 0):
        raise ValueError("Aspect ratio b/R must be positive and finite")
    if not (math.isfinite(radius_m) and radius_m > 0):
        raise ValueError("Cylinder radius R must be positive and finite")
    if not (math.isfinite(r) and 0 < r <= radius_m):
        raise ValueError("r must satisfy 0 < r <= R")
    depth = aspect_ratio * radius_m
    rho = r / radius_m
    q = radius_m ** 2 * (1.0 - rho ** 2) + depth ** 2 * rho ** 2
    z = depth * math.sqrt(max(0.0, 1.0 - rho ** 2))
    return z, q ** 1.5 / (radius_m * depth), radius_m * math.sqrt(q) / depth


def dome_resultants(pressure_pa: float, r1: float, r2: float) -> np.ndarray:
    """Load vector [N_phi, N_theta, 0, 0, 0, 0] [N/m] of a closed dome under internal pressure.

    N_phi = p r2 / 2 and N_theta = p r2 (1 - r2 / (2 r1)); ``r1 = math.inf`` gives the cylinder.
    """
    if not (r1 > 0 and r2 > 0 and math.isfinite(r2)):
        raise ValueError("Radii of curvature must be positive (r1 may be infinite for a cylinder)")
    return np.array([pressure_pa * r2 / 2.0, pressure_pa * r2 * (1.0 - r2 / (2.0 * r1)), 0.0, 0.0, 0.0, 0.0])


@dataclass(frozen=True)
class DomeStations:
    """Dome results at parallel radii running from the cylinder (r = R) toward the polar opening.

    ``n_phi`` and ``n_theta`` are the membrane resultants [N/m] at ``pressure_pa`` (per unit
    pressure when it is 1 Pa). ``thickness_m`` is the total wall thickness at each station and
    ``first_ply_pressure_pa`` the pressure at which the first ply of that station's wall fails.
    """
    alpha0_deg: float
    radius_m: np.ndarray
    axial_m: np.ndarray
    alpha_deg: np.ndarray
    thickness_ratio: np.ndarray
    thickness_m: np.ndarray
    r1_m: np.ndarray
    r2_m: np.ndarray
    n_phi: np.ndarray
    n_theta: np.ndarray
    first_ply_pressure_pa: np.ndarray
    first_ply_mode: tuple[str, ...]
    first_ply_ply: tuple[int, ...]
    arc_m: np.ndarray               # meridional arc length from the junction [m]
    membrane_valid: np.ndarray      # False within one bending decay length of the junction or of the opening
    bending_zone_m: float           # that decay length [m] (order-of-magnitude estimate, see module docstring)

    def weakest_valid_index(self) -> int | None:
        """Index of the lowest first-ply pressure among ``membrane_valid`` stations (None if there is none)."""
        valid = np.flatnonzero(self.membrane_valid)
        if valid.size == 0:
            return None
        return int(valid[np.argmin(self.first_ply_pressure_pa[valid])])


def dome_wall(layup: list[dict], alpha_deg: float, thickness_scale: float) -> list[dict]:
    """The cylinder wall ``layup`` carried onto the dome: every ply keeps its sign and material,
    its angle magnitude becomes ``alpha_deg`` and its thickness is multiplied by ``thickness_scale``."""
    return [{"theta": math.copysign(alpha_deg, ply["theta"]), "t": ply["t"] * thickness_scale, "mat": ply["mat"]}
            for ply in layup]


def dome_stations(layup: list[dict], materials: list[dict], strengths, r0: float, radius_m: float,
                  aspect_ratio: float = 1.0, n_stations: int = 41, r_end_ratio: float = 1.02,
                  pressure_pa: float = 1.0, zone_poisson_ratio: float = 0.3) -> DomeStations:
    """Winding angle, thickness, membrane resultants and first-ply pressure along a geodesic dome.

    ``layup`` is the helical wall on the CYLINDER (same ply dicts and material indexing as the
    rest of the app): every ply must be at +/-alpha0 with alpha0 = asin(r0/R), which makes the
    cylinder wall the r = R end of the dome (build it with ``angle_ply_wall(alpha0, ...)``).
    Stations run from r = R down to ``r_end_ratio * r0`` (just outside the singular opening,
    where the model thickness is infinite). Each station reuses the cylinder first-ply code
    (``first_ply_under_unit_load``) with that station's angle, thickness and resultants.
    ``membrane_valid`` marks the stations that are not within one bending decay length of the junction
    or of the opening (see the module docstring); the others are computed but are not strength predictions.
    """
    _check_radii(r0, radius_m)
    if not layup:
        raise ValueError("The layup must contain at least one ply")
    if not (isinstance(n_stations, int) and n_stations >= 2):
        raise ValueError("n_stations must be an integer of at least 2")
    if not (math.isfinite(r_end_ratio) and r_end_ratio > 1.0 and r_end_ratio * r0 < radius_m):
        raise ValueError("r_end_ratio must exceed 1 and keep the last station inside r0 < r < R")
    alpha0 = cylinder_winding_angle_deg(r0, radius_m)
    for index, ply in enumerate(layup, start=1):
        if abs(abs(ply["theta"]) - alpha0) > 1e-6:
            raise ValueError(f"Ply {index} is at {ply['theta']:g} deg; geodesic winding with r0/R = {r0 / radius_m:g} "
                             f"requires every ply at +/-{alpha0:.6f} deg")
    cylinder_thickness = sum(float(ply["t"]) for ply in layup)
    radii = np.linspace(radius_m, r_end_ratio * r0, n_stations)
    rows = []
    for r in radii:
        r = float(r)
        alpha = clairaut_angle_deg(r, r0)
        scale = thickness_factor(r, r0, radius_m)
        z, r1, r2 = ellipsoid_dome_geometry(r, radius_m, aspect_ratio)
        unit = dome_resultants(1.0, r1, r2)
        first_ply = first_ply_under_unit_load(dome_wall(layup, alpha, scale), materials, strengths, unit)
        rows.append((alpha, scale, z, r1, r2, unit, first_ply))
    ratio = np.array([row[1] for row in rows])
    arc = meridian_arc_length_m(radii, radius_m, aspect_ratio)
    total_arc = float(meridian_arc_length_m(r0, radius_m, aspect_ratio)[0])
    zone = bending_zone_length_m(radius_m, cylinder_thickness, zone_poisson_ratio)
    return DomeStations(
        alpha0_deg=alpha0, radius_m=radii,
        axial_m=np.array([row[2] for row in rows]),
        alpha_deg=np.array([row[0] for row in rows]),
        thickness_ratio=ratio, thickness_m=cylinder_thickness * ratio,
        r1_m=np.array([row[3] for row in rows]), r2_m=np.array([row[4] for row in rows]),
        n_phi=np.array([row[5][0] for row in rows]) * pressure_pa,
        n_theta=np.array([row[5][1] for row in rows]) * pressure_pa,
        first_ply_pressure_pa=np.array([row[6].pressure_pa for row in rows]),
        first_ply_mode=tuple(row[6].mode for row in rows),
        first_ply_ply=tuple(row[6].ply for row in rows),
        arc_m=arc, membrane_valid=(arc >= zone) & (total_arc - arc >= zone), bending_zone_m=zone,
    )
