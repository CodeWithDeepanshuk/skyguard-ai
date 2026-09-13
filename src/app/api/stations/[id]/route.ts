import { NextRequest, NextResponse } from 'next/server';
import { backendJSON } from '@/server/backend';
import { readStationCatalog } from '@/server/stations';

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

export async function GET(request: NextRequest, { params }: { params: { id: string } }) {
  const metadata = readStationCatalog().find(station => station.station_id === params.id);
  if (!metadata) return NextResponse.json({ error: 'Station not found' }, { status: 404 });
  try {
    const hours = Math.min(720, Math.max(1, Number(request.nextUrl.searchParams.get('hours')) || 24));
    const payload = await backendJSON(`/api/v1/operational/stations/${encodeURIComponent(params.id)}?hours=${hours}`);
    return NextResponse.json(payload, {
      headers: { 'x-skyguard-data-mode': 'operational-observation-store' },
    });
  } catch (error) {
    return NextResponse.json({
      metadata,
      latest: null,
      history: [],
      neighbors: [],
      assessment: null,
      communication: null,
      source: 'unavailable',
      message: error instanceof Error ? error.message : 'Operational observations are unavailable.',
    }, { status: 503 });
  }
}
