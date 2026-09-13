'use client';

import React, { useEffect, useState } from 'react';
import { AlertTriangle, BarChart3, Clock3, Database, FlaskConical, RadioTower } from 'lucide-react';

function percent(value: unknown) {
  return typeof value === 'number' ? (value * 100).toFixed(1) + '%' : 'Not available';
}

function number(value: unknown, digits = 3) {
  return typeof value === 'number' ? value.toFixed(digits) : 'Not available';
}

function Metric({ label, value, tone = 'text-[#102A43]' }: { label: string; value: string; tone?: string }) {
  return <div className="rounded-xl border border-[#D8E6EF] bg-white p-3"><p className="text-[10px] uppercase tracking-wider text-[#52667A]">{label}</p><p className={'mt-1 text-lg font-black tabular-nums ' + tone}>{value}</p></div>;
}

function Holdout({ title, icon, data }: { title: string; icon: React.ReactNode; data: any }) {
  const metric = data?.binary_fault_detection;
  const episode = metric?.episode_detection;
  return (
    <section className="rounded-2xl border border-[#D8E6EF] bg-white/92 p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between border-b border-slate-100 pb-2">
        <h2 className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-[#102A43]">{icon}{title}</h2>
        <span className="text-[10px] font-mono text-slate-500">{typeof data?.rows === 'number' ? data.rows.toLocaleString('en-IN') + ' rows' : 'Rows not available'}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Metric label="Precision" value={percent(metric?.precision)} />
        <Metric label="Recall" value={percent(metric?.recall)} />
        <Metric label="F1" value={percent(metric?.f1)} tone="text-[#1769AA]" />
        <Metric label="AUCPR" value={number(metric?.aucpr)} />
        <Metric label="False alerts / station-day" value={number(metric?.false_alarms_per_station_day, 4)} />
        <Metric label="Fault episodes detected" value={typeof episode?.detected_episodes === 'number' && typeof episode?.episodes === 'number' ? episode.detected_episodes + ' / ' + episode.episodes : 'Not available'} />
        <Metric label="Episode recall" value={percent(episode?.recall)} />
        <Metric label="Median latency" value={typeof episode?.median_detection_latency_minutes === 'number' ? episode.median_detection_latency_minutes.toFixed(1) + ' min' : 'Not available'} />
      </div>
    </section>
  );
}

export default function ScientificAnalyticsPage() {
  const [metrics, setMetrics] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/metrics', { cache: 'no-store' })
      .then(async response => {
        const payload = await response.json();
        if (!response.ok || !payload.benchmark) throw new Error(payload.message || 'Verified benchmark unavailable.');
        setMetrics(payload.benchmark);
      })
      .catch(reason => setError(reason instanceof Error ? reason.message : 'Verified benchmark unavailable.'));
  }, []);

  const timeTest = metrics?.evaluation?.time_test;
  const stationTest = metrics?.evaluation?.station_test;
  const timeFaults = timeTest?.binary_fault_detection?.episode_detection?.per_fault_type || {};
  const stationFaults = stationTest?.binary_fault_detection?.episode_detection?.per_fault_type || {};

  return (
    <div className="flex-1 space-y-4 overflow-y-auto p-4 md:p-6">
      <header className="rounded-2xl border border-white/80 bg-white/82 p-5 shadow-[0_18px_50px_rgba(23,105,170,.08)] backdrop-blur-xl">
        <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[.2em] text-violet-700">Scientific evidence</p>
            <h1 className="mt-1 flex items-center gap-2 text-xl font-black text-[#102A43]"><BarChart3 className="h-5 w-5 text-[#1769AA]" />Verified Phase 10 offline benchmark</h1>
            <p className="mt-1 max-w-3xl text-xs leading-relaxed text-[#52667A]">Faults were injected into held-out historical observations. These results test the research detector; they are not accuracy claims for the live Indian field network.</p>
          </div>
          <span className="rounded-xl border border-violet-200 bg-violet-50 px-3 py-2 text-[10px] font-bold text-violet-800">RESEARCH / OFFLINE EVIDENCE</span>
        </div>
      </header>

      {error && <div className="flex gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900"><AlertTriangle className="h-4 w-4" />{error}</div>}
      {!metrics && !error && <div className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-xs text-sky-800">Loading verified artifacts…</div>}

      {metrics && <>
        <div className="grid gap-4 xl:grid-cols-2">
          <Holdout title="Unseen-station holdout" icon={<RadioTower className="h-4 w-4 text-[#1769AA]" />} data={stationTest} />
          <Holdout title="Future-time holdout" icon={<Clock3 className="h-4 w-4 text-[#0F9D8A]" />} data={timeTest} />
        </div>

        <section className="rounded-2xl border border-[#D8E6EF] bg-white/92 p-4 shadow-sm">
          <h2 className="text-xs font-black uppercase tracking-wider text-[#102A43]">Per-fault episode recall</h2>
          <p className="mt-1 text-[10px] text-[#52667A]">Exact values from reports/phase10_final.json. “Not available” is shown when an artifact does not contain the result.</p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[620px] text-left text-xs">
              <thead className="border-b border-slate-200 text-[10px] uppercase text-slate-500"><tr><th className="py-2">Fault type</th><th>Station holdout</th><th>Future-time holdout</th><th>Episodes (time)</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {Array.from(new Set([...Object.keys(stationFaults), ...Object.keys(timeFaults)])).sort().map(key => (
                  <tr key={key}><td className="py-2.5 font-semibold text-[#102A43]">{key.replaceAll('_', ' ')}</td><td>{percent(stationFaults[key]?.recall)}</td><td>{percent(timeFaults[key]?.recall)}</td><td>{typeof timeFaults[key]?.episodes === 'number' ? timeFaults[key].episodes : 'Not available'}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <div className="grid gap-4 lg:grid-cols-2">
          <section className="rounded-2xl border border-[#D8E6EF] bg-white/92 p-4 shadow-sm">
            <h2 className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-[#102A43]"><FlaskConical className="h-4 w-4 text-violet-600" />Decision and root-cause evidence</h2>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <Metric label="Time event macro F1" value={percent(timeTest?.event_decision?.macro_f1)} />
              <Metric label="Station event macro F1" value={percent(stationTest?.event_decision?.macro_f1)} />
              <Metric label="Time root-cause macro F1" value={percent(timeTest?.oracle_root_cause?.macro_f1)} />
              <Metric label="Station root-cause macro F1" value={percent(stationTest?.oracle_root_cause?.macro_f1)} />
            </div>
            <p className="mt-3 text-[10px] leading-relaxed text-slate-500">Root-cause metrics are oracle-conditioned in the artifact: they evaluate class diagnosis on labelled fault examples and must not be interpreted as end-to-end live diagnosis accuracy.</p>
          </section>

          <section className="rounded-2xl border border-[#D8E6EF] bg-white/92 p-4 shadow-sm">
            <h2 className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-[#102A43]"><Database className="h-4 w-4 text-[#1769AA]" />Unlabelled historical QC profile</h2>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <Metric label="Observations screened" value={typeof metrics.quality_control?.total_observations === 'number' ? metrics.quality_control.total_observations.toLocaleString('en-IN') : 'Not available'} />
              <Metric label="Rule alerts" value={typeof metrics.quality_control?.total_alerts === 'number' ? metrics.quality_control.total_alerts.toLocaleString('en-IN') : 'Not available'} />
              <Metric label="Alerts / 1,000" value={number(metrics.quality_control?.alerts_per_1000, 2)} />
              <Metric label="Screening throughput" value={typeof metrics.quality_control?.observations_per_second === 'number' ? metrics.quality_control.observations_per_second.toLocaleString('en-IN') + '/s' : 'Not available'} />
            </div>
            <p className="mt-3 text-[10px] leading-relaxed text-amber-800">{metrics.quality_control?.warning || 'Unlabelled alert counts do not measure accuracy.'}</p>
          </section>
        </div>

        <section className="rounded-2xl border border-sky-200 bg-sky-50/90 p-4 text-xs text-sky-950">
          <b>Model contract:</b> {metrics.model_version || 'Not available'} · {metrics.feature_count ?? 'N/A'} causal engineered features · inputs {Array.isArray(metrics.input_parameters) ? metrics.input_parameters.join(', ') : 'Not available'}. {metrics.tcn_role}
        </section>
      </>}
    </div>
  );
}
