import { NextResponse } from 'next/server';
import { backendJSON } from '@/server/backend';
export const dynamic = 'force-dynamic';
export const maxDuration = 60;
interface BackendHealth {
  status?: string;
  model_version?: string;
  model_loaded?: boolean;
  live_capable?: boolean;
  continuous_history_ready?: boolean;
  imd_aws_credentials_configured?: boolean;
  operational_storage?: Record<string, unknown>;
  detector_inputs?: string[];
  deployment?: { revision?: string };
}
export async function GET() {
  let details: BackendHealth | null = null;
  try { details = await backendJSON<BackendHealth>('/health'); } catch { /* Unavailable is not healthy. */ }
  return NextResponse.json({ status: details ? 'connected' : 'degraded', frontend: true,
    ml_service: Boolean(details), model_loaded: details?.model_loaded ?? false,
    backend_revision: details?.deployment?.revision ?? null,
    backend_status: details?.status ?? null,
    model_version: details?.model_version ?? null,
    detector_inputs: details?.detector_inputs ?? null,
    live_capable: details?.live_capable ?? false,
    continuous_history_ready: details?.continuous_history_ready ?? false,
    imd_aws_credentials_configured: details?.imd_aws_credentials_configured ?? false,
    operational_storage: details?.operational_storage ?? null,
    retryable: !details, retry_after_seconds: details ? null : 5,
    live_validation: 'research_only',
    timestamp: new Date().toISOString(), version: '1.0.0',
  });
}
