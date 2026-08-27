#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
script = ROOT / 'src' / 'update_san_diego.py'
preview = ROOT / 'preview' / 'san-diego-integrated-preview.html'
subprocess.run([sys.executable, str(script), '--preview'], check=True)
html = preview.read_text(encoding='utf-8')
checks = {
    'high countdown': 'High tide in 2h 18m' in html,
    'low countdown': 'Low tide in 6h 57m' in html,
    'rising status': 'Tide is rising now ↑' in html,
    'seven desktop days': html.count('<tr><td class="day">') == 7,
    'mobile collapse': 'id="moreForecast" class="more-forecast" hidden' in html,
    'toggle button': 'Show all 7 days' in html,
    'no template placeholders': '{{' not in html,
    'preview warning': 'Technical preview:' in html,
}
for name, ok in checks.items():
    print(('PASS' if ok else 'FAIL'), name)
if not all(checks.values()):
    raise SystemExit(1)
