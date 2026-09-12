import { NextRequest, NextResponse } from 'next/server';
export const dynamic = 'force-dynamic';
export async function POST(request: NextRequest) {
  let body;
  try { body = await request.json(); }
  catch { return NextResponse.json({ error: 'Invalid JSON payload' }, { status: 400 }); }
  if (!body || typeof body.station_id !== 'string' ||
      !['temperature', 'pressure', 'humidity'].every(k => typeof body[k] === 'number' && Number.isFinite(body[k])))
    return NextResponse.json({ error: 'Provide station_id and three finite numeric measurements.' }, { status: 422 });
  // The deployed model uses ordered source histories. No single-row Python
  // inference endpoint exists; thresholds are not a calibrated substitute.
  return NextResponse.json({ status: 'unavailable', error:
    'Single-reading inference is not deployed. Open a station to view observed METAR history and research-model output. No probability or neighbour evidence has been invented.'
  }, { status: 503 });
}
