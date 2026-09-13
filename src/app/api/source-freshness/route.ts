import { NextResponse } from 'next/server';
import { backendJSON } from '@/server/backend';

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

export async function GET() {
  try {
    return NextResponse.json(await backendJSON('/api/v1/sources/freshness'));
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Source freshness unavailable.' },
      { status: 503 },
    );
  }
}
