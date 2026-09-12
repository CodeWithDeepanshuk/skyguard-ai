import fs from 'fs';
import path from 'path';
export function readStationCatalog(): Array<Record<string, any>> {
  const file = path.join(process.cwd(), 'config', 'all_india_aws_network.csv');
  if (!fs.existsSync(file)) return [];
  const text = fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, '');
  const rows: string[][] = [];
  let row: string[] = [], field = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
      if (quoted && text[i + 1] === '"') { field += '"'; i++; }
      else quoted = !quoted;
    } else if (!quoted && (c === ',' || c === '\n')) {
      row.push(field.replace(/\r$/, '')); field = '';
      if (c === '\n') { if (row.some(Boolean)) rows.push(row); row = []; }
    } else field += c;
  }
  if (field || row.length) { row.push(field.replace(/\r$/, '')); rows.push(row); }
  const headers = rows.shift() || [];
  const flag = (v: string) => ['1', 'true'].includes((v || '').toLowerCase());
  return rows.map(cols => {
    const r = Object.fromEntries(headers.map((h, i) => [h, cols[i] || '']));
    return { ...r, station_id: r.station_id, station_name: r.station_name || r.station_id,
      latitude: Number(r.latitude), longitude: Number(r.longitude), elevation_m: Number(r.elevation_m),
      is_benchmark: flag(r.is_benchmark), is_active_2024_plus: flag(r.is_active_2024_plus),
      status: 'UNVERIFIED', catalog_only: true };
  });
}
