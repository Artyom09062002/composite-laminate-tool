"""Wind-blade spar-cap example: an unsymmetric two-layer equivalent panel.

Material data: Griffith & Ashwill, "The Sandia 100-meter All-glass Baseline Wind
Turbine Blade: SNL100-00", Sandia report SAND2011-3779 (2011), Table 19
(SNL Triax and E-LT-5500/EP-3 unidirectional glass). The layer thicknesses are an
illustrative equivalent section, not a manufacturing ply book.
"""
from core import assemble_laminate_stiffness

TRIAX_GFRP = {"E1": 27.7e9, "E2": 13.65e9, "G12": 7.20e9, "v12": 0.39}  # SNL Triax [±45]2[0]2
UD_GFRP = {"E1": 41.8e9, "E2": 14.0e9, "G12": 2.63e9, "v12": 0.28}     # E-LT-5500/EP-3 [0]2
SKIN_THICKNESS_M = 0.003
CAP_THICKNESS_M = 0.065
MATERIAL_SOURCE = "Griffith & Ashwill, Sandia report SAND2011-3779 (SNL100-00 blade), Table 19"


def analyze_spar_cap():
    """Return the layup and laminate stiffness of the skin + cap equivalent panel."""
    layup = [{"theta": 0.0, "t": SKIN_THICKNESS_M, "mat": 0},
             {"theta": 0.0, "t": CAP_THICKNESS_M, "mat": 1}]
    return layup, assemble_laminate_stiffness(layup, [TRIAX_GFRP, UD_GFRP])
