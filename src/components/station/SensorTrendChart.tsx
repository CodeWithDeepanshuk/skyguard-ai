'use client';

import React, { useState } from 'react';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid, 
  ReferenceLine 
} from 'recharts';
import { TelemetryPoint } from '@/lib/types';

interface SensorTrendChartProps {
  data: TelemetryPoint[];
  stationName: string;
}

export function SensorTrendChart({ data, stationName }: SensorTrendChartProps) {
  const [activeParam, setActiveParam] = useState<'temp' | 'pressure' | 'rh'>('temp');

  const paramConfig = {
    temp: {
      name: 'Temperature (°C)',
      observedKey: 'observed_temp',
      neighbourKey: 'neighbour_temp',
      modelKey: 'model_temp',
      unit: '°C',
      domain: ['auto', 'auto'],
      strokeObserved: '#d97706', // Warm Amber
      strokeNeighbour: '#2563eb', // Royal Cobalt
      strokeModel: '#7c3aed', // Amethyst Violet
    },
    pressure: {
      name: 'Pressure (hPa)',
      observedKey: 'observed_pressure',
      neighbourKey: 'neighbour_pressure',
      modelKey: 'model_pressure',
      unit: 'hPa',
      domain: ['auto', 'auto'],
      strokeObserved: '#2563eb',
      strokeNeighbour: '#059669', // Alpine Emerald
      strokeModel: '#4f46e5',
    },
    rh: {
      name: 'Relative Humidity (%)',
      observedKey: 'observed_rh',
      neighbourKey: 'neighbour_rh',
      modelKey: 'model_rh',
      unit: '%',
      domain: [0, 100],
      strokeObserved: '#0284c7',
      strokeNeighbour: '#16a34a',
      strokeModel: '#9333ea',
    },
  }[activeParam];
  const hasNeighbourTrace = data.some((row: any) => row[paramConfig.neighbourKey] !== null && row[paramConfig.neighbourKey] !== undefined);
  const hasReferenceTrace = data.some((row: any) => row[paramConfig.modelKey] !== null && row[paramConfig.modelKey] !== undefined);

  // Custom Light Tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white border border-slate-200 rounded-lg p-2.5 shadow-xl text-xs font-mono select-none">
          <div className="text-[10px] text-slate-500 mb-1 border-b border-slate-100 pb-0.5 font-bold">
            {label}
          </div>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center justify-between gap-3 text-[11px] py-0.5">
              <span className="flex items-center gap-1.5" style={{ color: entry.color }}>
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
                <span>{entry.name}:</span>
              </span>
              <span className="font-bold text-slate-900">
                {entry.value !== undefined && entry.value !== null ? `${Number(entry.value).toFixed(1)} ${paramConfig.unit}` : '—'}
              </span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs select-none card-lift">
      {/* Chart Header & Parameter Selector */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div>
          <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-900">
            Causal telemetry history
          </h3>
          <p className="text-[10px] font-mono text-slate-500">
            Stored observations only; comparison traces appear only when supplied
          </p>
        </div>

        {/* Parameter Toggle */}
        <div className="flex items-center bg-slate-100 border border-slate-200 rounded-lg p-0.5 text-xs font-mono">
          <button
            onClick={() => setActiveParam('temp')}
            className={`px-2 py-0.5 rounded transition-all ${
              activeParam === 'temp' ? 'bg-white text-amber-700 font-bold shadow-xs' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Temp (T)
          </button>
          <button
            onClick={() => setActiveParam('pressure')}
            className={`px-2 py-0.5 rounded transition-all ${
              activeParam === 'pressure' ? 'bg-white text-blue-700 font-bold shadow-xs' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Pressure (P)
          </button>
          <button
            onClick={() => setActiveParam('rh')}
            className={`px-2 py-0.5 rounded transition-all ${
              activeParam === 'rh' ? 'bg-white text-indigo-700 font-bold shadow-xs' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            RH (%)
          </button>
        </div>
      </div>

      {/* Synchronized Recharts Canvas */}
      <div className="h-56 w-full mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="timestamp_utc"
              tickFormatter={(v) => v.slice(11, 16)}
              stroke="#94a3b8"
              tick={{ fontSize: 10, fontFamily: 'monospace', fill: '#64748b' }}
            />
            <YAxis
              domain={paramConfig.domain as any}
              stroke="#94a3b8"
              tick={{ fontSize: 10, fontFamily: 'monospace', fill: '#64748b' }}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Traces */}
            {hasNeighbourTrace && <Line
              type="monotone"
              dataKey={paramConfig.observedKey}
              name="Target Station (Observed)"
              stroke={paramConfig.strokeObserved}
              strokeWidth={2.5}
              dot={{ r: 2.5, fill: paramConfig.strokeObserved }}
              activeDot={{ r: 5 }}
            />}
            {hasReferenceTrace && <Line
              type="monotone"
              dataKey={paramConfig.neighbourKey}
              name="Neighbour Median Consensus"
              stroke={paramConfig.strokeNeighbour}
              strokeWidth={2}
              strokeDasharray="4 2"
              dot={false}
            />}
            <Line
              type="monotone"
              dataKey={paramConfig.modelKey}
              name="Reference Weather Field"
              stroke={paramConfig.strokeModel}
              strokeWidth={1.5}
              strokeDasharray="2 2"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Legend Strip */}
      <div className="flex flex-wrap items-center justify-center gap-4 mt-3 pt-2 border-t border-slate-100 text-[10px] font-mono">
        {hasNeighbourTrace && <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-amber-600" />
          <span className="text-slate-700">Target Station</span>
        </div>}
        {hasReferenceTrace && <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-blue-600 border-t border-dashed" />
          <span className="text-slate-700">Neighbour Consensus</span>
        </div>}
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-violet-600 border-t border-dotted" />
          <span className="text-slate-500">Context Reanalysis</span>
        </div>
      </div>
    </div>
  );
}
