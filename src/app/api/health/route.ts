import { NextResponse } from 'next/server';
import { backendJSON } from '@/server/backend';
export const dynamic = 'force-dynamic';
export async function GET() {
  let details = null;
  try { details = await backendJSON('/health'); } catch { /* Unavailable is not healthy. */ }
  return NextResponse.json({ status: details ? 'connected' : 'degraded', frontend: true,
    ml_service: Boolean(details), model_loaded: details?.model_loaded ?? false,
    live_validation: 'research_only', database: null,
    timestamp: new Date().toISOString(), version: '1.0.0',
  });
}
