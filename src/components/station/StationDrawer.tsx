'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { AlertTriangle, ArrowUpRight, Database, Download, Network, ShieldCheck } from 'lucide-react';
import { formatHumidity, formatPressure, formatTemp, formatTime } from '@/lib/formatters';
import { finiteOrNull } from '@/lib/operational';
import { StationObservation, TelemetryPoint } from '@/lib/types';
import { StationHeader } from './StationHeader';
import { SensorTrendChart } from './SensorTrendChart';

interface DetailPayload {
  metadata?: Record<string, any>;
  latest?: Record<string, any> | null;
  history?: Array<Record<string, any>>;
  neighbors?: Array<Record<string, any>>;
  assessment?: Record<string, any> | null;
  communication?: Record<string, any> | null;
  message?: string;
}

function ValueCard({ label, value, detail, colour }: { label: string; value: string; detail: string; colour: string }) {
  return (
    <div className="rounded-xl border border-[#D8E6EF] bg-white p-3 shadow-sm">
      <p className="text-[10px] font-bold uppercase tracking-wider text-[#52667A]">{label}</p>
      <p className="mt-1 text-xl font-black tabular-nums" style={{ color: colour }}>{value}</p>
      <p className="mt-1 text-[10px] leading-relaxed text-slate-500">{detail}</p>
    </div>
  );
}

