import { NextResponse } from 'next/server';
import { backendJSON } from '@/server/backend';
export const dynamic = 'force-dynamic';
export const maxDuration = 60;
interface BackendHealth {
  model_loaded?: boolean;
  deployment?: { revision?: string };
}
export async function GET() {
  let details: BackendHealth | null = null;
  try { details = await backendJSON<BackendHealth>('/health'); } catch { /* Unavailable is not healthy. */ }
  return NextResponse.json({ status: details ? 'connected' : 'degraded', frontend: true,
    ml_service: Boolean(details), model_loaded: details?.model_loaded ?? false,
    backend_revision: details?.deployment?.revision ?? null,
    retryable: !details, retry_after_seconds: details ? null : 5,
    live_validation: 'research_only', database: null,
    timestamp: new Date().toISOString(), version: '1.0.0',
  });
}
