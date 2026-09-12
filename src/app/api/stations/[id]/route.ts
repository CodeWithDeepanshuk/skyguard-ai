import { NextRequest, NextResponse } from 'next/server';
import { backendJSON, observedFeedStatus } from '@/server/backend';
import { readStationCatalog } from '@/server/stations';
export const dynamic = 'force-dynamic';
export async function GET(request: NextRequest, { params }: { params: { id: string } }) {
  const metadata = readStationCatalog().find(s => s.station_id === params.id);
  if (!metadata) return NextResponse.json({ error: 'Station not found' }, { status: 404 });
  try {
    const status = await observedFeedStatus();
    const raw = await backendJSON(`/api/live/readings?station_id=${encodeURIComponent(params.id)}&limit=80`);
    if (!Array.isArray(raw)) throw new Error('Invalid observation response.');
    const numeric = (v: unknown) => v === '' || v == null || !Number.isFinite(Number(v)) ? null : Number(v);
    const readings = raw.filter(r => r.station_id === params.id && r.observation_origin === 'aviationweather_metar')
      .map(r => ({ ...r, temperature_c: numeric(r.temperature_c), pressure_hpa: numeric(r.pressure_hpa),
        relative_humidity: numeric(r.relative_humidity_pct), decision: r.event_decision || 'UNVERIFIED',
        fault_probability: numeric(r.fault_probability), weather_probability: numeric(r.weather_probability),
      })).sort((a, b) => Date.parse(a.timestamp_utc) - Date.parse(b.timestamp_utc));
    return NextResponse.json({ station_id: params.id, metadata, source: 'aviationweather_metar',
      is_cached: status.is_cached, fetched_at_utc: status.fetched_at_utc, readings,
      message: readings.length ? 'Research-model outputs; not certified hardware diagnoses. RH is derived; pressure is QNH.' : 'No source observations for this catalog station.',
    });
  } catch (error) {
    return NextResponse.json({ station_id: params.id, metadata, source: 'unavailable', readings: [],
      message: error instanceof Error ? error.message : 'Live data unavailable.' });
  }
}
