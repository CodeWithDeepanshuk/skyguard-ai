'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  ShieldCheck, 
  Activity, 
  Radio, 
  Cpu, 
  ArrowUpRight, 
  CheckCircle2, 
  Gauge,
  Database,
  Layers3,
  Network,
  Info
} from 'lucide-react';

interface HealthData {
  status: string;
  ml_service: boolean;
  ml_backend_url?: string;
  retryable?: boolean;
  retry_after_seconds?: number | null;
  backend_revision?: string | null;
  compliance?: {
    problem_id: string;
    parameters: string[];
    policy: string;
  };
}

export default function Dashboard() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [stationCount, setStationCount] = useState<number | null>(null);

  // Three-signal contract preview. Production inference requires ordered history.
  const [testStation, setTestStation] = useState('43279099999'); // Chennai Intl
  const [testTemp, setTestTemp] = useState('32.4');
  const [testPress, setTestPress] = useState('1008.2');
  const [testHumidity, setTestHumidity] = useState('74.0');

  useEffect(() => {
    let cancelled = false;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let attempt = 0;

    const checkBackend = async () => {
      attempt += 1;
      try {
        const response = await fetch('/api/health', { cache: 'no-store' });
        const data: HealthData = await response.json();
        if (cancelled) return;
        setHealth(data);
        setLoading(false);
        if (!data.ml_service && attempt < 7) {
          // Render Free can take close to one minute to resume after an idle spin-down.
          const delaySeconds = Math.max(5, data.retry_after_seconds || 5);
          retryTimer = setTimeout(checkBackend, delaySeconds * 1000);
        }
      } catch {
        if (cancelled) return;
        setHealth({ status: 'degraded', ml_service: false, retryable: true });
        setLoading(false);
        if (attempt < 7) retryTimer = setTimeout(checkBackend, 5000);
      }
    };

    void checkBackend();
    void fetch('/api/stations', { cache: 'no-store' })
      .then(response => response.json())
      .then(rows => {
        if (!cancelled && Array.isArray(rows)) setStationCount(rows.length);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, []);

  const applyPreset = (temp: string, press: string, hum: string) => {
    setTestTemp(temp);
    setTestPress(press);
    setTestHumidity(hum);
  };

  const observationContractValid = Boolean(testStation.trim()) &&
    [testTemp, testPress, testHumidity].every(value => value.trim() !== '' && Number.isFinite(Number(value)));

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Judge-facing mission banner */}
      <section className="command-hero rounded-[28px] p-6 sm:p-8 lg:p-10">
        <div className="relative z-10 grid items-center gap-8 lg:grid-cols-[1.25fr_0.75fr]">
          <div>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-300/20 bg-cyan-300/[0.07] px-3 py-1.5 text-[11px] font-extrabold uppercase tracking-[0.16em] text-cyan-200">
              <Radio className="h-3.5 w-3.5 animate-pulse" />
              SIH 26073 · Operational anomaly intelligence
            </div>
            <h1 className="gradient-heading max-w-4xl text-4xl font-black leading-[1.04] tracking-[-0.045em] sm:text-5xl lg:text-[3.65rem]">
              Trust every weather reading.
            </h1>
            <p className="mt-5 max-w-3xl text-sm leading-7 text-slate-300 sm:text-[17px]">
              SkyGuard separates probable sensor faults from genuine weather using only temperature, pressure and relative humidity—then exposes the evidence behind every advisory.
            </p>
            <div className="mt-6 flex flex-wrap gap-2.5">
              <span className="data-chip inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-slate-200">
                <Database className="h-4 w-4 text-cyan-300" />
                <strong className="text-white">{stationCount ?? '—'}</strong> catalog stations
              </span>
              <span className="data-chip inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-slate-200">
                <Layers3 className="h-4 w-4 text-blue-300" />
                3-sensor physical contract
              </span>
              <span className="data-chip inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-slate-200">
                <ShieldCheck className="h-4 w-4 text-emerald-300" />
                Evidence-first alerting
              </span>
            </div>
          </div>

          <aside className="engine-card rounded-2xl p-5 sm:p-6" aria-label="Inference engine status">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className={`rounded-xl p-3 ${health?.ml_service ? 'bg-emerald-400/10 text-emerald-300' : 'bg-amber-400/10 text-amber-300'}`}>
                  <Cpu className={`h-6 w-6 ${loading ? 'animate-pulse' : ''}`} />
                </div>
                <div>
                  <p className="text-[10px] font-extrabold uppercase tracking-[0.18em] text-slate-500">Inference engine</p>
                  <p className="mt-1 text-sm font-extrabold text-white">
                    {health?.ml_service ? 'Connected · advisory mode' : loading ? 'Connecting securely…' : 'Waking · auto retry active'}
                  </p>
                </div>
              </div>
              <span className={`mt-1 h-2.5 w-2.5 rounded-full ${health?.ml_service ? 'bg-emerald-400 shadow-[0_0_16px_#34d399]' : 'bg-amber-400'} ${loading ? 'animate-pulse' : ''}`} />
            </div>

            <div className="my-5 h-px bg-gradient-to-r from-transparent via-cyan-100/15 to-transparent" />
            <div className="grid grid-cols-3 gap-2">
              {[
                ['T', 'Temperature', 'text-rose-300'],
                ['P', 'Pressure', 'text-blue-300'],
                ['RH', 'Humidity', 'text-cyan-300']
              ].map(([symbol, label, tone]) => (
                <div key={symbol} className="rounded-xl border border-white/[0.06] bg-white/[0.025] p-3 text-center">
                  <div className={`font-mono text-lg font-black ${tone}`}>{symbol}</div>
                  <div className="mt-1 text-[10px] font-semibold text-slate-500">{label}</div>
                </div>
              ))}
            </div>
            <div className="mt-5 flex items-center justify-between gap-4 rounded-xl border border-cyan-300/10 bg-[#03101c]/55 px-4 py-3">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">Decision context</p>
                <p className="mt-0.5 text-xs font-semibold text-slate-300">Causal history + spatial neighbours</p>
              </div>
              <div className="flex h-8 items-end gap-1" aria-hidden="true">
                {[12, 22, 16, 28, 20].map((height, index) => (
                  <span key={height} className="signal-bar" style={{ height, animationDelay: `${index * 110}ms` }} />
                ))}
              </div>
            </div>
          </aside>
        </div>
      </section>

      {/* Operational proof grid */}
      <section aria-label="Platform proof points" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="metric-card [--card-accent:#22d3ee] rounded-2xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-slate-400">National catalog</span>
            <Database className="h-5 w-5 text-cyan-300" />
          </div>
          <div className="font-mono text-3xl font-black tabular-nums text-white">{stationCount ?? '—'}</div>
          <p className="mt-1.5 text-xs leading-5 text-slate-400">Indian station coordinates available for network exploration</p>
        </div>

        <div className="metric-card [--card-accent:#60a5fa] rounded-2xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-slate-400">Allowed inputs</span>
            <Activity className="h-5 w-5 text-blue-300" />
          </div>
          <div className="font-mono text-3xl font-black tabular-nums text-white">03</div>
          <p className="mt-1.5 text-xs leading-5 text-slate-400">Temperature · Pressure · Relative humidity only</p>
        </div>

        <div className="metric-card [--card-accent:#a78bfa] rounded-2xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-slate-400">Promotion checks</span>
            <ShieldCheck className="h-5 w-5 text-violet-300" />
          </div>
          <div className="font-mono text-3xl font-black tabular-nums text-white">25</div>
          <p className="mt-1.5 text-xs leading-5 text-slate-400">Integrity, leakage, calibration and deployment gates</p>
        </div>

        <div className="metric-card [--card-accent:#34d399] rounded-2xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-slate-400">Service state</span>
            <Network className="h-5 w-5 text-emerald-300" />
          </div>
          <div className={`text-2xl font-black ${health?.ml_service ? 'text-emerald-300' : loading ? 'text-cyan-200' : 'text-amber-300'}`}>
            {health?.ml_service ? 'Connected' : loading ? 'Checking…' : 'Auto-retry'}
          </div>
          <p className="mt-1.5 text-xs leading-5 text-slate-400">Vercel control plane + Render inference service</p>
        </div>
      </section>

      <div className="integrity-strip flex flex-col gap-3 rounded-2xl px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <Info className="mt-0.5 h-5 w-5 shrink-0 text-blue-300" />
          <p className="text-xs leading-5 text-slate-300 sm:text-sm">
            <strong className="text-white">Scientific integrity guardrail:</strong> live outputs are advisory. Accuracy claims remain attached to their named offline holdout; catalog membership never implies a currently healthy sensor.
          </p>
        </div>
        <Link href="/analytics" className="shrink-0 text-xs font-bold text-cyan-300 transition hover:text-cyan-100">
          Inspect evidence →
        </Link>
      </div>

      {/* Input contract explorer: intentionally does not fake one-row ML output. */}
      <section className="glass-panel soft-grid-panel rounded-[24px] p-5 sm:p-7">
        <div className="mb-6 flex flex-col justify-between gap-4 border-b border-cyan-100/10 pb-5 lg:flex-row lg:items-center">
          <div>
            <div className="mb-2 text-[10px] font-extrabold uppercase tracking-[0.18em] text-cyan-300">Safe interaction zone</div>
            <h2 className="flex items-center gap-2 text-xl font-black text-white sm:text-2xl">
              <Gauge className="h-5 w-5 text-cyan-300" />
              Three-signal observation contract
            </h2>
            <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-400 sm:text-sm">
              Preview the exact payload accepted by SkyGuard. A trustworthy anomaly decision is shown only inside station telemetry, where ordered history and neighbouring observations are available.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="mr-1 text-[10px] font-extrabold uppercase tracking-wider text-slate-500">Signal presets</span>
            <button 
              type="button"
              onClick={() => applyPreset('32.4', '1008.2', '74.0')}
              className="rounded-lg border border-cyan-100/10 bg-white/[0.035] px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-emerald-300/30 hover:bg-emerald-400/[0.07] hover:text-emerald-200"
            >
              <span className="mr-1.5 text-emerald-300">●</span>Nominal
            </button>
            <button 
              type="button"
              onClick={() => applyPreset('58.5', '1008.0', '40.0')}
              className="rounded-lg border border-cyan-100/10 bg-white/[0.035] px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-amber-300/30 hover:bg-amber-400/[0.07] hover:text-amber-200"
            >
              <span className="mr-1.5 text-amber-300">●</span>Temperature spike
            </button>
            <button 
              type="button"
              onClick={() => applyPreset('28.0', '950.0', '85.0')}
              className="rounded-lg border border-cyan-100/10 bg-white/[0.035] px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-rose-300/30 hover:bg-rose-400/[0.07] hover:text-rose-200"
            >
              <span className="mr-1.5 text-rose-300">●</span>Pressure drop
            </button>
            <button 
              type="button"
              onClick={() => applyPreset('34.0', '985.0', '92.0')}
              className="rounded-lg border border-cyan-100/10 bg-white/[0.035] px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-violet-300/30 hover:bg-violet-400/[0.07] hover:text-violet-200"
            >
              <span className="mr-1.5 text-violet-300">●</span>Severe weather
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div>
            <label className="mb-1.5 block text-xs font-bold text-slate-300">Station ID</label>
            <input 
              type="text" 
              value={testStation} 
              onChange={e => setTestStation(e.target.value)}
              className="w-full rounded-xl border border-cyan-100/15 bg-[#040f1b]/80 px-3 py-2.5 font-mono text-sm text-white transition placeholder:text-slate-600 focus:border-cyan-400 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-bold text-slate-300">Temperature (°C)</label>
            <input 
              type="number" 
              step="0.1" 
              value={testTemp} 
              onChange={e => setTestTemp(e.target.value)}
              className="w-full rounded-xl border border-cyan-100/15 bg-[#040f1b]/80 px-3 py-2.5 font-mono text-sm text-white transition focus:border-rose-300 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-bold text-slate-300">Station Pressure (hPa)</label>
            <input 
              type="number" 
              step="0.1" 
              value={testPress} 
              onChange={e => setTestPress(e.target.value)}
              className="w-full rounded-xl border border-cyan-100/15 bg-[#040f1b]/80 px-3 py-2.5 font-mono text-sm text-white transition focus:border-blue-300 focus:outline-none"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-bold text-slate-300">Relative Humidity (%)</label>
            <input 
              type="number" 
              step="0.5" 
              value={testHumidity} 
              onChange={e => setTestHumidity(e.target.value)}
              className="w-full rounded-xl border border-cyan-100/15 bg-[#040f1b]/80 px-3 py-2.5 font-mono text-sm text-white transition focus:border-cyan-300 focus:outline-none"
            />
          </div>
        </div>

        <div className="flex flex-col gap-4 rounded-2xl border border-cyan-100/10 bg-[#040f1b]/65 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <CheckCircle2 className={`mt-0.5 h-5 w-5 shrink-0 ${observationContractValid ? 'text-emerald-300' : 'text-amber-300'}`} />
            <div>
              <p className="text-sm font-bold text-white">
                {observationContractValid ? 'Payload matches the three-signal contract' : 'Complete every field to validate the payload'}
              </p>
              <p className="mt-0.5 text-xs text-slate-500">No synthetic probability is produced from a context-free row.</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/stations" className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 px-4 py-2 text-xs font-extrabold text-white shadow-lg shadow-cyan-500/15 transition hover:-translate-y-0.5 hover:from-cyan-400 hover:to-blue-500">
              Open station telemetry
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
            <Link href="/validation" className="inline-flex min-h-10 items-center rounded-lg border border-cyan-100/15 bg-white/[0.035] px-4 py-2 text-xs font-bold text-slate-200 transition hover:border-cyan-300/30 hover:text-white">
              View verification gates
            </Link>
          </div>
        </div>
      </section>

      {/* Feature Sections Navigation */}
      <section aria-label="SkyGuard workspaces" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Link href="/stations" className="glass-panel group rounded-2xl p-5 transition-all hover:-translate-y-1 hover:border-cyan-300/35">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-bold uppercase text-cyan-400">Network Map</span>
            <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-cyan-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </div>
          <h3 className="text-lg font-bold text-white mb-1">All-India AWS Network</h3>
          <p className="text-xs text-slate-400">Station metadata, coordinates and available source observations.</p>
        </Link>

        <Link href="/incidents" className="glass-panel group rounded-2xl p-5 transition-all hover:-translate-y-1 hover:border-rose-300/30">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-bold uppercase text-rose-400">Alert Center</span>
            <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-rose-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </div>
          <h3 className="text-lg font-bold text-white mb-1">Incident Command</h3>
          <p className="text-xs text-slate-400">Stateful incident transitions with root-cause diagnostic rationales.</p>
        </Link>

        <Link href="/analytics" className="glass-panel group rounded-2xl p-5 transition-all hover:-translate-y-1 hover:border-emerald-300/30">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-bold uppercase text-emerald-400">Evidence</span>
            <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </div>
          <h3 className="text-lg font-bold text-white mb-1">Scientific Analytics</h3>
          <p className="text-xs text-slate-400">Verified benchmark scores from frozen 2024 holdout evaluations.</p>
        </Link>

        <Link href="/validation" className="glass-panel group rounded-2xl p-5 transition-all hover:-translate-y-1 hover:border-violet-300/30">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-bold uppercase text-purple-400">Compliance</span>
            <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-purple-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </div>
          <h3 className="text-lg font-bold text-white mb-1">25-Gate Verification</h3>
          <p className="text-xs text-slate-400">Full audit checklist and promotion gates from pipeline runs.</p>
        </Link>
      </section>
    </div>
  );
}
