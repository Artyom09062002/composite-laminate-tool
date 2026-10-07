"""R0 regression guard: every key number must equal tests/snapshot_v3.json.

The snapshot was taken from the final app (T300/5208 defaults) before any further work. A mismatch means a number
changed: either an unintended regression or a confirmed error fix, which must say so in the commit and regenerate the
file with ``python tests/snapshot_v3_values.py --write``. Tolerance: relative 1e-9, plus 1e-9 of the largest entry of the
same array and an absolute 1e-12 for entries that are numerically zero (e.g. B of a symmetric laminate).
"""
import json
import unittest

import numpy as np

try:
    from snapshot_v3_values import SNAPSHOT_PATH, compute
except ImportError:  # run from the project root without tests/ on the path
    from tests.snapshot_v3_values import SNAPSHOT_PATH, compute


# Entries that are exactly or numerically zero (B of a symmetric laminate, M_T, curvature) differ by round-off between
# platforms (about 1e-16); no non-zero quantity in the snapshot is smaller than 1e-6 in SI units.
ABS_NOISE = 1e-12


def _flatten(prefix, value, out):
    if isinstance(value, dict):
        for key, item in value.items():
            _flatten(f"{prefix}.{key}" if prefix else key, item, out)
    else:
        out[prefix] = value


class SnapshotV3Tests(unittest.TestCase):
    def test_snapshot_exists_and_has_every_block(self):
        self.assertTrue(SNAPSHOT_PATH.exists(), "tests/snapshot_v3.json is missing")
        stored = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        for block in ("laminate_example", "vessel", "dome", "thermal", "optimiser"):
            self.assertIn(block, stored)

    def test_all_numbers_are_identical_to_the_snapshot(self):
        stored = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        current = json.loads(json.dumps(compute()))  # same JSON round trip as the stored file
        flat_stored, flat_current = {}, {}
        _flatten("", stored, flat_stored)
        _flatten("", current, flat_current)
        self.assertEqual(sorted(flat_stored), sorted(flat_current), "snapshot keys changed")
        checked = 0
        for key, expected in flat_stored.items():
            actual = flat_current[key]
            if isinstance(expected, list):
                e, a = np.asarray(expected, dtype=object), np.asarray(actual, dtype=object)
                self.assertEqual(e.shape, a.shape, key)
                if e.size and isinstance(e.flat[0], (int, float)):
                    ef, af = e.astype(float), a.astype(float)
                    scale = float(np.max(np.abs(ef))) if ef.size else 0.0
                    np.testing.assert_allclose(af, ef, rtol=1e-9, atol=1e-9 * scale + ABS_NOISE, err_msg=key)
                    checked += ef.size
                else:
                    self.assertEqual(expected, actual, key)
            elif isinstance(expected, float) or (isinstance(expected, int) and not isinstance(expected, bool)
                                                 and isinstance(actual, float)):
                self.assertTrue(np.isclose(actual, expected, rtol=1e-9, atol=0.0), f"{key}: {actual!r} != {expected!r}")
                checked += 1
            else:
                self.assertEqual(expected, actual, key)
                checked += 1
        self.assertGreater(checked, 150)


if __name__ == "__main__":
    unittest.main()
