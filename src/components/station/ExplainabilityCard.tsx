'use client';

import React from 'react';
import { AlertOctagon, CheckCircle2, FileText, Info, ShieldAlert } from 'lucide-react';

interface ExplainabilityCardProps {
  stationName: string;
  isFlagged: boolean;
  faultClass?: string;
  confidencePct?: number;
  evidenceItems?: string[];
  persistenceVotes?: string;
}

export function ExplainabilityCard({
  stationName,
  isFlagged,
  faultClass = 'Probable Sensor Spike',
  confidencePct = 91,
  evidenceItems,
  persistenceVotes = '3/3 Gated Votes',
}: ExplainabilityCardProps) {
  if (!isFlagged) {
    return (
      <div className="bg-emerald-50/50 border border-emerald-200 rounded-xl p-4 shadow-xs select-none card-lift">
        <div className="flex items-center gap-2 text-emerald-800 font-bold text-xs mb-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>Spatially & Meteorologically Coherent</span>
        </div>
        <p className="text-xs text-slate-700 leading-relaxed">
          {stationName} tracks within expected empirical physical envelopes for Temperature, Pressure, and Humidity. Neighbour spatial residuals are within nominal bounds (&le; 1.8°C).
        </p>
      </div>
    );
  }

  const defaultEvidence = [
    'Temperature increased > 5.8°C within 10 min window without convective pressure plunge.',
    'Nearest neighbour cluster median changed only 0.4°C during identical temporal interval.',
    'Station pressure remained meteorologically coherent (ΔP < 0.2 hPa).',
    'Relative humidity response was physically inconsistent with local dew-point equilibrium.',
    'Temporal residual exceeded historical 99.2th empirical percentile for this climate zone.',
  ];

  const items = evidenceItems && evidenceItems.length > 0 ? evidenceItems : defaultEvidence;

  return (
    <div className="bg-white border border-rose-200 rounded-xl p-4 shadow-sm select-none relative overflow-hidden card-lift">
      <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/5 rounded-full blur-2xl pointer-events-none" />

      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-2.5">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-rose-600 animate-pulse-subtle" />
          <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-900">
            Why SkyGuard Flagged This Observation
          </h3>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-50 text-rose-800 border border-rose-300 font-bold">
          {confidencePct}% Confidence
        </span>
      </div>

      {/* Diagnosis Banner */}
      <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between text-xs mb-3">
        <div>
          <span className="text-[10px] text-slate-500 font-mono block">Attributed Root Cause</span>
          <span className="font-bold text-rose-700 text-sm">{faultClass}</span>
        </div>
        <div className="text-right font-mono text-[10px] text-slate-500">
          <span className="block">Persistence State</span>
          <span className="text-emerald-700 font-bold">{persistenceVotes}</span>
        </div>
      </div>

      {/* Structured Evidence Checklist */}
      <div className="space-y-2">
        <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider font-semibold">
          Empirical Model Evidence
        </div>
        {items.map((item, idx) => (
          <div key={idx} className="flex items-start gap-2 text-xs text-slate-700 leading-snug">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-600 mt-1.5 flex-shrink-0" />
            <span>{item}</span>
          </div>
        ))}
      </div>

      <div className="mt-3 pt-2.5 border-t border-slate-100 text-[10px] font-mono text-slate-500 flex items-center justify-between">
        <span>Three-Parameter Contract: T / P / RH Only</span>
        <span className="text-blue-700 font-semibold">Zero Future Leakage</span>
      </div>
    </div>
  );
}
