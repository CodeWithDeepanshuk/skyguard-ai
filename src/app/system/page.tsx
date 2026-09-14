'use client';

import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, Clock3, Cloud, Cpu, Database, RefreshCw, Server, ShieldCheck, WifiOff } from 'lucide-react';
import { formatTime } from '@/lib/formatters';

interface SystemState {
  health: Record<string, any> | null;
  summary: Record<string, any> | null;
  ingestion: Record<string, any> | null;
}

function StatusChip({ state }: { state: 'CONNECTED' | 'DEGRADED' | 'NOT CONFIGURED' | 'LOCAL FALLBACK' | 'DURABLE' }) {
  const style = state === 'CONNECTED' || state === 'DURABLE'
    ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
    : state === 'DEGRADED' || state === 'LOCAL FALLBACK'
      ? 'border-amber-200 bg-amber-50 text-amber-900'
      : 'border-slate-200 bg-slate-100 text-slate-700';
  return <span className={`rounded-full border px-2.5 py-1 text-[9px] font-bold uppercase tracking-wider ${style}`}>{state}</span>;
}

export default function SystemHealthPage() {
  const [state, setState] = useState<SystemState>({ health: null, summary: null, ingestion: null });
  const [loading, setLoading] = useState(true);
  const [checkedAt, setCheckedAt] = useState<string | null>(null);

  const probe = useCallback(async () => {
    setLoading(true);
    const results = await Promise.allSettled(['/api/health', '/api/network-summary', '/api/ingestion-health'].map(async endpoint => {
      const response = await fetch(endpoint, { cache: 'no-store' });
      if (!response.ok) throw new Error(`${endpoint}: HTTP ${response.status}`);
      return response.json();
    }));
    const value = (index: number) => results[index].status === 'fulfilled' ? results[index].value : null;
    setState({ health: value(0), summary: value(1), ingestion: value(2) });
    setCheckedAt(new Date().toISOString());
    setLoading(false);
  }, []);

  useEffect(() => { probe(); }, [probe]);

  const connected = state.health?.ml_service === true;
  const storage = state.summary?.storage || state.health?.operational_storage || state.ingestion?.storage;
  const durable = storage?.durable === true;
  const imdConfigured = state.health?.imd_aws_credentials_configured === true;
  const ingestionRuns: Array<Record<string, any>> = state.ingestion?.providers || [];

  const services = [
    { name: 'Next.js command interface', role: 'Responsive map, station and incident evidence views', endpoint: 'Current Vercel deployment', status: 'CONNECTED' as const, detail: 'Browser UI is running; this does not prove backend health.' },
    { name: 'FastAPI operational service', role: 'Provider adapters, append-only store and causal QC', endpoint: 'Configured SKYGUARD_API_URL / canonical Render service', status: connected ? 'CONNECTED' as const : 'DEGRADED' as const, detail: connected ? `Revision ${state.health?.backend_revision || 'not supplied'} · model artifact loaded: ${state.health?.model_loaded ? 'yes' : 'no'}` : 'Backend did not return a valid health response.' },
    { name: 'Observation store', role: 'Immutable telemetry, watermarks, run receipts and dead letters', endpoint: storage?.backend || 'Not available', status: durable ? 'DURABLE' as const : 'LOCAL FALLBACK' as const, detail: durable ? 'Database reports durable storage.' : 'SQLite/local filesystem is development-only; configure PostgreSQL for restart-safe production history.' },
    { name: 'Credentialed IMD AWS adapter', role: 'Primary physical AWS/ARG source when IMD access is granted', endpoint: 'Environment-only credentials', status: imdConfigured ? 'CONNECTED' as const : 'NOT CONFIGURED' as const, detail: imdConfigured ? 'Credentials are configured without being exposed to the browser.' : 'Public WIS2 and METAR fallback remain available; no IMD readings are fabricated.' },
  ];

  return (
    <main className="min-h-full space-y-5 bg-[#F5F9FC] p-4 sm:p-6">
      <section className="rounded-3xl border border-[#D8E6EF] bg-white/90 p-6 shadow-[0_20px_70px_-40px_rgba(23,105,170,.45)] backdrop-blur-xl">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end"><div><div className="mb-3 inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-[10px] font-bold uppercase tracking-[.18em] text-[#1769AA]"><Cpu className="h-3.5 w-3.5" /> System health</div><h1 className="text-3xl font-black tracking-tight text-[#102A43] sm:text-4xl">Operational truth, including what is missing.</h1><p className="mt-3 max-w-3xl text-sm leading-6 text-[#52667A]">Health cards report observed API state. They do not use hardcoded latency, station counts, model promotion or database durability.</p></div><button onClick={probe} disabled={loading} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-[#1769AA] px-4 text-xs font-bold text-white hover:bg-[#12588f] disabled:opacity-60"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />Probe services</button></div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl border border-[#D8E6EF] bg-white p-4 shadow-sm"><span className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Backend service</span><div className="mt-2 flex items-center gap-2">{connected ? <CheckCircle2 className="h-5 w-5 text-emerald-600" /> : <WifiOff className="h-5 w-5 text-amber-600" />}<strong className="text-lg text-[#102A43]">{connected ? 'Connected' : 'Unavailable'}</strong></div></div>
        <div className="rounded-2xl border border-[#D8E6EF] bg-white p-4 shadow-sm"><span className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Storage</span><strong className="mt-2 block text-lg text-[#102A43]">{storage ? `${String(storage.backend).toUpperCase()} · ${durable ? 'durable' : 'not durable'}` : 'Not available'}</strong></div>
        <div className="rounded-2xl border border-[#D8E6EF] bg-white p-4 shadow-sm"><span className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Stored observations</span><strong className="mt-2 block text-lg tabular-nums text-[#102A43]">{typeof state.summary?.observation_records === 'number' ? state.summary.observation_records.toLocaleString('en-IN') : 'Not available'}</strong></div>
        <div className="rounded-2xl border border-[#D8E6EF] bg-white p-4 shadow-sm"><span className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Last probe</span><strong className="mt-2 block text-sm text-[#102A43]">{formatTime(checkedAt, 'UTC', true)}</strong></div>
      </section>

      {!connected && !loading && <div role="alert" className="flex gap-2 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-950"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />The interface is online but the observation service is not reachable. Map telemetry and health must remain unavailable rather than switching to generated values.</div>}
      {!durable && storage && <div className="flex gap-2 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-950"><Database className="mt-0.5 h-4 w-4 shrink-0" />Production acceptance blocker: the active store reports {String(storage.backend)} / {String(storage.status)}. Add Render PostgreSQL through DATABASE_URL so 24-hour history survives service restarts.</div>}

      <section className="overflow-hidden rounded-3xl border border-[#D8E6EF] bg-white shadow-sm"><div className="border-b border-slate-100 p-5"><h2 className="flex items-center gap-2 text-lg font-extrabold text-[#102A43]"><Server className="h-5 w-5 text-[#1769AA]" />Subsystem status</h2></div><div className="divide-y divide-slate-100">{services.map(service => <div key={service.name} className="flex flex-col justify-between gap-3 p-5 sm:flex-row sm:items-center"><div><div className="flex flex-wrap items-center gap-2"><h3 className="text-sm font-extrabold text-[#102A43]">{service.name}</h3><StatusChip state={service.status} /></div><p className="mt-1 text-xs text-[#52667A]">{service.role}</p><p className="mt-1 text-[10px] leading-4 text-slate-500">{service.detail}</p></div><span className="max-w-sm break-all font-mono text-[9px] text-slate-500">{service.endpoint}</span></div>)}</div></section>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_.9fr]">
        <div className="rounded-3xl border border-[#D8E6EF] bg-white p-5 shadow-sm"><h2 className="flex items-center gap-2 text-lg font-extrabold text-[#102A43]"><Cloud className="h-5 w-5 text-[#0EA5E9]" />Latest provider runs</h2><div className="mt-4 space-y-3">{ingestionRuns.map(run => <div key={String(run.run_id)} className="rounded-2xl border border-slate-200 bg-slate-50 p-4"><div className="flex flex-wrap items-center justify-between gap-2"><strong className="text-sm text-[#102A43]">{String(run.provider)}</strong><StatusChip state={run.status === 'SUCCESS' ? 'CONNECTED' : 'DEGRADED'} /></div><div className="mt-3 grid grid-cols-2 gap-2 text-[10px] text-[#52667A] sm:grid-cols-4"><span>Fetched <b>{Number(run.fetched_count || 0).toLocaleString('en-IN')}</b></span><span>Inserted <b>{Number(run.inserted_count || 0).toLocaleString('en-IN')}</b></span><span>Duplicates <b>{Number(run.duplicate_count || 0).toLocaleString('en-IN')}</b></span><span>Dead letters <b>{Number(run.dead_letter_count || 0).toLocaleString('en-IN')}</b></span></div><p className="mt-2 text-[9px] text-slate-500">Finished: {formatTime(run.finished_at_utc, 'UTC', true)}</p></div>)}{!ingestionRuns.length && <p className="rounded-xl border border-dashed border-slate-300 p-4 text-xs text-slate-500">No ingestion-run receipt is available.</p>}</div></div>
        <div className="space-y-4"><section className="rounded-3xl border border-[#D8E6EF] bg-white p-5 shadow-sm"><h2 className="flex items-center gap-2 text-sm font-extrabold text-[#102A43]"><ShieldCheck className="h-4 w-4 text-[#0F9D8A]" />Deployment revision</h2><dl className="mt-3 space-y-2 text-xs"><div className="flex justify-between gap-3"><dt className="text-slate-500">Backend revision</dt><dd className="font-mono text-slate-800">{state.health?.backend_revision || 'Not supplied'}</dd></div><div className="flex justify-between gap-3"><dt className="text-slate-500">Model artifact</dt><dd className="text-right font-semibold text-slate-800">{state.health?.model_version || 'Not available'}</dd></div><div className="flex justify-between gap-3"><dt className="text-slate-500">Model loaded</dt><dd className="font-semibold text-slate-800">{state.health?.model_loaded ? 'Yes' : 'No'}</dd></div><div className="flex justify-between gap-3"><dt className="text-slate-500">Continuous history ready</dt><dd className="font-semibold text-slate-800">{state.health?.continuous_history_ready ? 'Yes' : 'No'}</dd></div></dl></section><section className="rounded-3xl border border-sky-200 bg-sky-50 p-5"><h2 className="flex items-center gap-2 text-sm font-extrabold text-sky-950"><Clock3 className="h-4 w-4" />No invented runtime metrics</h2><p className="mt-2 text-xs leading-5 text-sky-900">Latency and throughput are shown only after a measured benchmark artifact is available. A successful health probe is connectivity evidence, not an accuracy or performance result.</p></section></div>
      </section>
    </main>
  );
}
