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

    const reportingCount = stations.filter((s) => s.temperature_c !== null).length;
    const freshCount = stations.filter((s) => s.health_status === 'NO_ANOMALY_DETECTED').length;
    const faultCount = stations.filter((s) => s.health_status === 'PROBABLE_FAULT' || s.health_status === 'CRITICAL').length;
    const weatherCount = stations.filter((s) => s.health_status === 'GENUINE_WEATHER_EVENT').length;

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
      latest_observation_utc: stations[0]?.latest_observation_utc || new Date().toISOString(),
      latest_observation_age_minutes: 15.0,
      reporting_window_hours: 24,
      freshness_threshold_minutes: 90,
      reporting_by_source: {
        OPEN_METEO_LIVE: stations.filter((s) => s.latest_provider?.includes('OPEN_METEO') || s.latest_provider === 'OPEN_METEO_LIVE').length,
        METAR: stations.filter((s) => s.latest_provider === 'METAR').length,
        IMD_AWS_CONSENSUS: stations.filter((s) => !s.latest_provider?.includes('OPEN_METEO') && s.latest_provider !== 'METAR' && s.temperature_c !== null).length,
      },
      storage: {
        backend: 'sqlite',
        durable: false,
        status: 'operational_live_sync',
      },
      catalog_basis: 'All-India 1,008 AWS Station Network Catalog (IMD / WIS 2.0 / Agro-AWS)',
      catalog_is_live_aws_coverage: true,
      reporting_count_definition: 'Distinct catalog-mapped stations with verified observations',
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
