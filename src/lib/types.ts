/**
 * SkyGuard AI - Core Domain Types
 * SIH Problem Statement 26073
 * Strict Three-Parameter Meteorological Contract: Temperature [°C], Pressure [hPa], Relative Humidity [%]
 */

export type MeteorologicalParameter = 'temperature' | 'pressure' | 'relative_humidity' | 'multi_sensor';

export type StationQualityState = 
  | 'HEALTHY'
  | 'NO_ANOMALY_DETECTED'
  | 'GENUINE_WEATHER_EVENT'
  | 'WARMING_UP'
  | 'WATCH'
  | 'PROBABLE_FAULT'
  | 'CRITICAL'
  | 'MULTI_SENSOR_ANOMALY'
  | 'COMMUNICATION_FAILURE'
  | 'DELAYED'
  | 'STALE'
  | 'NO_RECENT_REPORT'
  | 'NOT_OBSERVED_IN_STORE'
  | 'NOT_ASSESSED'
  | 'UNVERIFIED';

export type SourceType = string;

export interface StationMetadata {
  station_id: string;
  station_name: string;
  latitude: number;
  longitude: number;
  elevation_m: number;
  state?: string;
  climate_zone?: string;
  network_type?: string;
  is_benchmark?: boolean;
  is_active_2024_plus?: boolean;
  catalog_only?: boolean;
}

export interface StationObservation {
  station_id: string;
  station_name: string;
  latitude: number;
  longitude: number;
  elevation: number | null;
  timestamp_utc: string | null;
  temperature: number | null;
  pressure: number | null;
  relative_humidity: number | null;
  source: string;
  source_type: SourceType;
  observation_age_minutes: number | null;
  quality_state: StationQualityState;
  state?: string;
  district?: string | null;
  provider_station_id?: string | null;
  wigos_id?: string | null;
  icao_code?: string | null;
  pressure_type?: string | null;
  humidity_observation_type?: string | null;
  observation_status?: string;
  assessment_decision?: string | null;
  assessment_severity?: string | null;
  anomaly_score?: number | null;
  score_label?: string | null;
  root_cause?: string | null;
  neighbor_support?: Record<string, number> | null;
  communication?: Record<string, unknown> | null;
  source_quality_flags?: string[];
  calibrated_probability_available?: boolean;
  /** Legacy field: populated only if a genuinely calibrated probability exists. */
  anomaly_probability?: number | null;
  fault_type?: string | null;
  expected_temperature?: number | null;
  expected_pressure?: number | null;
  expected_humidity?: number | null;
  temp_residual?: number | null;
  press_residual?: number | null;
  rh_residual?: number | null;
  temp_robust_z?: number | null;
  neighbour_agreement_pct?: number | null;
  active_incident_count?: number;
  catalog_only?: boolean;
  is_benchmark?: boolean;
}

export interface NeighbourStation {
  station_id: string;
  station_name: string;
  latitude: number;
  longitude: number;
  distance_km: number;
  elevation_m: number | null;
  temperature_c: number | null;
  pressure_hpa: number | null;
  relative_humidity_pct: number | null;
  temperature_delta?: number | null;
  state?: StationQualityState;
  weight?: number;
}

export interface TelemetryPoint {
  timestamp_utc: string;
  observed_temp: number | null;
  model_temp?: number | null;
  neighbour_temp?: number | null;
  observed_pressure: number | null;
  model_pressure?: number | null;
  neighbour_pressure?: number | null;
  observed_rh: number | null;
  model_rh?: number | null;
  neighbour_rh?: number | null;
  is_anomaly?: boolean;
}

export interface IncidentRecord {
  incident_id: string;
  station_id: string;
  station_name: string;
  latitude: number;
  longitude: number;
  fault_class: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  confidence: number | null;
  anomaly_score?: number | null;
  score_label?: string | null;
  calibrated_probability_available?: boolean;
  detected_timestamp_utc: string;
  duration_minutes: number | null;
  affected_parameter: MeteorologicalParameter;
  status: 'DETECTED' | 'CONFIRMED' | 'REVIEW' | 'ACKNOWLEDGED' | 'RESOLVED';
  decision?: string;
  state_machine_stage?: string;
  persistence_votes: {
    votes: number;
    window_size: number;
    threshold: number;
  };
  explanation: string;
  source_provenance: string;
  model_version: string | null;
  observed_value: string | null;
  expected_value: string | null;
  residual: string | null;
  evidence?: Array<Record<string, unknown>>;
  neighbor_support?: Record<string, number>;
  recommendation?: string | null;
  corrections?: Array<Record<string, unknown>>;
  source_observation_key?: string | null;
  source_observation_immutable?: boolean;
}

export interface ValidationGateRecord {
  gate_number: number;
  code: string;
  name: string;
  category: 
    | 'Data Integrity'
    | 'Leakage Prevention'
    | 'Generalization'
    | 'Weather Preservation'
    | 'Incident Performance'
    | 'Root Cause'
    | 'Calibration'
    | 'Operational Robustness';
  definition: string;
  threshold: string;
  measured_value: string;
  status: 'PASS' | 'FAIL' | 'RESEARCH_FRONTIER';
  evidence: string;
  evaluation_artifact: string;
  run_id: string;
  model_version: string;
}

export interface OperationalNetworkKPIs {
  catalog_stations: number | null;
  stations_reporting_now: number | null;
  healthy_count: number | null;
  watch_count: number | null;
  probable_fault_count: number | null;
  critical_count: number | null;
  stale_count: number | null;
  open_incidents: number | null;
  median_data_age_minutes: number | null;
  engine_status: 'OPERATIONAL' | 'DEGRADED' | 'OFFLINE';
  last_eval_timestamp_utc: string | null;
}

export type WorkingViewFilter = 
  | 'ALL_INDIA'
  | 'NORTH_INDIA'
  | 'SOUTH_INDIA'
  | 'EAST_INDIA'
  | 'WEST_CENTRAL'
  | 'CRITICAL_STATIONS'
  | 'ACTIVE_INCIDENTS'
  | 'HOLDOUT_SET';
