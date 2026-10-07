"""Views of existing solver outputs, shared by charts, export and checks."""
import json
from pathlib import Path

import altair as alt
import pandas as pd

from ui_theme import MODE_COLOURS, mode_name


def validation_status():
    data = json.loads((Path(__file__).parent / "validation" / "data.json").read_text(encoding="utf-8"))
    if not data["_meta"]["strict_usable_cases"]:
        return ("Not validated against experiment. No like-for-like comparison is possible with the current cases: "
                "inner radius is not explicitly reported in the supplied research text; Type III liner load sharing is not modelled. "
                "Sources remain unverified against the original paper pages. See validation/README.md.")
    return "Experimental validation status needs review; usable input cases alone do not prove agreement. See validation/README.md."


def progressive_frames(result):
    pressures, strains = result.load_strain_curve(1)
    curve = pd.DataFrame({"strain": strains * 100, "pressure": pressures / 1e6})
    steps = {s.step: s for s in result.history}
    events = pd.DataFrame([
        {"Step": e.step, "Ply": e.ply, "Face": e.surface, "Mode": mode_name(e.mode),
         "pressure": e.load_factor / 1e6, "strain": float(steps[e.step].strain_before[1]) * 100,
         "Held pressure": steps[e.step].cascade}
        for e in sorted(result.events, key=lambda e: (e.step, e.ply, e.mode))
    ])
    return curve, events


def failure_event_chart(events):
    modes = [mode for mode in MODE_COLOURS if mode in set(events["Mode"])]
    return alt.Chart(events).mark_point(filled=True, size=90, stroke="white").encode(
        x=alt.X("strain:Q", title="Linear-model hoop strain εy [%]"),
        y=alt.Y("pressure:Q", title="Pressure [MPa]"),
        color=alt.Color("Mode:N", scale=alt.Scale(domain=modes, range=[MODE_COLOURS[mode] for mode in modes]),
                        legend=alt.Legend(title="Initiation mode", orient="bottom", columns=2, labelLimit=250)),
        tooltip=["Step", "Ply", "Face", "Mode", "Held pressure",
                 alt.Tooltip("strain:Q", title="εy [%]", format=".3f"),
                 alt.Tooltip("pressure:Q", title="Pressure [MPa]", format=".3f")])


def dome_edge_bands(frame):
    """Station cells where the existing membrane_valid flag is false."""
    radii = frame["r"].to_numpy()
    bands = []
    for i, valid in enumerate(frame["valid"]):
        if not valid:
            bands.append({"r0": float(radii[i] if i == 0 else (radii[i-1] + radii[i])/2),
                          "r1": float(radii[i] if i == len(radii)-1 else (radii[i] + radii[i+1])/2)})
    return pd.DataFrame(bands, columns=["r0", "r1"])
