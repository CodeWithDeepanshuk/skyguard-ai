'use client';

import React, { useState } from 'react';
import { CloudLightning, Cpu, ShieldCheck, ShieldAlert, CheckCircle2 } from 'lucide-react';

export function WeatherVsFaultCard() {
  const [mode, setMode] = useState<'SENSOR_FAULT' | 'GENUINE_WEATHER'>('SENSOR_FAULT');

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs select-none card-lift">
      {/* Header with Mode Toggle */}
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-blue-600" />
          <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-900">
            Weather Event vs Sensor Fault
          </h3>
        </div>

        {/* Demo Mode Toggle */}
        <div className="flex items-center bg-slate-100 border border-slate-200 rounded-lg p-0.5 text-[10px] font-mono">
          <button
            onClick={() => setMode('SENSOR_FAULT')}
            className={`px-2 py-0.5 rounded transition-all ${
              mode === 'SENSOR_FAULT' ? 'bg-white text-rose-700 font-bold shadow-xs' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Sensor Spike
          </button>
          <button
            onClick={() => setMode('GENUINE_WEATHER')}
            className={`px-2 py-0.5 rounded transition-all ${
              mode === 'GENUINE_WEATHER' ? 'bg-white text-emerald-700 font-bold shadow-xs' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Weather Front
          </button>
        </div>
      </div>

      {mode === 'SENSOR_FAULT' ? (
        /* Sensor Fault Case */
        <div className="space-y-3">
          <div className="p-3 bg-rose-50/50 border border-rose-200 rounded-lg">
            <div className="flex items-center justify-between text-xs font-mono mb-2">
              <span className="text-slate-500">Target Station</span>
              <span className="text-rose-700 font-bold text-sm">37.8°C (↑ +5.7°C Residual)</span>
            </div>

            <div className="text-[11px] font-mono text-slate-500 mb-1 font-semibold">
              Neighbour AWS Cluster (Within 45 km):
            </div>
            <div className="grid grid-cols-4 gap-1.5 text-center text-xs font-mono">
              <div className="p-1 rounded bg-white text-slate-800 border border-slate-200 font-semibold">31.8°C</div>
              <div className="p-1 rounded bg-white text-slate-800 border border-slate-200 font-semibold">32.0°C</div>
              <div className="p-1 rounded bg-white text-slate-800 border border-slate-200 font-semibold">31.7°C</div>
              <div className="p-1 rounded bg-white text-slate-800 border border-slate-200 font-semibold">31.9°C</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
            <div className="p-2 bg-slate-50 rounded border border-slate-200">
              <span className="text-slate-500 block text-[10px]">Regional Coherence:</span>
              <span className="font-bold text-emerald-700">HIGH (Peers Agree)</span>
            </div>
            <div className="p-2 bg-slate-50 rounded border border-slate-200">
              <span className="text-slate-500 block text-[10px]">Model Evaluation:</span>
              <span className="font-bold text-rose-700">Isolated Sensor Anomaly</span>
            </div>
          </div>

          <div className="p-2 rounded bg-slate-50 border border-rose-200 text-[11px] text-slate-700 leading-tight">
            <strong className="text-rose-700">Decision:</strong> Target diverges markedly while surrounding stations remain stationary. Verified as physical sensor anomaly. Incident promoted.
          </div>
        </div>
      ) : (
        /* Genuine Weather Event Case */
        <div className="space-y-3">
          <div className="p-3 bg-emerald-50/50 border border-emerald-200 rounded-lg">
            <div className="flex items-center justify-between text-xs font-mono mb-2">
              <span className="text-slate-500">Target Station (Gust Front)</span>
              <span className="text-emerald-700 font-bold text-sm">24.2°C (↓ -6.1°C Plunge)</span>
            </div>

            <div className="text-[11px] font-mono text-slate-500 mb-1 font-semibold">
              Neighbour AWS Cluster (Concurrently Plunging):
            </div>
            <div className="grid grid-cols-4 gap-1.5 text-center text-xs font-mono">
              <div className="p-1 rounded bg-white text-slate-800 border border-slate-200 font-semibold">24.5°C</div>
              <div className="p-1 rounded bg-white text-slate-800 border border-slate-200 font-semibold">23.9°C</div>
              <div className="p-1 rounded bg-white text-slate-800 border border-slate-200 font-semibold">24.8°C</div>
              <div className="p-1 rounded bg-white text-slate-800 border border-slate-200 font-semibold">24.1°C</div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
            <div className="p-2 bg-slate-50 rounded border border-slate-200">
              <span className="text-slate-500 block text-[10px]">Spatial Consistency:</span>
              <span className="font-bold text-emerald-700">COHERENT SHIFT</span>
            </div>
            <div className="p-2 bg-slate-50 rounded border border-slate-200">
              <span className="text-slate-500 block text-[10px]">Model Evaluation:</span>
              <span className="font-bold text-blue-700">Genuine Frontal Transition</span>
            </div>
          </div>

          <div className="p-2 rounded bg-slate-50 border border-emerald-200 text-[11px] text-slate-700 leading-tight">
            <strong className="text-emerald-700">Decision:</strong> Multiple stations shifting simultaneously in pressure and temperature. Spatial buddy QC vetoes alert. Zero false alarms generated.
          </div>
        </div>
      )}
    </div>
  );
}
