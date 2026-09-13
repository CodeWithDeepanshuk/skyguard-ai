'use client';

import React from 'react';
import { 
  ArrowDown, 
  CheckCircle2, 
  Database, 
  FileCheck, 
  Layers, 
  Network, 
  Radio, 
  ShieldCheck, 
  Workflow 
} from 'lucide-react';
import { Tooltip, SCIENTIFIC_EXPLANATIONS } from '@/components/common/Tooltip';

export default function DataSourcesPage() {
  const pipelineSteps = [
    { num: '01', name: 'Raw Telemetry Ingestion', desc: 'Direct ingestion via IMD WIS2, METAR aviation feeds, and physical AWS loggers.' },
    { num: '02', name: 'Schema & Identity Validation', desc: 'Station coordinates, elevation MSL, WMO ID resolution, and corrupt frame filtering.' },
    { num: '03', name: 'Time Normalization', desc: 'Strict UTC timestamping, clock-drift correction, and duplicate packet deduplication.' },
    { num: '04', name: 'Physical QC Range Checks', desc: 'NOAA MADIS-grade physical boundaries (T: -50 to +60°C, P: 800 to 1080 hPa, RH: 0 to 100%).' },
    { num: '05', name: 'Causal Temporal Features', desc: '108 causal rolling features (diurnal tendencies, acceleration, quantization dwell, CUSUM).' },
    { num: '06', name: 'Spatial Neighbour Graph', desc: 'Haversine geodesic buddy check (k=5 neighbours) computing spatial residuals and agreement.' },
    { num: '07', name: 'Multi-Model ML Ensemble', desc: 'PyTorch Causal TCN (3 dilated blocks) + LightGBM Spatial Buddy Trees + Specialist Detectors.' },
    { num: '08', name: 'Isotonic Calibration', desc: 'Maps raw neural log-odds into empirically calibrated probabilities (ECE 0.0085).' },
    { num: '09', name: 'Persistence Gate (k=3, n=5)', desc: 'Temporal state machine requiring 3 confirmations in 5 observations before alert promotion.' },
    { num: '10', name: 'Incident Command Emission', desc: 'Dispatches confirmed fault dossier to field operations with root-cause attribution.' },
  ];

  const sources = [
    {
      source: 'IMD AWS',
      type: 'Direct In-Situ Physical',
      coverage: 'All-India AWS & ARG Network',
      latestFetch: 'Live (< 15 min)',
      latency: '15 min',
      stationCount: '410 Active',
      status: 'PRIMARY PHYSICAL',
      fallbackPriority: 'Priority 1 (Ground Truth)',
      statusColor: 'text-emerald-700 border-emerald-300 bg-emerald-50',
    },
    {
      source: 'IMD WIS 2.0 (SYNOP)',
      type: 'WMO Global Exchange',
      coverage: 'Indian Principal Meteorological Stations',
      latestFetch: 'Live (< 30 min)',
      latency: '30 min',
      stationCount: '133 Stations',
      status: 'OFFICIAL SYNOP',
      fallbackPriority: 'Priority 2 (WMO Baseline)',
      statusColor: 'text-blue-700 border-blue-300 bg-blue-50',
    },
    {
      source: 'Aviation METAR',
      type: 'ICAO Airport Observatories',
      coverage: 'Major Indian Civil & Military Airports',
      latestFetch: 'Live (< 30 min)',
      latency: '30 min',
      stationCount: '52 Airports',
      status: 'AIRPORT METAR',
      fallbackPriority: 'Priority 3 (Calibrated Baseline)',
      statusColor: 'text-sky-700 border-sky-300 bg-sky-50',
    },
    {
      source: 'MOSDAC / Reanalysis',
      type: 'Satellite & Numerical Context',
      coverage: 'Indian Subcontinent & Oceanic Grid',
      latestFetch: 'Hourly Reanalysis',
      latency: '60 min',
      stationCount: 'Grid Coverage',
      status: 'CONTEXT ONLY',
      fallbackPriority: 'External Reference (Not ML Input)',
      statusColor: 'text-violet-700 border-violet-300 bg-violet-50',
    },
    {
      source: 'Internal Evaluation Archive',
      type: 'Historical Frozen Dataset',
      coverage: '578,450 Verified Observations (2022–2024)',
      latestFetch: 'Immutable Frozen Benchmark',
      latency: '0 ms (Local)',
      stationCount: '543 Catalog',
      status: 'SCIENTIFIC BENCHMARK',
      fallbackPriority: 'Ground Truth Holdout',
      statusColor: 'text-slate-700 border-slate-300 bg-slate-100',
    },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 select-none font-sans bg-slate-50 min-h-full">
      {/* Header */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4 card-lift">
        <div>
          <div className="flex items-center gap-2.5 text-slate-900 font-extrabold text-lg tracking-tight">
            <div className="w-9 h-9 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center shadow-sm">
              <Database className="w-5 h-5 text-blue-600" />
            </div>
            <h1>Data Sources, Ingestion Pipeline & Scientific Provenance</h1>
          </div>
          <p className="text-xs text-slate-500 font-mono mt-1">
            Transparent telemetry provenance and multi-stage causal quality-control pipeline (SIH 26073).
          </p>
        </div>

        <div className="px-3.5 py-1.5 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 text-xs font-mono font-bold shadow-sm self-start sm:self-auto">
          Strict Provenance Tracking
        </div>
      </div>

      {/* 1. End-to-End Ingestion-to-Incident Pipeline Visual */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-sm space-y-4 card-lift">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Workflow className="w-4 h-4 text-blue-600" />
            <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-800">
              End-to-End Operational Intelligence Pipeline
            </h3>
          </div>
          <span className="text-[11px] font-mono font-bold text-emerald-600 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
            10 Verified Causal Stages
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {pipelineSteps.map((step) => (
            <div
              key={step.num}
              className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex flex-col justify-between hover:border-blue-300 hover:bg-blue-50/20 transition-all card-lift"
            >
              <div>
                <span className="text-[10px] font-mono text-blue-600 font-bold block mb-1">
                  STAGE {step.num}
                </span>
                <h4 className="text-xs font-bold text-slate-900 mb-1.5">{step.name}</h4>
                <p className="text-[11px] text-slate-500 font-sans leading-relaxed">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 2. Source Inventory Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm card-lift">
        <div className="p-4 bg-slate-50/80 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-blue-600" />
            <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-800">
              Multi-Provider Telemetry Sources & Fallback Priority
            </h3>
          </div>
          <span className="text-[10px] font-mono text-slate-500 font-semibold">Zero Unverified Data Ingestion</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse font-mono">
            <thead className="bg-slate-50 border-b border-slate-200 text-[11px] text-slate-500 font-bold">
              <tr>
                <th className="py-3 px-4">Data Source</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">Geographic Coverage</th>
                <th className="py-3 px-4">Latency</th>
                <th className="py-3 px-4">Fleet Count</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Role</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-[11px]">
              {sources.map((s) => (
                <tr key={s.source} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 px-4 font-bold text-slate-900">{s.source}</td>
                  <td className="py-3 px-4 text-slate-600 font-sans">{s.type}</td>
                  <td className="py-3 px-4 text-slate-700 font-sans">{s.coverage}</td>
                  <td className="py-3 px-4 text-blue-600 font-bold">{s.latency}</td>
                  <td className="py-3 px-4 text-slate-800 font-semibold">{s.stationCount}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold border shadow-xs ${s.statusColor}`}>
                      {s.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-500 font-sans">{s.fallbackPriority}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 3. Scientific Rules & Provenance Contract Box */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-sm space-y-4 card-lift">
        <div className="flex items-center gap-2 text-blue-800 font-bold text-xs uppercase font-mono border-b border-slate-100 pb-2">
          <ShieldCheck className="w-4 h-4 text-blue-600" />
          <span>Strict Three-Parameter Physical Contract & Pressure Semantics</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 card-lift">
            <span className="text-amber-700 font-bold block mb-1">1. Air Temperature (°C)</span>
            <p className="text-[11px] text-slate-600 font-sans leading-relaxed">
              Standard 2-metre aspirated physical sensor readings. Differentiates rapid convective frontal plunges from unphysical spikes and flatlines.
            </p>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 card-lift">
            <span className="text-blue-700 font-bold block mb-1">2. Station Pressure (hPa)</span>
            <p className="text-[11px] text-slate-600 font-sans leading-relaxed">
              True station-level barometric pressure (P_station). Explicit elevation-invariant tendency calculation prevents mixing P_station with altimeter QNH or MSLP.
            </p>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 card-lift">
            <span className="text-violet-700 font-bold block mb-1">3. Relative Humidity (%)</span>
            <p className="text-[11px] text-slate-600 font-sans leading-relaxed">
              Capacitive relative humidity. Explicitly flagged as derived from dew point when ingesting METAR fallbacks. Zero uncalibrated cross-substitution.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
