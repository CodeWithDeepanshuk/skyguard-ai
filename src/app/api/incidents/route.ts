import { NextRequest, NextResponse } from 'next/server';
import { backendJSON } from '@/server/backend';

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

export async function GET(request: NextRequest) {
  try {
    const limit = Math.min(500, Math.max(1, Number(request.nextUrl.searchParams.get('limit')) || 100));
    const payload = await backendJSON<{ incidents?: unknown[] }>(`/api/v1/operational/incidents?limit=${limit}`);
    if (!Array.isArray(payload.incidents)) throw new Error('Invalid operational incident response.');
    return NextResponse.json(payload.incidents, {
      headers: { 'x-skyguard-data-mode': 'operational-observation-store' },
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Operational incidents unavailable.' },
      { status: 503 },
    );
  }
}
