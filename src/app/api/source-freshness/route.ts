import fs from 'fs';
import path from 'path';
import { NextResponse } from 'next/server';
import { backendJSON } from '@/server/backend';

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

export async function GET() {
  let backendData: any = null;
  try {
    backendData = await backendJSON('/api/v1/sources/freshness');
  } catch {
    // Continue with local provenance
  }

  // Check local latest.json cache
  const cachePath = path.join(process.cwd(), 'data', 'live', 'latest.json');
  let localStationsCount = 0;
  let latestTimeUtc: string | null = null;
  if (fs.existsSync(cachePath)) {
    try {
      const parsed = JSON.parse(fs.readFileSync(cachePath, 'utf8'));
      const stations = Array.isArray(parsed.stations) ? parsed.stations : Array.isArray(parsed.readings) ? parsed.readings : [];
      if (stations.length > 0) {
        localStationsCount = stations.length;
        latestTimeUtc = parsed.collected_at_utc || stations[0].timestamp_utc || null;
      }
    } catch {
      // Ignore
    }
  }

  const providers = backendData?.providers || [];
  const hasOpenMeteo = providers.some((p: any) => p.provider === 'OPEN_METEO_LIVE');

  if (!hasOpenMeteo) {
    providers.unshift({
      provider: 'OPEN_METEO_LIVE',
      access: 'reference/model API (not physical AWS telemetry)',
      freshness: {
        latest_observation_utc: latestTimeUtc,
        latest_ingestion_utc: latestTimeUtc,
        observation_records: localStationsCount,
        stations_seen: localStationsCount,
        observation_age_minutes: latestTimeUtc ? Math.max(0, Math.round((Date.now() - new Date(latestTimeUtc).getTime()) / 60000)) : null,
        freshness: latestTimeUtc && (Date.now() - new Date(latestTimeUtc).getTime()) <= 90 * 60 * 1000 ? 'FRESH' : 'STALE',
      },
    });
  } else {
    // If backend provided OPEN_METEO_LIVE but freshness is null, populate it
    const om = providers.find((p: any) => p.provider === 'OPEN_METEO_LIVE');
    if (om && !om.freshness) {
      om.freshness = {
        latest_observation_utc: latestTimeUtc,
        latest_ingestion_utc: latestTimeUtc,
        observation_records: localStationsCount,
        stations_seen: localStationsCount,
        observation_age_minutes: latestTimeUtc ? Math.max(0, Math.round((Date.now() - new Date(latestTimeUtc).getTime()) / 60000)) : null,
        freshness: latestTimeUtc && (Date.now() - new Date(latestTimeUtc).getTime()) <= 90 * 60 * 1000 ? 'FRESH' : 'STALE',
      };
    }
  }

  // Ensure IMD_AWS and others are present
  const required = [
    { provider: 'IMD_AWS', access: 'credentials_not_configured (Awaiting MoES Portal Token)' },
    { provider: 'IMD_WIS2', access: 'public_official_fallback' },
    { provider: 'METAR', access: 'airport_observation_fallback' },
  ];
  for (const req of required) {
    if (!providers.some((p: any) => p.provider === req.provider)) {
      providers.push({ provider: req.provider, access: req.access, freshness: null });
    }
  }

  return NextResponse.json({
    providers,
    source_events: backendData?.source_events || [],
    reference_model_is_station_observation: false,
  });
}
