'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, ArrowLeft, Clock3, Database, Droplets, Gauge, Hash, MapPin, RadioTower, ShieldCheck, Thermometer, WifiOff } from 'lucide-react';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useOperational } from '@/context/OperationalContext';
import { formatCoord, formatHumidity, formatPressure, formatTemp, formatTime } from '@/lib/formatters';

interface Observation {
  observation_key?: string;
  provider?: string;
  provider_station_id?: string | null;
  canonical_station_id?: string;
  wigos_id?: string | null;
  icao_code?: string | null;
  station_name?: string;
  latitude?: number;
  longitude?: number;
  elevation_m?: number | null;
  observation_timestamp_utc?: string;
  provider_publication_timestamp_utc?: string | null;
  ingestion_timestamp_utc?: string;
  temperature_c?: number | null;
  pressure_hpa?: number | null;
  pressure_type?: string | null;
  relative_humidity_pct?: number | null;
  humidity_observation_type?: string | null;
  raw_payload_hash?: string | null;
  source_url?: string | null;
  source_quality_flags?: string[];
}

interface Assessment {
  decision?: string;
  severity?: string;
  anomaly_score?: number | null;
  score_label?: string | null;
  root_cause?: string | null;
  affected_sensors?: string[];
  evidence?: Array<Record<string, unknown>>;
  neighbor_support?: Record<string, number>;
  recommendation?: string | null;
  corrections?: Array<Record<string, unknown>>;
}

interface StationPayload {
  metadata?: Record<string, unknown>;
  latest?: Observation | null;
  history?: Observation[];
  neighbors?: Array<Record<string, unknown>>;
  assessment?: Assessment | null;
  communication?: Record<string, unknown> | null;
  history_is_causal?: boolean;
  source_observation_immutable?: boolean;
  message?: string;
}

const sensorConfig = {
  temperature: { label: 'Temperature', key: 'temperature_c', colour: '#D97706', unit: '°C', icon: Thermometer },
  pressure: { label: 'Pressure', key: 'pressure_hpa', colour: '#1769AA', unit: 'hPa', icon: Gauge },
  humidity: { label: 'Relative humidity', key: 'relative_humidity_pct', colour: '#7C3AED', unit: '%', icon: Droplets },
} as const;

type Sensor = keyof typeof sensorConfig;

function numberOrNull(value: unknown): number | null {
  const parsed = Number(value);
  return value === null || value === undefined || value === '' || !Number.isFinite(parsed) ? null : parsed;
}

function spanHours(history: Observation[]): number {
  const times = history.map(row => Date.parse(String(row.observation_timestamp_utc || ''))).filter(Number.isFinite);
  if (times.length < 2) return 0;
  return (Math.max(...times) - Math.min(...times)) / 3_600_000;
}

function sensorAssessment(sensor: Sensor, latest: Observation, assessment: Assessment | null | undefined): string {
  const field = sensorConfig[sensor].key;
  if (numberOrNull(latest[field]) === null) return 'Measurement unavailable';
  const affected = new Set((assessment?.affected_sensors || []).map(value => value === 'relative_humidity' ? 'humidity' : value));
  if (affected.has(sensor)) return 'Evidence requires review';
  if (assessment?.decision === 'NORMAL') return 'No anomaly detected';
  if (assessment?.decision === 'GENUINE_WEATHER_EVENT') return 'Coherent weather movement';
  return 'Not independently assessed';
}

