import { NextRequest, NextResponse } from 'next/server';
import { backendJSON } from '@/server/backend';
import { readStationCatalog } from '@/server/stations';

export const dynamic = 'force-dynamic';
export const revalidate = 0;
export const maxDuration = 60;

type StationRow = Record<string, unknown>;

function metadataOnly(row: StationRow): StationRow {
  return {
    ...row,
    latest_observation_utc: null,
    observation_age_minutes: null,
    latest_provider: null,
    provider_station_id: null,
    wigos_id: null,
    icao_code: row.icao || null,
    temperature_c: null,
    pressure_hpa: null,
    relative_humidity_pct: null,
    pressure_type: null,
    humidity_observation_type: null,
    source_quality_flags: [],
    observation_status: 'NOT_OBSERVED_IN_STORE',
    assessment_decision: 'INSUFFICIENT_CONTEXT',
    assessment_severity: null,
    anomaly_score: null,
    score_label: null,
    root_cause: null,
    neighbor_support: null,
    communication: null,
    health_status: 'NOT_OBSERVED_IN_STORE',
    catalog_only: true,
  };
}

function filterRows(rows: StationRow[], request: NextRequest): StationRow[] {
  const query = (request.nextUrl.searchParams.get('query') || '').trim().toLowerCase();
  const region = (request.nextUrl.searchParams.get('state') || '').trim().toLowerCase();
  const status = (request.nextUrl.searchParams.get('status') || '').trim().toLowerCase();

  return rows.filter(row => {
    const matchesQuery = !query || [row.station_name, row.station_id, row.provider_station_id, row.wigos_id, row.icao_code]
      .some(value => String(value || '').toLowerCase().includes(query));
    const matchesRegion = !region || [row.state, row.district, row.climate_zone, row.cluster]
      .some(value => String(value || '').toLowerCase().includes(region));
    const matchesStatus = !status || status === 'all' || String(row.health_status || '').toLowerCase() === status;
    return matchesQuery && matchesRegion && matchesStatus;
  });
}

export async function GET(request: NextRequest) {
  try {
    const payload = await backendJSON<{ stations?: StationRow[] }>('/api/v1/network/stations?limit=2000');
    if (!Array.isArray(payload.stations)) throw new Error('Invalid operational station response.');
    return NextResponse.json(filterRows(payload.stations, request), {
      headers: { 'x-skyguard-data-mode': 'operational-observation-store' },
    });
  } catch {
    const catalog = readStationCatalog().map(metadataOnly);
    return NextResponse.json(filterRows(catalog, request), {
      headers: {
        'x-skyguard-data-mode': 'metadata-only-catalog',
        'x-skyguard-warning': 'Observation service unavailable; telemetry and health are intentionally blank.',
      },
    });
  }
}