export function StationDrawer({
  station,
  isOpen,
  onClose,
  timeMode,
}: {
  station: StationObservation | null;
  isOpen: boolean;
  onClose: () => void;
  timeMode: 'UTC' | 'IST';
  allStations?: StationObservation[];
}) {
  const [detail, setDetail] = useState<DetailPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!station || !isOpen) return;
    const controller = new AbortController();
    setLoading(true);
    setDetail(null);
    setError(null);
    fetch('/api/stations/' + encodeURIComponent(station.station_id) + '?hours=72', { cache: 'no-store', signal: controller.signal })
      .then(async response => {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.message || payload.error || 'Station observations are unavailable.');
        setDetail(payload);
      })
      .catch(reason => {
        if (reason?.name !== 'AbortError') setError(reason instanceof Error ? reason.message : 'Station observations are unavailable.');
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [station, isOpen]);

  const history = useMemo<TelemetryPoint[]>(() => (detail?.history || []).map(row => ({
    timestamp_utc: String(row.observation_timestamp_utc || ''),
    observed_temp: finiteOrNull(row.temperature_c),
    observed_pressure: finiteOrNull(row.pressure_hpa),
    observed_rh: finiteOrNull(row.relative_humidity_pct),
  })).filter(row => Boolean(row.timestamp_utc)), [detail]);

  if (!isOpen || !station) return null;
  const latest = detail?.latest;
  const assessment = detail?.assessment;
  const evidence = Array.isArray(assessment?.evidence) ? assessment.evidence : [];
  const corrections = Array.isArray(assessment?.corrections) ? assessment.corrections : [];
  const neighbours = Array.isArray(detail?.neighbors) ? detail.neighbors : [];
  const temperature = latest ? finiteOrNull(latest.temperature_c) : station.temperature;
  const pressure = latest ? finiteOrNull(latest.pressure_hpa) : station.pressure;
  const humidity = latest ? finiteOrNull(latest.relative_humidity_pct) : station.relative_humidity;

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col overflow-hidden border-l border-[#D8E6EF] bg-white shadow-2xl">
      <StationHeader station={station} timeMode={timeMode} onClose={onClose} />
      <div className="flex-1 space-y-4 overflow-y-auto bg-[#F5F9FC] p-4">
        {loading && <div className="rounded-xl border border-sky-200 bg-sky-50 p-3 text-xs text-sky-800">Loading the append-only observation history and causal evidence…</div>}
        {error && <div className="flex gap-2 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900"><AlertTriangle className="h-4 w-4 shrink-0" />{error} No values have been generated as a fallback.</div>}

        <section>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-[#102A43]">Latest three-parameter observation</h3>
            <span className="text-[10px] font-mono text-slate-500">{latest?.observation_timestamp_utc ? formatTime(latest.observation_timestamp_utc, timeMode) : 'Not available'}</span>
          </div>
          <div className="grid gap-2 sm:grid-cols-3">
            <ValueCard label="Temperature" value={formatTemp(temperature)} detail={latest ? 'Direct/decoded source field' : 'Not available in observation store'} colour="#D97706" />
            <ValueCard label="Pressure" value={formatPressure(pressure)} detail={latest?.pressure_type ? 'Semantics: ' + latest.pressure_type : 'Pressure semantics not available'} colour="#1769AA" />
            <ValueCard label="Relative humidity" value={formatHumidity(humidity)} detail={latest?.humidity_observation_type ? 'Field type: ' + latest.humidity_observation_type : 'Humidity observation type not available'} colour="#7C3AED" />
          </div>
          {latest && <div className="mt-2 rounded-xl border border-[#D8E6EF] bg-white px-3 py-2 text-[10px] text-[#52667A]"><Database className="mr-1 inline h-3.5 w-3.5 text-[#1769AA]" />Provider {latest.provider || 'Not available'} · provider station ID {latest.provider_station_id || 'Not available'} · raw payload hash {latest.raw_payload_hash || 'Not available'}</div>}
        </section>

        <section className="rounded-xl border border-[#D8E6EF] bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-[#52667A]">Causal operational assessment</p>
              <h3 className="mt-1 text-base font-black text-[#102A43]">{assessment?.decision || 'Not assessed'}</h3>
              <p className="mt-1 text-xs text-[#52667A]">{assessment?.recommendation || detail?.message || 'No assessment is available.'}</p>
            </div>
            <div className="rounded-xl border border-violet-200 bg-violet-50 px-3 py-2 text-right">
              <p className="text-[9px] font-bold uppercase text-violet-700">Anomaly evidence score</p>
              <p className="text-lg font-black text-violet-800">{assessment?.anomaly_score == null ? 'N/A' : Number(assessment.anomaly_score).toFixed(3)}</p>
              <p className="text-[9px] text-violet-700">Not a calibrated probability</p>
            </div>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-3 text-[10px]">
            <div className="rounded-lg bg-slate-50 p-2"><span className="text-slate-500">Root cause</span><b className="mt-0.5 block text-slate-800">{assessment?.root_cause || 'Not available'}</b></div>
            <div className="rounded-lg bg-slate-50 p-2"><span className="text-slate-500">Severity</span><b className="mt-0.5 block text-slate-800">{assessment?.severity || 'Not available'}</b></div>
            <div className="rounded-lg bg-slate-50 p-2"><span className="text-slate-500">Warm-up</span><b className="mt-0.5 block text-slate-800">{assessment?.warmup_state || 'Not available'}</b></div>
          </div>
        </section>

        <section className="rounded-xl border border-[#D8E6EF] bg-white p-4 shadow-sm">
          <h3 className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-[#102A43]"><ShieldCheck className="h-4 w-4 text-[#0F9D8A]" />Contributing evidence</h3>
          {evidence.length === 0 ? <p className="mt-3 text-xs text-slate-500">No anomaly evidence is available for this observation.</p> : (
            <div className="mt-3 space-y-2">
              {evidence.map((item: any, index: number) => (
                <div key={String(item.code) + index} className="rounded-lg border border-slate-100 bg-slate-50 p-2.5 text-xs">
                  <div className="flex justify-between gap-2"><b className="text-[#102A43]">{item.code || 'Evidence'}</b><span className="font-mono text-violet-700">strength {item.strength == null ? 'N/A' : Number(item.strength).toFixed(2)}</span></div>
                  <p className="mt-1 text-[#52667A]">{item.message || 'No explanation available.'}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-xl border border-[#D8E6EF] bg-white p-4 shadow-sm">
          <h3 className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-[#102A43]"><Network className="h-4 w-4 text-[#1769AA]" />Time-aligned neighbours</h3>
          {neighbours.length === 0 ? <p className="mt-3 text-xs text-slate-500">No aligned neighbours within the current 90-minute / 350 km evidence window.</p> : (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[540px] text-left text-[10px]">
                <thead className="text-slate-500"><tr><th className="pb-2">Station</th><th>Distance</th><th>Temperature</th><th>Pressure</th><th>RH</th></tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {neighbours.map((row: any) => <tr key={row.canonical_station_id || row.station_id}><td className="py-2 font-semibold text-slate-800">{row.station_name || row.canonical_station_id}</td><td>{row.distance_km == null ? 'N/A' : row.distance_km + ' km'}</td><td>{formatTemp(finiteOrNull(row.temperature_c))}</td><td>{formatPressure(finiteOrNull(row.pressure_hpa))}</td><td>{formatHumidity(finiteOrNull(row.relative_humidity_pct))}</td></tr>)}
                </tbody>
              </table>
            </div>
          )}
          <p className="mt-2 text-[9px] text-slate-500">Pressure buddies are compared only when pressure_type matches the target. Current pressure spatial QC: {assessment?.pressure_spatial_qc || 'Not available'}.</p>
        </section>

        {history.length > 0 ? <SensorTrendChart data={history} stationName={station.station_name} /> : <div className="rounded-xl border border-[#D8E6EF] bg-white p-4 text-xs text-slate-500">No causal history is available. The system will remain in warm-up and will not invent a 24-hour trace.</div>}

        <section className="rounded-xl border border-[#D8E6EF] bg-white p-4 text-xs">
          <h3 className="font-bold text-[#102A43]">Communication and maintenance</h3>
          <p className="mt-2 text-[#52667A]">Communication: <b>{detail?.communication?.decision || 'Not assessed'}</b> — {detail?.communication?.reason || 'No cadence decision available.'}</p>
          <p className="mt-2 text-[#52667A]">{history.length >= 24 * 7 ? 'Longer-term history is available for trend review.' : 'Maintenance horizon is not estimated: approximately 7–30 days of reliable history is required for defensible degradation trends.'}</p>
        </section>

        {corrections.length > 0 && <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs"><h3 className="font-bold text-amber-900">Advisory correction — never overwrites raw data</h3>{corrections.map((item: any) => <p key={item.sensor} className="mt-2 text-amber-900">{item.sensor}: raw {item.raw_value}; estimate {item.estimated_value}; interval [{item.interval_lower}, {item.interval_upper}]. {item.reason}</p>)}</section>}
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-[#D8E6EF] bg-white p-3">
        <Link href={'/stations/' + encodeURIComponent(station.station_id)} className="flex min-h-11 items-center gap-1.5 rounded-xl border border-sky-200 bg-sky-50 px-3 text-xs font-bold text-[#1769AA]">Full dossier <ArrowUpRight className="h-3.5 w-3.5" /></Link>
        <button onClick={() => {
          const blob = new Blob([JSON.stringify({ station, detail }, null, 2)], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const anchor = document.createElement('a');
          anchor.href = url;
          anchor.download = 'skyguard_' + station.station_id + '_evidence.json';
          anchor.click();
          URL.revokeObjectURL(url);
        }} className="flex min-h-11 items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 text-xs text-slate-700"><Download className="h-3.5 w-3.5" />Export evidence</button>
      </div>
    </div>
  );
}
