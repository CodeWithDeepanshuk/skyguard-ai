'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowRight, BrainCircuit, Clock3, Database, GitBranch, Layers3, Network, Scale, ShieldCheck } from 'lucide-react';

interface MetricsPayload {
  benchmark?: {
    model_version?: string | null;
    feature_count?: number | null;
    input_parameters?: string[] | null;
    claim_scope?: string;
    tcn_role?: string | null;
    evaluation?: Record<string, any>;
  } | null;
}

const operationalStages = [
  ['A', 'Transport and schema QC', 'Duplicates, lateness, impossible time, missing fields and communication cadence are evaluated before sensor logic.'],
  ['B', 'Physical QC', 'Temperature, pressure and RH range/rate checks plus stuck-at and cross-parameter evidence.'],
  ['C', 'Causal temporal QC', 'Past-only rolling median/MAD, EWMA, freeze run and CUSUM evidence. No future observation enters its own baseline.'],
  ['D', 'Spatial buddy QC', 'Time-aligned neighbours, minimum support and pressure-type compatibility protect genuine regional weather.'],
  ['E', 'Decision and incident state', 'NORMAL, WEATHER, PROBABLE FAULT, COMMUNICATION or INSUFFICIENT CONTEXT; weak evidence remains SUSPECTED.'],
];

const researchModels = [
  ['LightGBM / CatBoost', 'Primary interpretable tabular research detectors', 'Retained because mixed temporal, spatial and missingness features are naturally tabular and SHAP-compatible.'],
  ['Causal TCN', 'Temporal challenger / advisory evidence', 'Evaluated on past-only sequences; it is not automatically trusted more than the tabular and physical evidence.'],
  ['LSTM autoencoder', 'Unsupervised challenger', 'Useful for unknown patterns, but reconstruction error is only an anomaly score and can learn faulty behaviour.'],
  ['Isolation Forest', 'Supporting novelty detector', 'Adds weak unsupervised evidence; never confirms a hardware failure by itself.'],
];

function metric(value: unknown): string {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(3) : 'Not available';
}

