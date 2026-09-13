'use client';

import React from 'react';
import { AlertTriangle, CheckCircle2, Clock, Cpu, Eye, RadioTower, WifiOff } from 'lucide-react';
import { formatAge } from '@/lib/formatters';
import { OperationalNetworkKPIs } from '@/lib/types';

export function StatusBar({ kpis }: { kpis: OperationalNetworkKPIs; timeMode?: 'UTC' | 'IST' }) {
  const value = (item: number | null) => item === null ? 'N/A' : item.toLocaleString('en-IN');
  const divider = <span className="text-slate-300">|</span>;
  return (
    <div className="w-full bg-white/78 backdrop-blur-xl border-b border-[#D8E6EF] px-4 py-2 flex items-center justify-between gap-4 overflow-x-auto text-[11px] font-mono select-none shadow-sm">
      <div className="flex items-center gap-4 min-w-max">
        <div className="flex items-center gap-1.5"><RadioTower className="w-3.5 h-3.5 text-[#1769AA]" /><span className="text-slate-500">Catalog</span><strong>{value(kpis.catalog_stations)}</strong></div>
        {divider}
        <div className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-sky-500" /><span className="text-slate-500">Reporting ≤24h</span><strong className="text-[#1769AA]">{value(kpis.stations_reporting_now)}</strong></div>
        {divider}
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 text-emerald-700" title="No supported anomaly in available context"><CheckCircle2 className="w-3.5 h-3.5" />{value(kpis.healthy_count)} no signal</span>
          <span className="flex items-center gap-1 text-amber-700" title="Watch or station still warming up"><Eye className="w-3.5 h-3.5" />{value(kpis.watch_count)} watch/warm-up</span>
          <span className="flex items-center gap-1 text-orange-700" title="Probable fault evidence; operator review required"><AlertTriangle className="w-3.5 h-3.5" />{value(kpis.probable_fault_count)} probable</span>
          <span className="flex items-center gap-1 text-slate-600" title="Delayed, stale, silent or not observed"><WifiOff className="w-3.5 h-3.5" />{value(kpis.stale_count)} delayed/offline</span>
        </div>
        {divider}
        <div><span className="text-slate-500">Active evidence incidents </span><strong>{value(kpis.open_incidents)}</strong></div>
      </div>
      <div className="flex items-center gap-4 min-w-max text-slate-600">
        <span className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" />Median age <strong className="text-slate-900">{formatAge(kpis.median_data_age_minutes)}</strong></span>
        {divider}
        <span className="flex items-center gap-1.5"><Cpu className="w-3.5 h-3.5 text-[#1769AA]" />Service <strong className={kpis.engine_status === 'OPERATIONAL' ? 'text-emerald-700' : 'text-amber-700'}>{kpis.engine_status}</strong></span>
      </div>
    </div>
  );
}
