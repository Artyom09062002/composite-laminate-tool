"""Shared presentation conventions; no mechanics or material data."""

APP_VERSION = "v4-refine"
STATUS_BADGES_HTML = ('<div style="display:flex;gap:8px;flex-wrap:wrap;margin:8px 0">'
    '<span style="background:#eef5f7;border:1px solid #c9d8de;border-radius:20px;padding:4px 10px">Checked by tests · recorded suite</span>'
    '<span style="background:#eef5f7;border:1px solid #c9d8de;border-radius:20px;padding:4px 10px">Model assumption · see limits</span>'
    '<span style="background:#fff5d8;border:1px solid #c9d8de;border-radius:20px;padding:4px 10px">Not validated against experiment</span></div>')
PALETTE = {"ink": "#173042", "teal": "#087f8c", "grid": "#c9d8de",
           "shade": "#eef5f7", "first": "#e07b22", "last": "#7b3fa0"}
MODE_COLOURS = {"Fibre tension": "#2563a6", "Fibre compression": "#7145a0",
                "Matrix tension": "#d47718", "Matrix compression": "#16866d",
                "Shear": "#a94a63", "Shear-dominated fibre tension": "#a94a63",
                "Fibre": "#54677b", "Matrix": "#80735c"}


def mode_name(mode):
    return str(mode).replace("_", " ").capitalize()


def mode_style(value):
    colour = MODE_COLOURS.get(mode_name(value))
    return f"background-color: {colour}; color: white" if colour else ""


GLOSSARY = {
    "Lamina / ply": "One fibre-reinforced layer, with its own angle and thickness.",
    "Layup": "The ordered ply list, from the bottom face to the top face.",
    "Q / Q-bar": "Ply stiffness in fibre axes / rotated into laminate axes.",
    "A, B, D": "Extension, extension-bending coupling and bending stiffness matrices.",
    "Resultant": "Force or moment per unit width, obtained by integrating stress through thickness.",
    "Microstrain (µε)": "One millionth of unit strain; 1000 µε is 0.1% extension.",
    "Symmetric": "Matching plies mirrored about the mid-plane; B vanishes in this CLT model.",
    "Balanced": "Equal thickness of +θ and −θ plies of the same material.",
    "First-ply": "The first calculated initiation limit reached by a ply face.",
    "Last-ply (model stop)": "The stopping pressure of the assumed residual-stiffness algorithm.",
    "Strength ratio R": "The proportional load multiplier at which a chosen criterion reaches 1.",
    "Netting": "A fibre-only equilibrium reference; matrix and liner load sharing are omitted.",
    "Residual thermal stress": "Stress remaining after temperature change because bonded plies cannot expand independently.",
    "Stress-free temperature": "An assumed common reference at which this assembled laminate has no thermal stress.",
    "Geodesic": "The ideal dome winding path satisfying r sin(α) = opening radius.",
}

STYLE_CSS = '\n<style>\n  .block-container {max-width: 1360px; padding-top: 1.45rem; padding-bottom: 3rem;}\n  .hero {background: linear-gradient(120deg, #102a43, #075f70); color: white;\n    padding: 1.8rem 2rem; border-radius: 1.1rem; margin-bottom: 1.3rem;}\n  .hero .eyebrow {font-size: .76rem; letter-spacing: .15em; font-weight: 700;\n    color: #9fe1e7; margin-bottom: .55rem;}\n  .hero h1 {color: white; font-size: clamp(2rem, 3.4vw, 3rem); line-height: 1.08;\n    margin: 0 0 .7rem 0;}\n  .hero p {color: #e5f3f5; font-size: 1.04rem; max-width: 66rem; margin: 0;}\n  [data-testid="stMetric"] {background: white; border: 1px solid #dce9ee;\n    border-radius: .9rem; padding: .85rem 1rem; box-shadow: 0 5px 18px #102a4309;}\n  .stTabs [data-baseweb="tab-list"] {gap: .35rem; padding-bottom: .4rem;}\n  .stTabs [data-baseweb="tab"] {border-radius: .65rem .65rem 0 0; padding: .65rem .8rem;}\n  [data-testid="stSidebar"] {min-width: 330px;}\n</style>\n'

PALETTE.update({'response': '#3b6fb6', 'first': '#e07b22', 'last': '#7b3fa0', 'teal': '#087f8c', 'muted': '#5b7080', 'working': '#c0392b', 'excluded': '#9db4d6', 'edge': '#80735c', 'stress1': '#1f77b4', 'stress3': '#2a9d5c'})
