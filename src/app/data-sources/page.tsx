'use client';

import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, Database, FileKey2, RefreshCw, RadioTower, ShieldCheck, Waves, WifiOff } from 'lucide-react';
import { formatTime } from '@/lib/formatters';

interface SourceFreshness {
  provider: string;
  access: string;
  freshness: null | {
    latest_observation_utc?: string;
    latest_ingestion_utc?: string;
    observation_records?: number;
    stations_seen?: number;
    observation_age_minutes?: number;
    freshness?: string;
  };
}

interface DataState {
  summary: Record<string, any> | null;
  sources: SourceFreshness[];
  ingestion: Record<string, any> | null;
  provenance: Record<string, any> | null;
}

const stages = [
  ['01', 'Provider adapters', 'Credentialed IMD AWS/ARG first; public WIS2 SYNOP second; airport METAR third. Reference-model data never becomes a station observation.'],
  ['02', 'Identity and schema', 'Canonical IDs are resolved from provider IDs, WIGOS/ICAO and geographic checks—not station names alone.'],
  ['03', 'Append-only storage', 'Observation, publication and ingestion timestamps remain separate; hashes enforce idempotent duplicate rejection.'],
  ['04', 'Transport QC', 'Malformed, duplicate, late, out-of-order and communication evidence is separated from sensor hardware evidence.'],
  ['05', 'Physical and temporal QC', 'Temperature, pressure and RH bounds, rates, robust history, freeze patterns and CUSUM use current and past data only.'],
  ['06', 'Pressure-safe buddy QC', 'Neighbour comparison requires time alignment, minimum support and compatible pressure semantics.'],
  ['07', 'Incident evidence', 'The live path exposes NORMAL, WEATHER, PROBABLE FAULT, COMMUNICATION or INSUFFICIENT CONTEXT with an uncalibrated evidence score.'],
  ['08', 'Offline model research', 'LightGBM/TCN and other challengers remain offline evidence until live-domain labels and calibration justify promotion.'],
];

function storageLabel(storage: Record<string, any> | null | undefined): string {
  if (!storage) return 'Not available';
  return `${String(storage.backend || 'unknown').toUpperCase()} · ${storage.durable ? 'durable' : String(storage.status || 'not durable')}`;
}

