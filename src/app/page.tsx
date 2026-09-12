'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  ShieldCheck, 
  Activity, 
  AlertTriangle, 
  CloudRain, 
  Radio, 
  Cpu, 
  ChevronRight, 
  ArrowUpRight, 
  Play, 
  CheckCircle2, 
  XCircle,
  RefreshCw,
  Gauge
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

interface PredictionResponse {
  status: string;
  station_id: string;
  prediction: {
    decision_state: string;
    p_normal: number;
    p_weather: number;
    p_fault: number;
    severity: string;
  };
  diagnostics: {
    freeze_detected: boolean;
    transport_gap: boolean;
    regional_agreement: number;
    explanation: string;
  };
  backend_mode: string;
}

export default function Dashboard() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);

  // Anomaly testing sandbox state
  const [testStation, setTestStation] = useState('43279099999'); // Chennai Intl
  const [testTemp, setTestTemp] = useState('32.4');
  const [testPress, setTestPress] = useState('1008.2');
  const [testHumidity, setTestHumidity] = useState('74.0');
  const [evaluating, setEvaluating] = useState(false);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [predictionError, setPredictionError] = useState('');

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
    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, []);

  const handlePredict = async () => {
    setEvaluating(true);
    setPrediction(null);
    setPredictionError('');
    try {
      const res = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          station_id: testStation,
          temperature: parseFloat(testTemp),
          pressure: parseFloat(testPress),
          humidity: parseFloat(testHumidity),
          timestamp: new Date().toISOString()
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Inference is unavailable.');
      setPrediction(data);
    } catch (error) {
      setPredictionError(error instanceof Error ? error.message : 'Inference request failed');
    } finally {
      setEvaluating(false);
    }
  };

  const applyPreset = (temp: string, press: string, hum: string) => {
    setTestTemp(temp);
    setTestPress(press);
    setTestHumidity(hum);
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Banner */}
      <div className="rounded-2xl border border-[#1a4163] bg-gradient-to-r from-[#0c2234] via-[#0f2b42] to-[#071521] p-6 sm:p-8 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none"></div>
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-800/80 text-cyan-400 text-xs font-semibold">
              <Radio className="w-3.5 h-3.5 animate-pulse" />
              <span>SIH 26073 · Operational Anomaly Intelligence</span>
            </div>
            <h1 className="text-2xl sm:text-4xl font-black text-white tracking-tight">
              Trust Every Weather Reading.
            </h1>
            <p className="text-slate-300 max-w-2xl text-sm sm:text-base leading-relaxed">
              Explore the Indian station catalog and available METAR observations. Research models flag readings for review using temperature, pressure and relative humidity. Catalog coverage is not live sensor coverage.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row md:flex-col lg:flex-row items-start sm:items-center gap-3">
            <div className="bg-[#071521]/90 border border-[#1a4163] rounded-xl p-4 flex items-center space-x-3.5">
              <div className={`p-2.5 rounded-lg ${health?.ml_service ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
                <Cpu className={`w-5 h-5 ${loading ? 'animate-pulse' : ''}`} />
              </div>
              <div>
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Inference Engine</div>
                <div className="text-sm font-bold text-white flex items-center gap-1.5">
                  {health?.ml_service
                    ? 'ML service connected · research mode'
                    : loading
                    ? 'Connecting to ML service…'
                    : 'ML service waking · automatic retry'}
                  <span className={`w-2 h-2 rounded-full ${health?.ml_service ? 'bg-emerald-400' : 'bg-amber-400'} ${loading ? 'animate-pulse' : ''}`}></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Metric Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-[#1a4163] bg-[#0c2234] p-5 shadow-lg relative hover:border-cyan-500/50 transition-colors">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">Unseen-Station Precision</span>
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-black text-white">Not measured</div>
          <p className="text-xs text-slate-400 mt-1">Live precision requires independently verified fault labels</p>
        </div>

        <div className="rounded-xl border border-[#1a4163] bg-[#0c2234] p-5 shadow-lg relative hover:border-emerald-500/50 transition-colors">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">Detection Latency</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-black text-white">Not measured</div>
          <p className="text-xs text-slate-400 mt-1">Public-host runtime has not been benchmarked</p>
        </div>

        <div className="rounded-xl border border-[#1a4163] bg-[#0c2234] p-5 shadow-lg relative hover:border-amber-500/50 transition-colors">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">False Alert Rate</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-black text-white">Unverified</div>
          <p className="text-xs text-slate-400 mt-1">No live false-alarm guarantee is available</p>
        </div>

        <div className="rounded-xl border border-[#1a4163] bg-[#0c2234] p-5 shadow-lg relative hover:border-purple-500/50 transition-colors">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">Weather Veto Specificity</span>
            <CloudRain className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-black text-white">Research only</div>
          <p className="text-xs text-slate-400 mt-1">See offline validation; real weather events need independent review</p>
        </div>
      </div>

      {/* Interactive Inference Sandbox */}
      <div className="rounded-2xl border border-[#1a4163] bg-[#0c2234] p-6 shadow-xl">
        <div className="border-b border-[#1a4163] pb-4 mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2">
              <Gauge className="w-5 h-5 text-cyan-400" />
              Single-reading sandbox · not deployed
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
              A single reading cannot supply temporal history or neighbouring observations. Use station telemetry for the deployed history-based model.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-400 font-semibold mr-1">Presets:</span>
            <button 
              type="button"
              onClick={() => applyPreset('32.4', '1008.2', '74.0')}
              className="text-xs px-2.5 py-1 rounded bg-[#143652] text-slate-200 hover:bg-cyan-900 hover:text-cyan-200 border border-slate-700 transition"
            >
              Normal
            </button>
            <button 
              type="button"
              onClick={() => applyPreset('58.5', '1008.0', '40.0')}
              className="text-xs px-2.5 py-1 rounded bg-[#143652] text-amber-300 hover:bg-amber-950 border border-slate-700 transition"
            >
              🔥 Temp Spike
            </button>
            <button 
              type="button"
              onClick={() => applyPreset('28.0', '950.0', '85.0')}
              className="text-xs px-2.5 py-1 rounded bg-[#143652] text-rose-300 hover:bg-rose-950 border border-slate-700 transition"
            >
              📉 Pressure Drop
            </button>
            <button 
              type="button"
              onClick={() => applyPreset('34.0', '985.0', '92.0')}
              className="text-xs px-2.5 py-1 rounded bg-[#143652] text-sky-300 hover:bg-sky-950 border border-slate-700 transition"
            >
              ⛈️ Severe Weather
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Station ID</label>
            <input 
              type="text" 
              value={testStation} 
              onChange={e => setTestStation(e.target.value)}
              className="w-full bg-[#071521] border border-[#1a4163] rounded-lg px-3 py-2 text-sm text-white font-mono focus:border-cyan-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Temperature (°C)</label>
            <input 
              type="number" 
              step="0.1" 
              value={testTemp} 
              onChange={e => setTestTemp(e.target.value)}
              className="w-full bg-[#071521] border border-[#1a4163] rounded-lg px-3 py-2 text-sm text-white font-mono focus:border-cyan-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Station Pressure (hPa)</label>
            <input 
              type="number" 
              step="0.1" 
              value={testPress} 
              onChange={e => setTestPress(e.target.value)}
              className="w-full bg-[#071521] border border-[#1a4163] rounded-lg px-3 py-2 text-sm text-white font-mono focus:border-cyan-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Relative Humidity (%)</label>
            <input 
              type="number" 
              step="0.5" 
              value={testHumidity} 
              onChange={e => setTestHumidity(e.target.value)}
              className="w-full bg-[#071521] border border-[#1a4163] rounded-lg px-3 py-2 text-sm text-white font-mono focus:border-cyan-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={handlePredict}
            disabled={evaluating}
            className="flex items-center space-x-2 px-6 py-2.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-sm shadow-lg shadow-cyan-500/20 transition-all disabled:opacity-50"
          >
            {evaluating ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Evaluating...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Run SkyGuard Anomaly Inference</span>
              </>
            )}
          </button>
        </div>

        {/* Prediction Output Card */}
        {predictionError && <p role="alert" className="mt-4 text-amber-300">{predictionError}</p>}
        {prediction && (
          <div className="mt-6 rounded-xl border border-cyan-500/30 bg-[#071521] p-5 animate-slideDown">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1a4163] pb-4">
              <div>
                <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Decision State</span>
                <div className="text-xl font-black text-white flex items-center gap-2 mt-0.5">
                  <span className={`px-3 py-1 rounded-md text-xs font-extrabold uppercase ${
                    prediction.prediction.decision_state === 'NORMAL' 
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : prediction.prediction.decision_state === 'GENUINE_WEATHER_EVENT'
                      ? 'bg-cyan-950 text-cyan-400 border border-cyan-800'
                      : 'bg-rose-950 text-rose-400 border border-rose-800'
                  }`}>
                    {prediction.prediction.decision_state}
                  </span>
                  <span className="text-sm font-medium text-slate-400">Severity: {prediction.prediction.severity}</span>
                </div>
              </div>
              <div className="flex items-center space-x-4 text-xs font-mono">
                <div>
                  <span className="text-slate-500 block">P(Normal)</span>
                  <span className="text-emerald-400 font-bold">{(prediction.prediction.p_normal * 100).toFixed(1)}%</span>
                </div>
                <div>
                  <span className="text-slate-500 block">P(Weather)</span>
                  <span className="text-cyan-400 font-bold">{(prediction.prediction.p_weather * 100).toFixed(1)}%</span>
                </div>
                <div>
                  <span className="text-slate-500 block">P(Fault)</span>
                  <span className="text-rose-400 font-bold">{(prediction.prediction.p_fault * 100).toFixed(1)}%</span>
                </div>
              </div>
            </div>

            <div className="mt-4 text-xs text-slate-300">
              <strong className="text-cyan-400">Diagnostic Explanation: </strong>
              {prediction.diagnostics.explanation}
            </div>
          </div>
        )}
      </div>

      {/* Feature Sections Navigation */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link href="/stations" className="group rounded-xl border border-[#1a4163] bg-[#0c2234] p-5 hover:border-cyan-500/50 hover:bg-[#0f2b42] transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-bold uppercase text-cyan-400">Network Map</span>
            <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-cyan-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </div>
          <h3 className="text-lg font-bold text-white mb-1">All-India AWS Network</h3>
          <p className="text-xs text-slate-400">Station metadata, coordinates and available source observations.</p>
        </Link>

        <Link href="/incidents" className="group rounded-xl border border-[#1a4163] bg-[#0c2234] p-5 hover:border-cyan-500/50 hover:bg-[#0f2b42] transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-bold uppercase text-rose-400">Alert Center</span>
            <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-rose-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </div>
          <h3 className="text-lg font-bold text-white mb-1">Incident Command</h3>
          <p className="text-xs text-slate-400">Stateful incident transitions with root-cause diagnostic rationales.</p>
        </Link>

        <Link href="/analytics" className="group rounded-xl border border-[#1a4163] bg-[#0c2234] p-5 hover:border-cyan-500/50 hover:bg-[#0f2b42] transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-bold uppercase text-emerald-400">Evidence</span>
            <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </div>
          <h3 className="text-lg font-bold text-white mb-1">Scientific Analytics</h3>
          <p className="text-xs text-slate-400">Verified benchmark scores from frozen 2024 holdout evaluations.</p>
        </Link>

        <Link href="/validation" className="group rounded-xl border border-[#1a4163] bg-[#0c2234] p-5 hover:border-cyan-500/50 hover:bg-[#0f2b42] transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-bold uppercase text-purple-400">Compliance</span>
            <ArrowUpRight className="w-4 h-4 text-slate-400 group-hover:text-purple-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </div>
          <h3 className="text-lg font-bold text-white mb-1">25-Gate Verification</h3>
          <p className="text-xs text-slate-400">Full audit checklist and promotion gates from pipeline runs.</p>
        </Link>
      </div>
    </div>
  );
}
