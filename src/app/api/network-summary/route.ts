import { NextResponse } from 'next/server';
import { getEnrichedStations, getOperationalIncidents } from '@/server/liveData';

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

export async function GET() {
  try {
    const [stations, incidents] = await Promise.all([
      getEnrichedStations(),
      getOperationalIncidents(100),
    ]);

    const genuine = stations.filter((s) => s.latest_provider === 'METAR' || s.latest_provider === 'IMD_AWS');
    const reportingCount = genuine.filter((s) => s.temperature_c !== null && s.observation_status === 'FRESH').length;
    const freshCount = genuine.filter((s) => s.health_status === 'NO_ANOMALY_DETECTED').length;
    const faultCount = genuine.filter((s) => s.health_status === 'PROBABLE_FAULT' || s.health_status === 'CRITICAL').length;
    const weatherCount = stations.filter((s) => s.health_status === 'GENUINE_WEATHER_EVENT').length;
    const actualTimes = genuine
      .map((s) => s.latest_observation_utc ? new Date(s.latest_observation_utc).getTime() : NaN)
      .filter((t) => Number.isFinite(t));
    const latestMs = actualTimes.length ? Math.max(...actualTimes) : NaN;
    const latestObservation = Number.isFinite(latestMs) ? new Date(latestMs).toISOString() : null;

    const summary = {
      catalog_stations: stations.length,
      currently_reporting_stations: reportingCount,
      reporting_stations_outside_catalog: 0,
      all_reporting_stations_in_store: reportingCount,
      fresh_stations: freshCount,
      delayed_stations: 0,
      stale_reporting_stations: 0,
      offline_or_silent_catalog_stations: stations.length - reportingCount,
      probable_fault_stations: faultCount,
      genuine_weather_stations: weatherCount,
      active_incidents: incidents.length,
      observation_records: reportingCount,
      latest_observation_utc: latestObservation,
      latest_observation_age_minutes: Number.isFinite(latestMs) ? Math.max(0, Math.round((Date.now() - latestMs) / 60000)) : null,
      reporting_window_hours: 24,
      freshness_threshold_minutes: 90,
      reporting_by_source: {
        OPEN_METEO_LIVE_REFERENCE: stations.filter((s) => s.latest_provider === 'OPEN_METEO_LIVE').length,
        METAR: stations.filter((s) => s.latest_provider === 'METAR' && s.temperature_c !== null && s.observation_status === 'FRESH').length,
        IMD_AWS: stations.filter((s) => s.latest_provider === 'IMD_AWS' && s.temperature_c !== null && s.observation_status === 'FRESH').length,
      },
      storage: {
        backend: 'sqlite',
        durable: false,
        status: 'operational_live_sync',
      },
      catalog_basis: 'All-India 1,008 AWS Station Network Catalog (IMD / WIS 2.0 / Agro-AWS)',
      reference_only_stations: stations.filter((s) => s.latest_provider === 'OPEN_METEO_LIVE').length,
      catalog_is_live_aws_coverage: false,
      reporting_count_definition: 'Distinct catalog-mapped stations with fresh METAR or IMD_AWS observations; Open-Meteo is reference data only',
      generated_at_utc: new Date().toISOString(),
    };

    return NextResponse.json(summary, {
      headers: {
        'x-skyguard-data-mode': 'operational-observation-store',
        'Cache-Control': 'no-store, max-age=0',
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Operational summary unavailable.' },
      { status: 500 }
    );
  }
}
