'use client';

import React from 'react';
import { Clock3, RadioTower } from 'lucide-react';
import { formatTime } from '@/lib/formatters';

export function TimeScrubber({
  timeMode,
  latestObservationUtc = null,
  reportingCount = 0,
}: {
  timeMode: 'UTC' | 'IST';
  latestObservationUtc?: string | null;
  reportingCount?: number;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-[#D8E6EF] bg-white/94 px-4 py-2.5 shadow-xl backdrop-blur-xl sm:flex-row sm:items-center sm:justify-between">
      <span className="flex items-center gap-2 text-[10px] font-semibold text-[#52667A]"><RadioTower className="h-3.5 w-3.5 text-[#0F9D8A]" />{reportingCount.toLocaleString('en-IN')} stations with stored observations</span>
      <span className="flex items-center gap-2 text-[10px] font-mono text-[#102A43]"><Clock3 className="h-3.5 w-3.5 text-[#1769AA]" />Latest received observation: {latestObservationUtc ? formatTime(latestObservationUtc, timeMode) : 'Not available'}</span>
    </div>
  );
}
