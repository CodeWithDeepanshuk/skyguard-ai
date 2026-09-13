import { IncidentRecord, StationObservation, StationQualityState } from '@/lib/types';

const QUALITY_STATES = new Set<StationQualityState>([
  'HEALTHY',
  'NO_ANOMALY_DETECTED',
  'GENUINE_WEATHER_EVENT',
  'WARMING_UP',
  'WATCH',
  'PROBABLE_FAULT',
  'CRITICAL',
  'MULTI_SENSOR_ANOMALY',
  'COMMUNICATION_FAILURE',
  'DELAYED',
  'STALE',
  'NO_RECENT_REPORT',
  'NOT_OBSERVED_IN_STORE',
  'NOT_ASSESSED',
  'UNVERIFIED',
]);

export function finiteOrNull(value: unknown): number | null {
  if (value === '' || value === null || value === undefined) return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function qualityState(value: unknown): StationQualityState {
  const state = String(value || 'NOT_ASSESSED') as StationQualityState;
  return QUALITY_STATES.has(state) ? state : 'NOT_ASSESSED';
}

export function mapOperationalStation(raw: Record<string, any>): StationObservation {
  const latestProvider = raw.latest_provider ? String(raw.latest_provider) : null;
  return {
    station_id: String(raw.station_id || raw.canonical_station_id || ''),
    station_name: String(raw.station_name || raw.station_id || 'Unnamed station'),
    latitude: finiteOrNull(raw.latitude) ?? 0,
    longitude: finiteOrNull(raw.longitude) ?? 0,
    elevation: finiteOrNull(raw.elevation_m),
    timestamp_utc: raw.latest_observation_utc ? String(raw.latest_observation_utc) : null,
    temperature: finiteOrNull(raw.temperature_c),
    pressure: finiteOrNull(raw.pressure_hpa),
    relative_humidity: finiteOrNull(raw.relative_humidity_pct),
    source: latestProvider || 'No received observation',
    source_type: latestProvider || 'Catalog metadata only',
    observation_age_minutes: finiteOrNull(raw.observation_age_minutes),
    observation_status: String(raw.observation_status || 'NOT_OBSERVED_IN_STORE'),
    quality_state: qualityState(raw.health_status),
    state: String(raw.state || raw.climate_zone || ''),
    district: raw.district ? String(raw.district) : null,
    provider_station_id: raw.provider_station_id ? String(raw.provider_station_id) : null,
    wigos_id: raw.wigos_id ? String(raw.wigos_id) : null,
    icao_code: raw.icao_code ? String(raw.icao_code) : null,
    pressure_type: raw.pressure_type ? String(raw.pressure_type) : null,
    humidity_observation_type: raw.humidity_observation_type ? String(raw.humidity_observation_type) : null,
    assessment_decision: raw.assessment_decision ? String(raw.assessment_decision) : null,
    assessment_severity: raw.assessment_severity ? String(raw.assessment_severity) : null,
    anomaly_score: finiteOrNull(raw.anomaly_score),
    score_label: raw.score_label ? String(raw.score_label) : null,
    root_cause: raw.root_cause ? String(raw.root_cause) : null,
    neighbor_support: raw.neighbor_support && typeof raw.neighbor_support === 'object' ? raw.neighbor_support : null,
    communication: raw.communication && typeof raw.communication === 'object' ? raw.communication : null,
    source_quality_flags: Array.isArray(raw.source_quality_flags) ? raw.source_quality_flags.map(String) : [],
    calibrated_probability_available: false,
    anomaly_probability: null,
    fault_type: raw.root_cause ? String(raw.root_cause) : null,
    catalog_only: !latestProvider,
    is_benchmark: Boolean(raw.is_benchmark),
    active_incident_count: raw.health_status === 'PROBABLE_FAULT' || raw.health_status === 'COMMUNICATION_FAILURE' ? 1 : 0,
  };
}

export function mapOperationalIncident(raw: Record<string, any>): IncidentRecord {
  const decision = String(raw.decision || 'PROBABLE_SENSOR_FAULT');
  const sensor = Array.isArray(raw.affected_sensors) && raw.affected_sensors.length
    ? String(raw.affected_sensors[0])
    : decision === 'COMMUNICATION_FAILURE' ? 'multi_sensor' : 'multi_sensor';
  const affectedParameter = ['temperature', 'pressure', 'relative_humidity', 'multi_sensor'].includes(sensor)
    ? sensor as IncidentRecord['affected_parameter']
    : sensor === 'humidity' ? 'relative_humidity' : 'multi_sensor';
  const stage = String(raw.incident_state || 'SUSPECTED');
  const status: IncidentRecord['status'] = stage === 'CONFIRMED' ? 'CONFIRMED' : 'REVIEW';
  return {
    incident_id: String(raw.incident_id || ''),
    station_id: String(raw.station_id || ''),
    station_name: String(raw.station_name || raw.station_id || 'Unknown station'),
    latitude: finiteOrNull(raw.latitude) ?? 0,
    longitude: finiteOrNull(raw.longitude) ?? 0,
    fault_class: String(raw.root_cause || decision),
    severity: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].includes(String(raw.severity))
      ? raw.severity
      : decision === 'COMMUNICATION_FAILURE' ? 'MEDIUM' : 'HIGH',
    confidence: raw.calibrated_probability_available ? finiteOrNull(raw.probability) : null,
    anomaly_score: finiteOrNull(raw.anomaly_score),
    score_label: raw.score_label ? String(raw.score_label) : null,
    calibrated_probability_available: Boolean(raw.calibrated_probability_available),
    detected_timestamp_utc: String(raw.detected_timestamp_utc || ''),
    duration_minutes: finiteOrNull(raw.duration_minutes),
    affected_parameter: affectedParameter,
    status,
    decision,
    state_machine_stage: stage,
    persistence_votes: { votes: 0, window_size: 0, threshold: 0 },
    explanation: String(raw.recommendation || 'Review the evidence before diagnosing station hardware.'),
    source_provenance: String(raw.source_provider || 'Observation store'),
    model_version: null,
    observed_value: null,
    expected_value: null,
    residual: null,
    evidence: Array.isArray(raw.evidence) ? raw.evidence : [],
    neighbor_support: raw.neighbor_support && typeof raw.neighbor_support === 'object' ? raw.neighbor_support : {},
    recommendation: raw.recommendation ? String(raw.recommendation) : null,
    corrections: Array.isArray(raw.corrections) ? raw.corrections : [],
    source_observation_key: raw.source_observation_key ? String(raw.source_observation_key) : null,
    source_observation_immutable: Boolean(raw.source_observation_immutable),
  };
}
