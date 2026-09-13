import { NextResponse } from 'next/server';
import { backendJSON } from '@/server/backend';

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

export async function GET() {
  try {
    return NextResponse.json(await backendJSON('/api/v1/ingestion/health'));
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Ingestion health unavailable.' },
      { status: 503 },
    );
  }
}