export default function DataSourcesPage() {
  const [state, setState] = useState<DataState>({ summary: null, sources: [], ingestion: null, provenance: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const requests = ['/api/network-summary', '/api/source-freshness', '/api/ingestion-health', '/api/provenance'];
    const results = await Promise.allSettled(requests.map(async url => {
      const response = await fetch(url, { cache: 'no-store' });
      if (!response.ok) throw new Error(`${url} returned HTTP ${response.status}`);
      return response.json();
    }));
    const value = (index: number) => results[index].status === 'fulfilled' ? results[index].value : null;
    setState({ summary: value(0), sources: value(1)?.providers || [], ingestion: value(2), provenance: value(3) });
    const failed = results.filter(result => result.status === 'rejected').length;
    setError(failed ? `${failed} operational evidence endpoint${failed === 1 ? '' : 's'} could not be reached. Missing fields remain blank.` : null);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <main className="min-h-full space-y-5 bg-[#F5F9FC] p-4 sm:p-6">
      <section className="rounded-3xl border border-[#D8E6EF] bg-white/90 p-6 shadow-[0_20px_70px_-40px_rgba(23,105,170,.45)] backdrop-blur-xl">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div className="max-w-3xl"><div className="mb-3 inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-[10px] font-bold uppercase tracking-[.18em] text-[#1769AA]"><Database className="h-3.5 w-3.5" /> Data provenance</div><h1 className="text-3xl font-black tracking-tight text-[#102A43] sm:text-4xl">Know where every reading came from.</h1><p className="mt-3 text-sm leading-6 text-[#52667A]">Catalog coverage, reporting coverage and observation volume are different numbers. SkyGuard preserves that distinction together with pressure type, RH derivation and raw-message identity.</p></div>
          <button onClick={load} disabled={loading} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-[#1769AA] px-4 text-xs font-bold text-white hover:bg-[#12588f] disabled:opacity-60"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />Refresh source evidence</button>
        </div>
      </section>

      {error && <div role="alert" className="flex gap-2 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900"><AlertTriangle className="h-4 w-4 shrink-0" />{error}</div>}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {[
          ['Catalog metadata', state.summary?.catalog_stations, 'Not equal to live AWS coverage'],
          ['Reporting in 24 h', state.summary?.currently_reporting_stations, 'Catalog-mapped stations'],
          ['Fresh stations', state.summary?.fresh_stations, `≤ ${state.summary?.freshness_threshold_minutes ?? '—'} min`],
          ['Silent catalog stations', state.summary?.offline_or_silent_catalog_stations, 'No record in reporting window'],
          ['Stored observations', state.summary?.observation_records, storageLabel(state.summary?.storage)],
        ].map(([label, value, note]) => <div key={String(label)} className="rounded-2xl border border-[#D8E6EF] bg-white p-4 shadow-sm"><span className="text-[9px] font-bold uppercase tracking-wider text-slate-400">{label}</span><strong className="mt-1 block text-2xl tabular-nums text-[#102A43]">{typeof value === 'number' ? value.toLocaleString('en-IN') : 'Not available'}</strong><p className="mt-1 text-[10px] leading-4 text-[#52667A]">{String(note)}</p></div>)}
      </section>

      <section className="overflow-hidden rounded-3xl border border-[#D8E6EF] bg-white shadow-sm">
        <div className="border-b border-slate-100 p-5"><h2 className="flex items-center gap-2 text-lg font-extrabold text-[#102A43]"><RadioTower className="h-5 w-5 text-[#1769AA]" />Provider freshness and coverage</h2><p className="mt-1 text-xs text-[#52667A]">Counts below come from the append-only store; access state is reported by each adapter.</p></div>
        <div className="overflow-x-auto"><table className="w-full min-w-[820px] text-left text-xs"><thead className="bg-[#EDF6FB] text-[9px] uppercase tracking-wider text-[#52667A]"><tr><th className="p-4">Provider</th><th className="p-4">Role/access</th><th className="p-4">Stations seen</th><th className="p-4">Stored records</th><th className="p-4">Latest observation</th><th className="p-4">Freshness</th></tr></thead><tbody className="divide-y divide-slate-100">{state.sources.map(source => <tr key={source.provider}><td className="p-4 font-bold text-[#102A43]">{source.provider}</td><td className="p-4 text-[#52667A]">{source.access.replaceAll('_', ' ')}</td><td className="p-4 tabular-nums text-slate-800">{source.freshness?.stations_seen?.toLocaleString('en-IN') ?? 'Not available'}</td><td className="p-4 tabular-nums text-slate-800">{source.freshness?.observation_records?.toLocaleString('en-IN') ?? 'Not available'}</td><td className="p-4 text-[#52667A]">{formatTime(source.freshness?.latest_observation_utc, 'UTC')}</td><td className="p-4"><span className={source.freshness?.freshness === 'FRESH' ? 'rounded-full border border-emerald-200 bg-emerald-50 px-2 py-1 text-[9px] font-bold text-emerald-800' : source.freshness ? 'rounded-full border border-amber-200 bg-amber-50 px-2 py-1 text-[9px] font-bold text-amber-900' : 'rounded-full border border-slate-200 bg-slate-100 px-2 py-1 text-[9px] font-bold text-slate-600'}>{source.freshness?.freshness || 'No observations'}</span></td></tr>)}{!state.sources.length && <tr><td colSpan={6} className="p-8 text-center text-slate-500">Provider evidence unavailable.</td></tr>}</tbody></table></div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.15fr_.85fr]">
        <div className="rounded-3xl border border-[#D8E6EF] bg-white p-5 shadow-sm"><h2 className="flex items-center gap-2 text-lg font-extrabold text-[#102A43]"><Waves className="h-5 w-5 text-[#0EA5E9]" />Operational evidence pipeline</h2><div className="mt-4 grid gap-3 sm:grid-cols-2">{stages.map(([number, title, detail]) => <div key={number} className="rounded-2xl border border-slate-200 bg-slate-50 p-4"><span className="font-mono text-[9px] font-bold text-[#1769AA]">STAGE {number}</span><h3 className="mt-1 text-sm font-extrabold text-[#102A43]">{title}</h3><p className="mt-1 text-[11px] leading-5 text-[#52667A]">{detail}</p></div>)}</div></div>
        <div className="space-y-4">
          <section className="rounded-3xl border border-[#D8E6EF] bg-white p-5 shadow-sm"><h2 className="flex items-center gap-2 text-sm font-extrabold text-[#102A43]"><ShieldCheck className="h-4 w-4 text-[#0F9D8A]" />Three-parameter contract</h2><div className="mt-3 space-y-2 text-xs text-[#52667A]"><p className="rounded-xl bg-amber-50 p-3"><strong className="text-amber-900">Temperature:</strong> degrees Celsius</p><p className="rounded-xl bg-sky-50 p-3"><strong className="text-sky-900">Pressure:</strong> hPa with explicit pressure type</p><p className="rounded-xl bg-violet-50 p-3"><strong className="text-violet-900">Relative humidity:</strong> percent, direct or derived label retained</p></div><p className="mt-3 text-[10px] leading-4 text-slate-500">Wind, rain, cloud, dew point and forecast fields are not hidden detector inputs.</p></section>
          <section className={`rounded-3xl border p-5 shadow-sm ${state.summary?.storage?.durable ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50'}`}><h2 className="flex items-center gap-2 text-sm font-extrabold text-[#102A43]">{state.summary?.storage?.durable ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <WifiOff className="h-4 w-4 text-amber-700" />}Storage durability</h2><p className="mt-2 text-xs leading-5 text-[#52667A]">{storageLabel(state.summary?.storage)}. Production history must use PostgreSQL; local SQLite is a development fallback and must not be presented as restart-safe hosting.</p></section>
          <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="flex items-center gap-2 text-sm font-extrabold text-[#102A43]"><FileKey2 className="h-4 w-4 text-[#1769AA]" />Latest ingestion runs</h2><div className="mt-3 space-y-2">{(state.ingestion?.providers || []).map((run: Record<string, any>) => <div key={String(run.run_id)} className="rounded-xl bg-slate-50 p-3 text-[10px] text-[#52667A]"><strong className="text-[#102A43]">{String(run.provider)}</strong> · {String(run.status)} · inserted {Number(run.inserted_count || 0).toLocaleString('en-IN')} · duplicates {Number(run.duplicate_count || 0).toLocaleString('en-IN')} · dead letters {Number(run.dead_letter_count || 0).toLocaleString('en-IN')}<span className="mt-1 block">Finished {formatTime(run.finished_at_utc, 'UTC', true)}</span></div>)}{!(state.ingestion?.providers || []).length && <p className="text-xs text-slate-500">No ingestion-run evidence is available.</p>}</div></section>
        </div>
      </section>
    </main>
  );
}
