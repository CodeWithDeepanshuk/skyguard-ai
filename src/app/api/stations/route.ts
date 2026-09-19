import { NextRequest, NextResponse } from 'next/server';
import { getEnrichedStations } from '@/server/liveData';

export const dynamic = 'force-dynamic';
export const revalidate = 0;
export const maxDuration = 60;

export async function GET(request: NextRequest) {
  try {
    const query = request.nextUrl.searchParams.get('query') || undefined;
    const state = request.nextUrl.searchParams.get('state') || undefined;
    const status = request.nextUrl.searchParams.get('status') || undefined;

    const stations = await getEnrichedStations({ query, state, status });

    return NextResponse.json(stations, {
      headers: {
        'x-skyguard-data-mode': 'operational-observation-store',
        'Cache-Control': 'no-store, max-age=0',
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Observation service unavailable.' },
      { status: 500 }
    );
  }
}