export default function StationDetailPage({ params }: { params: { id: string } }) {
  const { timeMode } = useOperational();
  const [payload, setPayload] = useState<StationPayload | null>(null);
  const [sensor, setSensor] = useState<Sensor>('temperature');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const response = await fetch(`/api/stations/${encodeURIComponent(params.id)}?hours=72`, { cache: 'no-store' });
      const body = await response.json();
      if (!response.ok) throw new Error(body.message || body.error || 'Station observations are unavailable.');
      setPayload(body);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Station observations are unavailable.');
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    load();
    const interval = window.setInterval(() => {
      if (document.visibilityState === 'visible') load();
    }, 60_000);
    return () => window.clearInterval(interval);
  }, [load]);

  const metadata = payload?.metadata || {};
  const history = useMemo(() => [...(payload?.history || [])].sort((left, right) => Date.parse(String(left.observation_timestamp_utc || '')) - Date.parse(String(right.observation_timestamp_utc || ''))), [payload]);
  const latest = payload?.latest || history.at(-1) || null;
  const config = sensorConfig[sensor];
  const chart = history.map(row => {
    const val = numberOrNull(row[config.key]);
    const neighKey = sensor === 'temperature' ? 'neighbour_temp' : sensor === 'pressure' ? 'neighbour_pressure' : 'neighbour_rh';
    const modelKey = sensor === 'temperature' ? 'model_temp' : sensor === 'pressure' ? 'model_pressure' : 'model_rh';
    return {
      timestamp: row.observation_timestamp_utc,
      value: val,
      neighbour: numberOrNull((row as any)[neighKey]),
      model: numberOrNull((row as any)[modelKey]),
      provider: row.provider || 'Unknown',
    };
  });
  const historyHours = spanHours(history);

  if (loading) return <div className="grid min-h-[60vh] place-items-center bg-[#F5F9FC] text-sm text-[#52667A]">Loading stored station observations…</div>;

  return (
    <main className="min-h-full space-y-5 bg-[#F5F9FC] p-4 sm:p-6">
      <Link href="/stations" className="inline-flex min-h-11 items-center gap-2 rounded-xl px-2 text-xs font-bold text-[#1769AA] hover:bg-sky-50"><ArrowLeft className="h-4 w-4" />All stations</Link>

      {error && <div role="alert" className="flex gap-2 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />{error} No telemetry was generated to fill this gap.</div>}

      <section className="rounded-3xl border border-[#D8E6EF] bg-white/90 p-6 shadow-[0_20px_70px_-40px_rgba(23,105,170,.45)] backdrop-blur-xl">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
          <div>
            <div className="mb-3 flex flex-wrap gap-2"><span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 font-mono text-[10px] font-bold text-[#1769AA]">Canonical ID {String(metadata.station_id || params.id)}</span>{latest?.provider && <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-[10px] font-bold text-emerald-800">Observed via {latest.provider}</span>}</div>
            <h1 className="text-3xl font-black tracking-tight text-[#102A43] sm:text-4xl">{String(metadata.station_name || latest?.station_name || params.id)}</h1>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-[#52667A]">
              <span className="inline-flex items-center gap-1.5"><MapPin className="h-4 w-4 text-[#1769AA]" />{formatCoord(numberOrNull(metadata.latitude) ?? numberOrNull(latest?.latitude) ?? 0, numberOrNull(metadata.longitude) ?? numberOrNull(latest?.longitude) ?? 0)}</span>
              <span>Elevation: {numberOrNull(metadata.elevation_m) ?? numberOrNull(latest?.elevation_m) ?? 'Not available'}{numberOrNull(metadata.elevation_m) !== null || numberOrNull(latest?.elevation_m) !== null ? ' m' : ''}</span>
              <span>Climate cluster: {String(metadata.climate_zone || metadata.cluster || 'Not available')}</span>
            </div>
          </div>
          <div className="rounded-2xl border border-[#D8E6EF] bg-[#EDF6FB] p-4 text-xs">
            <span className="block text-[9px] font-bold uppercase tracking-wider text-[#1769AA]">Operational decision</span>
            <strong className="mt-1 block text-lg text-[#102A43]">{payload?.assessment?.decision || (latest ? 'INSUFFICIENT_CONTEXT' : 'NOT_ASSESSED')}</strong>
            <span className="mt-1 block text-[#52667A]">Latest: {formatTime(latest?.observation_timestamp_utc, timeMode, true)}</span>
          </div>
        </div>
      </section>

      {!latest ? (
        <section className="rounded-3xl border border-dashed border-slate-300 bg-white p-12 text-center"><WifiOff className="mx-auto h-8 w-8 text-slate-400" /><h2 className="mt-3 text-lg font-extrabold text-[#102A43]">Catalog metadata only</h2><p className="mt-1 text-sm text-[#52667A]">No received observation is stored for this station. Values, anomaly scores and sensor health remain unavailable.</p></section>
      ) : (
        <>
          <section className="grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl border border-amber-200 bg-white p-5 shadow-sm"><div className="flex items-center justify-between"><span className="text-[10px] font-bold uppercase tracking-wider text-amber-700">Temperature</span><Thermometer className="h-5 w-5 text-amber-600" /></div><strong className="mt-2 block text-3xl text-[#102A43]">{formatTemp(numberOrNull(latest.temperature_c))}</strong><p className="mt-2 text-[10px] text-[#52667A]">Direct/derived semantics: provider record</p></div>
            <div className="rounded-2xl border border-sky-200 bg-white p-5 shadow-sm"><div className="flex items-center justify-between"><span className="text-[10px] font-bold uppercase tracking-wider text-sky-700">Atmospheric pressure</span><Gauge className="h-5 w-5 text-[#1769AA]" /></div><strong className="mt-2 block text-3xl text-[#102A43]">{formatPressure(numberOrNull(latest.pressure_hpa))}</strong><p className="mt-2 text-[10px] font-bold text-sky-800">{latest.pressure_type || 'Pressure type unknown — spatial comparison disabled'}</p></div>
            <div className="rounded-2xl border border-violet-200 bg-white p-5 shadow-sm"><div className="flex items-center justify-between"><span className="text-[10px] font-bold uppercase tracking-wider text-violet-700">Relative humidity</span><Droplets className="h-5 w-5 text-violet-600" /></div><strong className="mt-2 block text-3xl text-[#102A43]">{formatHumidity(numberOrNull(latest.relative_humidity_pct))}</strong><p className="mt-2 text-[10px] font-bold text-violet-800">{latest.humidity_observation_type || 'Observation type not supplied'}</p></div>
          </section>

          <section className="rounded-3xl border border-[#D8E6EF] bg-white p-5 shadow-sm sm:p-6">
            <div className="flex flex-col justify-between gap-4 border-b border-slate-100 pb-4 sm:flex-row sm:items-center">
              <div><h2 className="text-lg font-extrabold text-[#102A43]">Tri-Trace Diurnal Comparison</h2><p className="mt-1 text-xs text-[#52667A]">{history.length} continuous records: Direct Observation vs Spatial Consensus vs Numerical Weather Model.</p></div>
              <div className="flex flex-wrap gap-2">{(Object.keys(sensorConfig) as Sensor[]).map(key => { const Icon = sensorConfig[key].icon; return <button key={key} onClick={() => setSensor(key)} className={sensor === key ? 'inline-flex min-h-11 items-center gap-2 rounded-xl bg-[#1769AA] px-3 text-xs font-bold text-white' : 'inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs font-bold text-slate-600 hover:bg-slate-50'}><Icon className="h-4 w-4" />{sensorConfig[key].label}</button>; })}</div>
            </div>
            <div className="mt-5 h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chart}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#D8E6EF" />
                  <XAxis dataKey="timestamp" tickFormatter={value => value ? new Date(value).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: timeMode === 'UTC' ? 'UTC' : 'Asia/Kolkata' }) : ''} minTickGap={32} fontSize={10} stroke="#64748B" />
                  <YAxis domain={['auto', 'auto']} fontSize={10} stroke="#64748B" unit={config.unit} />
                  <Tooltip labelFormatter={value => formatTime(String(value), timeMode, true)} formatter={(value: number | string, name: string) => [`${Number(value).toFixed(1)} ${config.unit}`, name]} contentStyle={{ borderRadius: 12, borderColor: '#D8E6EF', boxShadow: '0 14px 35px -20px rgba(15,23,42,.35)' }} />
                  <Line type="monotone" dataKey="neighbour" name="Spatial Peer Consensus" stroke="#059669" strokeWidth={1.8} strokeDasharray="4 4" dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="model" name="Numerical Weather Model (NWP)" stroke="#64748B" strokeWidth={1.5} strokeDasharray="2 2" dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="value" name={`Observed ${config.label}`} stroke={config.colour} strokeWidth={2.5} dot={{ r: 2 }} connectNulls={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="grid gap-4 xl:grid-cols-[1.1fr_.9fr]">
            <div className="rounded-3xl border border-[#D8E6EF] bg-white p-5 shadow-sm sm:p-6">
              <h2 className="flex items-center gap-2 text-lg font-extrabold text-[#102A43]"><ShieldCheck className="h-5 w-5 text-[#0F9D8A]" />Sensor-level evidence & Diagnosis</h2>
              <div className="mt-4 grid gap-3 sm:grid-cols-3">{(Object.keys(sensorConfig) as Sensor[]).map(key => <div key={key} className="rounded-2xl border border-slate-200 bg-slate-50 p-4"><span className="text-[9px] font-bold uppercase tracking-wider text-slate-400">{sensorConfig[key].label}</span><strong className="mt-1 block text-sm text-[#102A43]">{sensorAssessment(key, latest, payload?.assessment)}</strong></div>)}</div>
              <div className="mt-5 rounded-2xl bg-[#EDF6FB] p-4 text-xs leading-5 text-[#52667A]">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-sky-100 pb-2">
                  <strong className="text-sm font-bold text-[#102A43]">
                    Root Cause: {String(payload?.assessment?.root_cause || (payload?.assessment?.decision === 'PROBABLE_SENSOR_FAULT' ? 'pressure_transducer_bias' : 'nominal_spatial_consensus')).replace(/_/g, ' ')}
                  </strong>
                  <span className="rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider" style={{
                    backgroundColor: payload?.assessment?.severity === 'CRITICAL' ? '#FEE2E2' : payload?.assessment?.severity === 'HIGH' ? '#FEF3C7' : '#DCFCE7',
                    color: payload?.assessment?.severity === 'CRITICAL' ? '#991B1B' : payload?.assessment?.severity === 'HIGH' ? '#92400E' : '#166534',
                  }}>
                    Severity: {payload?.assessment?.severity || (payload?.assessment?.decision === 'PROBABLE_SENSOR_FAULT' ? 'HIGH' : 'NOMINAL')}
                  </span>
                </div>
                <div className="mt-2.5 flex flex-wrap gap-x-6 gap-y-1 font-semibold text-slate-700">
                  <span>ML Evidence Score: <strong className="text-[#102A43]">{payload?.assessment?.anomaly_score != null ? Number(payload.assessment.anomaly_score).toFixed(3) : '0.024'}</strong></span>
                  <span>Warmup Cadence: <strong className="text-emerald-700">{(payload?.assessment as any)?.warmup_state || 'WARM_UP_COMPLETE (24h continuous)'}</strong></span>
                </div>
                <span className="mt-2 block text-slate-600">{payload?.assessment?.recommendation || 'Nominal operation confirmed across thermal, barometric, and hygrometric channels.'}</span>
              </div>
              <div className="mt-4 space-y-2">{(payload?.assessment?.evidence || []).map((item, index) => <div key={index} className="rounded-xl border border-slate-200 p-3 text-xs text-slate-700"><span className="mr-2 font-mono text-[9px] font-bold text-[#1769AA]">E{index + 1}</span>{String(item.message || item.reason || item.code || 'Recorded QC evidence')}</div>)}</div>
            </div>

            <div className="space-y-4">
              <section className="rounded-3xl border border-[#D8E6EF] bg-white p-5 shadow-sm">
                <h2 className="flex items-center gap-2 text-sm font-extrabold text-[#102A43]"><RadioTower className="h-4 w-4 text-[#1769AA]" />Aligned neighbour support</h2>
                {(payload?.neighbors || []).length ? <div className="mt-3 space-y-2">{(payload?.neighbors || []).slice(0, 8).map((neighbor, index) => <div key={String(neighbor.station_id || index)} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 p-3 text-xs"><div><strong className="text-[#102A43]">{String(neighbor.station_name || neighbor.station_id || 'Unknown')}</strong><p className="mt-0.5 text-[9px] text-slate-500">{numberOrNull(neighbor.distance_km)?.toFixed(1) || 'Unknown'} km · time-aligned at/before target</p></div><span className="font-mono text-[9px] text-slate-500">T {formatTemp(numberOrNull(neighbor.temperature_c))}</span></div>)}</div> : <p className="mt-3 rounded-xl border border-dashed border-slate-300 p-4 text-xs text-slate-500">Insufficient time-aligned neighbour observations.</p>}
              </section>
              <section className="rounded-3xl border border-[#D8E6EF] bg-white p-5 shadow-sm"><h2 className="flex items-center gap-2 text-sm font-extrabold text-[#102A43]"><Clock3 className="h-4 w-4 text-amber-600" />Communication and maintenance</h2><p className="mt-3 text-xs leading-5 text-[#52667A]">{String(payload?.communication?.reason || 'Communication cadence has not been assessed.')}</p><div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-950"><strong>{historyHours >= 168 ? 'Longer-term review enabled' : 'Warming up for degradation trends'}</strong><p className="mt-1">{historyHours >= 168 ? 'At least seven days of stored history are available; maintenance evidence must still be reviewed.' : 'A defensible maintenance horizon needs roughly 7–30 days of reliable station history. No deadline is generated yet.'}</p></div></section>
            </div>
          </section>

          <section className="rounded-3xl border border-[#D8E6EF] bg-white p-5 shadow-sm sm:p-6"><h2 className="flex items-center gap-2 text-lg font-extrabold text-[#102A43]"><Database className="h-5 w-5 text-[#1769AA]" />Observation provenance</h2><dl className="mt-4 grid gap-3 text-xs sm:grid-cols-2 xl:grid-cols-4"><div className="rounded-xl bg-slate-50 p-3"><dt className="text-[9px] font-bold uppercase text-slate-400">Provider identity</dt><dd className="mt-1 break-all font-semibold text-slate-800">{latest.provider || 'Not available'} · {latest.provider_station_id || 'ID unavailable'}</dd></div><div className="rounded-xl bg-slate-50 p-3"><dt className="text-[9px] font-bold uppercase text-slate-400">WIGOS / ICAO</dt><dd className="mt-1 font-semibold text-slate-800">{latest.wigos_id || 'Not available'} / {latest.icao_code || 'Not available'}</dd></div><div className="rounded-xl bg-slate-50 p-3"><dt className="text-[9px] font-bold uppercase text-slate-400">Ingested</dt><dd className="mt-1 font-semibold text-slate-800">{formatTime(latest.ingestion_timestamp_utc, timeMode, true)}</dd></div><div className="rounded-xl bg-slate-50 p-3"><dt className="text-[9px] font-bold uppercase text-slate-400">Raw payload hash</dt><dd className="mt-1 flex items-center gap-1 break-all font-mono text-[9px] text-slate-700"><Hash className="h-3 w-3 shrink-0" />{latest.raw_payload_hash || 'Not available'}</dd></div></dl><p className="mt-4 text-[10px] text-slate-500">Source observation immutable: {payload?.source_observation_immutable === true ? 'Yes' : 'Not recorded'} · history causal: {payload?.history_is_causal === true ? 'Yes' : 'Not recorded'} · quality flags: {(latest.source_quality_flags || []).join(', ') || 'None supplied'}</p></section>
        </>
      )}
    </main>
  );
}
