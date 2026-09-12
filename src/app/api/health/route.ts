import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  const mlUrl = process.env.SKYGUARD_API_URL || 'http://127.0.0.1:8000';
  let mlServiceHealthy = false;
  let mlDetails = null;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);
    const res = await fetch(`${mlUrl}/health`, {
      signal: controller.signal,
      cache: 'no-store'
    });
    clearTimeout(timeoutId);
    if (res.ok) {
      mlServiceHealthy = true;
      mlDetails = await res.json();
    }
  } catch {
    mlServiceHealthy = false;
  }

  return NextResponse.json({
    status: mlServiceHealthy ? 'healthy' : 'degraded',
    frontend: true,
    api: true,
    database: true,
    ml_service: mlServiceHealthy,
    ml_backend_url: mlUrl,
    ml_details: mlDetails,
    timestamp: new Date().toISOString(),
    version: '1.0.0',
    compliance: {
      problem_id: 'SIH 26073',
      parameters: ['temperature', 'pressure', 'relative_humidity'],
      policy: 'Phase 10 three-parameter certified; integer-aware freeze; CUSUM drift'
    }
  });
}
