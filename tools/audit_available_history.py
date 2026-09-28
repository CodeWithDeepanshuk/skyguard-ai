"""Inventory local 2022–2024 training inputs without changing observations."""
import hashlib
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'data/archive/legacy_noaa_aws/aws_observations_2022_2024.csv.gz'
df = pd.read_csv(path, dtype={'station_id': str}, low_memory=False)
t = pd.to_datetime(df.timestamp_utc, utc=True, errors='coerce')
channels = ['temperature_c', 'pressure_hpa', 'relative_humidity_pct']
report = {
    'path': str(path.relative_to(ROOT)),
    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'rows': len(df), 'stations': int(df.station_id.nunique()),
    'start': str(t.min()), 'end': str(t.max()),
    'invalid_timestamps': int(t.isna().sum()),
    'duplicate_station_times': int(pd.DataFrame({'station': df.station_id, 'time': t}).duplicated().sum()),
    'years': {str(y): {'rows': int(t.dt.year.eq(y).sum()),
                       'stations': int(df.loc[t.dt.year.eq(y), 'station_id'].nunique()),
                       'raw_csv_files': len(list((ROOT / f'data/raw/noaa/{y}').glob('*.csv')))}
              for y in [2022, 2023, 2024]},
    'missing': {c: int(df[c].isna().sum()) for c in channels},
    'pressure_sources': df.pressure_source.fillna('MISSING').value_counts().to_dict(),
    'evaluation_roles': df.evaluation_role.value_counts().to_dict(),
    'sources': df.source.value_counts().to_dict(),
    'limitations': [
        'NOAA/NCEI Indian surface-station archive; not direct IMD AWS API history.',
        'SLP and MA1 altimeter are different pressure quantities and must not be mixed.',
        'No maintenance-confirmed fault labels in this archive.',
        'Raw file counts do not establish usable station coverage before parsing.'
    ],
}
out = ROOT / 'artifacts/history_audit_2022_2024.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
