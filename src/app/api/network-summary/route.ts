import { NextResponse } from 'next/server';
import { backendJSON } from '@/server/backend';

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

export async function GET() {
  try {
    const payload = await backendJSON('/api/v1/network/operational-summary');
    return NextResponse.json(payload);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Operational summary unavailable.' },
      { status: 503 },
    );
  }
}