export default function ModelIntelligencePage() {
  const [metrics, setMetrics] = useState<MetricsPayload | null>(null);
  useEffect(() => { fetch('/api/metrics', { cache: 'no-store' }).then(response => response.ok ? response.json() : null).then(setMetrics).catch(() => setMetrics(null)); }, []);
  const benchmark = metrics?.benchmark;
  const time = benchmark?.evaluation?.time_test?.binary_fault_detection;
  const station = benchmark?.evaluation?.station_test?.binary_fault_detection;

  return (
    <main className="min-h-full space-y-5 bg-[#F5F9FC] p-4 sm:p-6">
      <section className="rounded-3xl border border-[#D8E6EF] bg-white/90 p-6 shadow-[0_20px_70px_-40px_rgba(23,105,170,.45)] backdrop-blur-xl">
        <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-[10px] font-bold uppercase tracking-[.18em] text-violet-800"><BrainCircuit className="h-3.5 w-3.5" /> Model intelligence</div>
        <h1 className="max-w-4xl text-3xl font-black tracking-tight text-[#102A43] sm:text-4xl">Hybrid evidence beats a single black box.</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-[#52667A]">The live service currently uses causal operational QC and exposes an uncalibrated evidence score. The trained Phase 10 ensemble remains a verified offline research baseline until provider-domain calibration and independent live fault labels are available.</p>
        <div className="mt-5 flex flex-wrap gap-2 text-[10px] font-bold"><span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-emerald-800">Operational QC online</span><span className="rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-violet-800">ML baseline: offline research</span><span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-amber-900">Live calibration unavailable</span></div>
      </section>

      <section className="rounded-3xl border border-[#D8E6EF] bg-white p-5 shadow-sm sm:p-6">
        <div className="flex items-center justify-between gap-3"><div><h2 className="flex items-center gap-2 text-lg font-extrabold text-[#102A43]"><GitBranch className="h-5 w-5 text-[#1769AA]" />Live causal decision path</h2><p className="mt-1 text-xs text-[#52667A]">Every stage can abstain when evidence is insufficient.</p></div><span className="rounded-full bg-emerald-50 px-3 py-1 text-[9px] font-bold uppercase text-emerald-800">Deployed path</span></div>
        <div className="mt-5 grid gap-3 lg:grid-cols-5">{operationalStages.map(([number, title, description], index) => <div key={number} className="relative rounded-2xl border border-slate-200 bg-slate-50 p-4"><span className="grid h-7 w-7 place-items-center rounded-lg bg-sky-100 font-mono text-[10px] font-black text-[#1769AA]">{number}</span><h3 className="mt-3 text-sm font-extrabold text-[#102A43]">{title}</h3><p className="mt-2 text-[11px] leading-5 text-[#52667A]">{description}</p>{index < operationalStages.length - 1 && <ArrowRight className="absolute -right-2.5 top-1/2 z-10 hidden h-5 w-5 rounded-full bg-white text-sky-400 lg:block" />}</div>)}</div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.05fr_.95fr]">
        <div className="rounded-3xl border border-[#D8E6EF] bg-white p-5 shadow-sm sm:p-6"><h2 className="flex items-center gap-2 text-lg font-extrabold text-[#102A43]"><Layers3 className="h-5 w-5 text-violet-600" />Offline research ensemble</h2><p className="mt-1 text-xs text-[#52667A]">Model version: {benchmark?.model_version || 'Artifact unavailable'} · feature count: {benchmark?.feature_count ?? 'Not available'}</p><div className="mt-4 space-y-3">{researchModels.map(([name, role, description]) => <div key={name} className="rounded-2xl border border-slate-200 p-4"><div className="flex flex-col justify-between gap-1 sm:flex-row"><h3 className="text-sm font-extrabold text-[#102A43]">{name}</h3><span className="text-[9px] font-bold uppercase text-violet-700">{role}</span></div><p className="mt-2 text-[11px] leading-5 text-[#52667A]">{description}</p></div>)}</div></div>
        <div className="space-y-4">
          <section className="rounded-3xl border border-[#D8E6EF] bg-white p-5 shadow-sm"><h2 className="flex items-center gap-2 text-sm font-extrabold text-[#102A43]"><Database className="h-4 w-4 text-[#1769AA]" />Strict input contract</h2><div className="mt-3 grid gap-2">{(benchmark?.input_parameters || ['temperature', 'pressure', 'relative humidity']).map(parameter => <div key={parameter} className="rounded-xl bg-[#EDF6FB] px-3 py-2 text-xs font-bold text-[#1769AA]">{parameter}</div>)}</div><p className="mt-3 text-[10px] leading-4 text-slate-500">Station ID, coordinates, timestamps, source and missingness support alignment. Wind, rain, dew point and forecast fields are not model inputs.</p></section>
          <section className="rounded-3xl border border-amber-200 bg-amber-50 p-5 shadow-sm"><h2 className="flex items-center gap-2 text-sm font-extrabold text-amber-950"><Clock3 className="h-4 w-4" />Cold-start policy</h2><ul className="mt-3 space-y-2 text-xs leading-5 text-amber-900"><li>Immediately: physical and transport QC.</li><li>With aligned peers: spatial disagreement evidence.</li><li>After ~24 h: short-term spike, freeze and drift evidence with a warm-up label.</li><li>After ~7–30 days: stronger degradation trend; seasonality needs longer history or transferred climatology.</li></ul></section>
        </div>
      </section>

      <section className="rounded-3xl border border-[#D8E6EF] bg-white p-5 shadow-sm sm:p-6"><div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center"><div><h2 className="flex items-center gap-2 text-lg font-extrabold text-[#102A43]"><Scale className="h-5 w-5 text-[#0F9D8A]" />Verified offline baseline</h2><p className="mt-1 text-xs text-[#52667A]">Fault-injected holdouts; not live-field accuracy.</p></div><span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-[9px] font-bold text-[#1769AA]">{benchmark?.claim_scope || 'Evidence unavailable'}</span></div><div className="mt-5 grid gap-3 md:grid-cols-2"><div className="rounded-2xl bg-[#EDF6FB] p-4"><h3 className="text-sm font-extrabold text-[#102A43]">2024 time holdout</h3><div className="mt-3 grid grid-cols-4 gap-2 text-center">{[['Precision', time?.precision], ['Recall', time?.recall], ['F1', time?.f1], ['AUCPR', time?.aucpr]].map(([label, value]) => <div key={String(label)}><strong className="block text-lg tabular-nums text-[#1769AA]">{metric(value)}</strong><span className="text-[9px] uppercase text-slate-500">{label}</span></div>)}</div></div><div className="rounded-2xl bg-violet-50 p-4"><h3 className="text-sm font-extrabold text-[#102A43]">Unseen-station holdout</h3><div className="mt-3 grid grid-cols-4 gap-2 text-center">{[['Precision', station?.precision], ['Recall', station?.recall], ['F1', station?.f1], ['AUCPR', station?.aucpr]].map(([label, value]) => <div key={String(label)}><strong className="block text-lg tabular-nums text-violet-700">{metric(value)}</strong><span className="text-[9px] uppercase text-slate-500">{label}</span></div>)}</div></div></div><div className="mt-4 flex gap-2 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-950"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />Unseen-station recall is the major weakness. More genuine Indian station history and independently labelled faults—not a bigger neural network alone—are needed to improve it credibly.</div></section>

      <section className="grid gap-4 md:grid-cols-3"><div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4"><ShieldCheck className="h-5 w-5 text-emerald-700" /><h3 className="mt-2 text-sm font-extrabold text-emerald-950">Explainable evidence</h3><p className="mt-1 text-xs leading-5 text-emerald-900">Physical, temporal and spatial signals are shown separately before an operator acts.</p></div><div className="rounded-2xl border border-sky-200 bg-sky-50 p-4"><Network className="h-5 w-5 text-sky-700" /><h3 className="mt-2 text-sm font-extrabold text-sky-950">Weather preservation</h3><p className="mt-1 text-xs leading-5 text-sky-900">Regional coherence reduces single-sensor blame during genuine widespread changes.</p></div><div className="rounded-2xl border border-violet-200 bg-violet-50 p-4"><BrainCircuit className="h-5 w-5 text-violet-700" /><h3 className="mt-2 text-sm font-extrabold text-violet-950">Honest uncertainty</h3><p className="mt-1 text-xs leading-5 text-violet-900">Uncalibrated live output is called an evidence score, never a fault probability.</p></div></section>
    </main>
  );
}
