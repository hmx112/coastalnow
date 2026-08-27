from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
L=json.loads((ROOT/'data'/'locations.json').read_text())
print(f'{len(L)} locations loaded; next step is NOAA station mapping and scheduled data fetch.')
