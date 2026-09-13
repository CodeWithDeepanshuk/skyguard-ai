'use client';

import React from 'react';
import { NeighbourStation } from '@/lib/types';
import { formatTemp } from '@/lib/formatters';
import { Compass, Users, CheckCircle2 } from 'lucide-react';
import { Tooltip, SCIENTIFIC_EXPLANATIONS } from '@/components/common/Tooltip';

interface NeighbourConsensusProps {
  targetTemp: number | null;
  expectedTemp: number | null;
  spatialResidual: number | null;
  neighbourAgreementPct: number;
  modelConfidencePct: number;
  nearestNeighbours: NeighbourStation[];
}

export function NeighbourConsensus({
  targetTemp,
  expectedTemp,
  spatialResidual,
  neighbourAgreementPct,
  modelConfidencePct,
  nearestNeighbours,
}: NeighbourConsensusProps) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs select-none card-lift">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-blue-600" />
          <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-900">
            Spatial Neighbour Consensus
          </h3>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 font-semibold">
          Geodesic Buddy Check
        </span>
      </div>

      {/* KPI Comparison Strip */}
      <div className="grid grid-cols-3 gap-2 p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-center text-xs font-mono mb-3">
        <div>
          <span className="text-[10px] text-slate-500 block">Agreement</span>
          <span className="font-bold text-emerald-700 text-sm">{neighbourAgreementPct}%</span>
        </div>
        <div>
          <span className="text-[10px] text-slate-500 block">Spatial Residual</span>
          <span className={`font-bold text-sm ${Math.abs(spatialResidual ?? 0) > 3 ? 'text-rose-600' : 'text-slate-900'}`}>
            {spatialResidual !== null ? `${spatialResidual > 0 ? '+' : ''}${spatialResidual.toFixed(1)}°C` : '—'}
          </span>
        </div>
        <div>
          <span className="text-[10px] text-slate-500 block">Model Confidence</span>
          <span className="font-bold text-blue-700 text-sm">{modelConfidencePct}%</span>
        </div>
      </div>

      {/* Nearest Reporting Physical Neighbours List */}
      <div>
        <div className="text-[11px] font-mono text-slate-500 mb-1.5 flex items-center justify-between font-semibold">
          <span>Nearest Valid Physical AWS</span>
          <span>Distance (Haversine)</span>
        </div>

        {nearestNeighbours.length === 0 ? (
          <div className="text-xs text-slate-400 italic py-2 text-center">
            No active physical neighbours within 250 km radius.
          </div>
        ) : (
          <div className="space-y-1.5">
            {nearestNeighbours.map((nb) => (
              <div
                key={nb.station_id}
                className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs font-mono hover:border-blue-300 transition-colors"
              >
                <div className="flex items-center gap-2 truncate pr-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0" />
                  <span className="text-slate-800 font-semibold truncate">{nb.station_name}</span>
                </div>
                <div className="flex items-center gap-3 text-right flex-shrink-0">
                  <span className="text-slate-900 font-bold">{formatTemp(nb.temperature_c)}</span>
                  <span className="text-slate-500 text-[10px] w-14">{nb.distance_km} km</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
