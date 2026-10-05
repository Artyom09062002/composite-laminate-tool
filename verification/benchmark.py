"""Reproducible reference values (graphite/epoxy Q, glass/epoxy Q-bar at 30 deg) for the audit notes."""
from pathlib import Path
import json
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import compute_Q_matrix, transform_Q

def results():
    q = compute_Q_matrix(181e9, 10.3e9, 7.17e9, 0.28)
    glass_q = compute_Q_matrix(38.6e9, 8.27e9, 4.14e9, 0.26)
    qbar = transform_Q(glass_q, 30.0)
    return {
        "graphite_epoxy_q_gpa": np.round(q / 1e9, 6).tolist(),
        "glass_epoxy_30deg_qbar_gpa": np.round(qbar / 1e9, 6).tolist(),
        "units": "GPa",
    }

if __name__ == "__main__":
    output = ROOT / "verification" / "benchmark_results.json"
    output.write_text(json.dumps(results(), indent=2) + "\n", encoding="utf-8")
    print(output)
