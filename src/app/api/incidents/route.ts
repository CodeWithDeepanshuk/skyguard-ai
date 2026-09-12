import { NextRequest, NextResponse } from 'next/server';
import { backendJSON, observedFeedStatus } from '@/server/backend';
export const dynamic = 'force-dynamic';
export async function GET(request: NextRequest) {
  try {
    await observedFeedStatus();
    const incidents = await backendJSON('/api/live/incidents');
    if (!Array.isArray(incidents)) throw new Error('Invalid incident response.');
    const limit = Math.min(500, Math.max(1, Number(request.nextUrl.searchParams.get('limit')) || 100));
    return NextResponse.json(incidents.filter(i => !i.simulation).slice(0, limit));
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Live incidents unavailable.' }, { status: 503 });
  }
}
