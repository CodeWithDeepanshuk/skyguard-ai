'use client';

import React, { useState } from 'react';
import { HelpCircle } from 'lucide-react';

interface TooltipProps {
  label: React.ReactNode;
  content: string;
  scientificTerm?: boolean;
}

export function Tooltip({ label, content, scientificTerm = false }: TooltipProps) {
  const [visible, setVisible] = useState(false);

  return (
    <span className="relative inline-flex items-center gap-1 group cursor-help">
      <span className={scientificTerm ? 'border-b border-dotted border-blue-500' : ''}>
        {label}
      </span>
      {scientificTerm && <HelpCircle className="w-3 h-3 text-blue-600" />}

      <span
        className={`absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 text-xs text-slate-700 bg-white border border-slate-200 rounded-xl shadow-xl shadow-slate-300/40 pointer-events-none transition-all duration-150 z-50 ${
          visible ? 'opacity-100 visible' : 'opacity-0 invisible group-hover:opacity-100 group-hover:visible'
        }`}
      >
        <span className="block font-bold text-blue-700 mb-1">Scientific Definition</span>
        <span className="text-[11px] leading-relaxed block">{content}</span>
        <span className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-white" />
      </span>
    </span>
  );
}

export const SCIENTIFIC_EXPLANATIONS: Record<string, string> = {
  SPATIAL_RESIDUAL: 'Difference between the target station observation and its robust distance-weighted neighbour consensus.',
  ROBUST_Z: 'Modified Z-score using median and Median Absolute Deviation (MAD), resilient against severe outlier contamination.',
  ECE: 'Expected Calibration Error measures how closely predicted confidence matches empirical event frequency.',
  PERSISTENCE_GATE: 'Temporal state machine requiring k=3 anomalous observations in a rolling window of n=5 before promoting to confirmed incident.',
  THREE_PARAMETER: 'Strict physical contract evaluating only Air Temperature [°C], Station Pressure [hPa], and Relative Humidity [%].',
  CUSUM_DRIFT: 'Two-sided Cumulative Sum detector sensitive to slow sensor degradation and calibration decalibration.',
};
