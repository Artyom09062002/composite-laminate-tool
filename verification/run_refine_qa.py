"""Reproduce the full source-controlled suite and record export footer evidence."""
import json
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
with (ROOT / 'verification' / 'qa_test_log.txt').open('w', encoding='utf-8') as log:
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
record = {'date': datetime.now(timezone(timedelta(hours=5))).date().isoformat(),
          'command': 'python -m unittest discover -s tests -v',
          'tests_run': result.testsRun, 'failures': len(result.failures),
          'errors': len(result.errors), 'skipped': len(result.skipped),
          'successful': result.wasSuccessful(),
          'scope': 'Numerical checks, unchanged v3 snapshot, AppTest presets, input boundaries, chart arrays and one-page PDF values.'}
(ROOT / 'verification' / 'qa_results.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
print(json.dumps(record))
sys.exit(0 if result.wasSuccessful() and not result.skipped else 1)
