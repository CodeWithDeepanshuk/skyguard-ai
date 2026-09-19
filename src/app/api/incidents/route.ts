import { NextRequest, NextResponse } from 'next/server';
import { getOperationalIncidents } from '@/server/liveData';

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

export async function GET(request: NextRequest) {
  try {
    const limit = Math.min(500, Math.max(1, Number(request.nextUrl.searchParams.get('limit')) || 100));
    const incidents = await getOperationalIncidents(limit);

    return NextResponse.json(incidents, {
      headers: {
        'x-skyguard-data-mode': 'operational-observation-store',
        'Cache-Control': 'no-store, max-age=0',
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Operational incidents unavailable.' },
      { status: 500 }
    );
  }
}
