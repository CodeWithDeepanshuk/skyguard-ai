'use client';

import React from 'react';
import { MeteorologicalParameter } from '@/lib/types';
import { formatResidual } from '@/lib/formatters';
import { Activity, ArrowDownRight, ArrowUpRight, Gauge, Thermometer, Waves } from 'lucide-react';
import { Tooltip, SCIENTIFIC_EXPLANATIONS } from '@/components/common/Tooltip';

interface SensorMetricCardProps {
  parameter: MeteorologicalParameter;
  observedValue: number | null;
  expectedValue: number | null;
  residual: number | null;
  robustZ: number | null;
  statusLabel: string;
  isAnomaly?: boolean;
}

export function SensorMetricCard({
  parameter,
  observedValue,
  expectedValue,
  residual,
  robustZ,
  statusLabel,
  isAnomaly = false,
}: SensorMetricCardProps) {
  const meta = {
    temperature: {
      name: 'Surface Air Temperature',
      unit: '°C',
      icon: Thermometer,
      accent: 'text-amber-600',
      border: isAnomaly ? 'border-rose-300 bg-rose-50/50' : 'border-slate-200 bg-white',
    },
    pressure: {
      name: 'Station Atmospheric Pressure',
      unit: 'hPa',
      icon: Gauge,
      accent: 'text-blue-600',
      border: isAnomaly ? 'border-rose-300 bg-rose-50/50' : 'border-slate-200 bg-white',
    },
    relative_humidity: {
      name: 'Relative Humidity',
      unit: '%',
      icon: Waves,
      accent: 'text-indigo-600',
      border: isAnomaly ? 'border-rose-300 bg-rose-50/50' : 'border-slate-200 bg-white',
    },
    multi_sensor: {
      name: 'Multi-Sensor Coherence',
      unit: '',
      icon: Activity,
      accent: 'text-purple-600',
      border: isAnomaly ? 'border-purple-300 bg-purple-50/50' : 'border-slate-200 bg-white',
    },
  }[parameter];

  const Icon = meta.icon;

  return (
    <div className={`rounded-xl border p-3.5 transition-all shadow-xs card-lift ${meta.border}`}>
      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-2 text-xs">
        <div className="flex items-center gap-1.5 font-bold text-slate-800">
          <Icon className={`w-4 h-4 ${meta.accent}`} />
          <span>{meta.name}</span>
        </div>
        <span
          className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
            isAnomaly
              ? 'bg-rose-50 text-rose-800 border-rose-300 font-bold'
              : 'bg-emerald-50 text-emerald-800 border-emerald-300 font-medium'
          }`}
        >
          {statusLabel}
        </span>
      </div>

      {/* Main Observed Value */}
      <div className="flex items-baseline justify-between mt-1">
        <div>
          <div className="text-[11px] text-slate-500 font-mono">Observed Value</div>
          <div className="text-xl font-extrabold font-mono text-slate-900 tracking-tight">
            {observedValue !== null ? `${observedValue.toFixed(1)}${meta.unit}` : '—'}
          </div>
        </div>

        <div className="text-right">
          <div className="text-[11px] text-slate-500 font-mono">Neighbour Consensus</div>
          <div className="text-sm font-semibold font-mono text-slate-700">
            {expectedValue !== null ? `${expectedValue.toFixed(1)}${meta.unit}` : '—'}
          </div>
        </div>
      </div>

      {/* Residual & Robust Z Strip */}
      <div className="grid grid-cols-2 gap-2 mt-3 pt-2.5 border-t border-slate-100 text-[11px] font-mono">
        <div>
          <span className="text-slate-500 block text-[10px]">
            <Tooltip label="Spatial Residual" content={SCIENTIFIC_EXPLANATIONS.SPATIAL_RESIDUAL} scientificTerm />
          </span>
          <span className={`font-bold ${isAnomaly ? 'text-rose-600' : 'text-slate-900'}`}>
            {formatResidual(residual, meta.unit)}
          </span>
        </div>

        <div>
          <span className="text-slate-500 block text-[10px]">
            <Tooltip label="Robust Z-Score" content={SCIENTIFIC_EXPLANATIONS.ROBUST_Z} scientificTerm />
          </span>
          <span className={`font-bold ${Math.abs(robustZ ?? 0) > 3.0 ? 'text-rose-600' : 'text-slate-900'}`}>
            {robustZ !== null ? `${robustZ > 0 ? '+' : ''}${robustZ.toFixed(2)}` : '—'}
          </span>
        </div>
      </div>
    </div>
  );
}
