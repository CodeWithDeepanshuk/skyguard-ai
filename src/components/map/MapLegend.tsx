'use client';

import React from 'react';

export type MapLayerType =
  | 'STATION_HEALTH'
  | 'TEMPERATURE'
  | 'PRESSURE'
  | 'RELATIVE_HUMIDITY'
  | 'ANOMALY_SCORE'
  | 'FRESHNESS';

const rows: Record<MapLayerType, Array<[string, string]>> = {
  STATION_HEALTH: [
    ['#0F9D8A', 'No anomaly detected'],
    ['#0EA5E9', 'Coherent regional weather'],
    ['#D97706', 'Watch, warm-up or delayed'],
    ['#DC4C4C', 'Probable/critical fault evidence'],
    ['#64748B', 'No recent observation / not assessed'],
  ],
  TEMPERATURE: [['#2563EB', 'Cooler'], ['#14B8A6', 'Moderate'], ['#F59E0B', 'Warm'], ['#DC4C4C', 'Hot']],
  PRESSURE: [['#4F46E5', 'Lower hPa'], ['#0EA5E9', 'Mid-range hPa'], ['#0F9D8A', 'Higher hPa']],
  RELATIVE_HUMIDITY: [['#D97706', 'Dry'], ['#0EA5E9', 'Moderate RH'], ['#2563EB', 'High RH']],
  ANOMALY_SCORE: [['#0F9D8A', 'Low evidence score'], ['#D97706', 'Review evidence'], ['#DC4C4C', 'Strong evidence score']],
  FRESHNESS: [['#0F9D8A', 'Fresh ≤90 min'], ['#D97706', 'Delayed / stale'], ['#64748B', 'No recent report']],
};

const titles: Record<MapLayerType, string> = {
  STATION_HEALTH: 'Operational QC state',
  TEMPERATURE: 'Observed temperature (°C)',
  PRESSURE: 'Observed pressure (hPa)',
  RELATIVE_HUMIDITY: 'Observed relative humidity (%)',
  ANOMALY_SCORE: 'Uncalibrated evidence score',
  FRESHNESS: 'Observation freshness',
};

export function MapLegend({ activeLayer }: { activeLayer: MapLayerType }) {
  return (
    <div className="min-w-[190px] rounded-xl border border-[#D8E6EF] bg-white/94 p-3 shadow-lg backdrop-blur-xl">
      <p className="mb-2 border-b border-slate-100 pb-1.5 text-[10px] font-bold uppercase tracking-wider text-[#102A43]">{titles[activeLayer]}</p>
      <div className="space-y-1.5">
        {rows[activeLayer].map(([colour, label]) => (
          <div key={label} className="flex items-center gap-2 text-[10px] text-[#52667A]">
            <span className="h-2.5 w-2.5 rounded-full border border-white shadow" style={{ backgroundColor: colour }} />
            <span>{label}</span>
          </div>
        ))}
        <div className="flex items-center gap-2 text-[10px] text-[#52667A]">
          <span className="h-2.5 w-2.5 rounded-full bg-slate-300" />
          <span>Value not available</span>
        </div>
      </div>
      {activeLayer === 'ANOMALY_SCORE' && <p className="mt-2 border-t border-slate-100 pt-2 text-[9px] leading-relaxed text-slate-500">This score is not a calibrated fault probability.</p>}
    </div>
  );
}
