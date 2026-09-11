"""Read-only 2022/2023 provenance and semantic audit; never opens test years."""
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from data.normalize_noaa_isd import normalize_file

stations = list(csv.DictReader((ROOT/'data/iteration10/config/india_stations.csv').open(encoding='utf-8-sig')))
manifest = list(csv.DictReader((ROOT/'data/iteration10/manifest/india_development_files.csv').open(encoding='utf-8-sig')))
files = []
quality = Counter()
switches = []
for station in stations:
    for year in (2022, 2023):
        path = ROOT/'data/raw/noaa'/str(year)/(station['station_id']+'.csv')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        matches = [r for r in manifest if r.get('sha256') == digest]
        files.append({'station':station['station_id'], 'year':year, 'sha256':digest, 'manifest_hash_match':bool(matches)})
        with path.open(encoding='utf-8-sig', newline='') as handle:
            for row in csv.DictReader(handle):
                for field in ('TMP','DEW','SLP'):
                    parts = row.get(field,'').split(',')
                    if len(parts)>1: quality[field+':'+parts[1]] += 1
        records = sorted(normalize_file(path, station, year).values(), key=lambda r:r['timestamp_utc'])
        sources = [r['pressure_source'] for r in records if r['pressure_source']]
        count = sum(a!=b for a,b in zip(sources,sources[1:]))
        switches.append({'station':station['station_id'],'year':year,'source_switches':count,'sources':dict(Counter(sources))})
report = {'scope':'2022-2023 only; read-only; no observations rewritten',
          'files_verified':len(files),'all_manifest_hashes_match':all(r['manifest_hash_match'] for r in files),
          'raw_quality_flag_counts':dict(quality),'pressure_source_switches':switches,
          'total_pressure_source_switches':sum(r['source_switches'] for r in switches),
          'files':files,
          'suitability':'conditional development proxy; derived RH, mixed pressure definitions, no real sensor-failure labels',
          'notebook_training_release':'BLOCKED pending pressure/QC handling and independent scientific evaluation'}
out=ROOT/'reports/TRAINING_CORRECTNESS_DATA_AUDIT.json'
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('files','pressure_source_switches')},indent=2))
