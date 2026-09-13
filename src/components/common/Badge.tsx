'use client';

import React from 'react';
import { StationQualityState } from '@/lib/types';
import { AlertTriangle, CheckCircle2, Eye, HelpCircle, ShieldAlert, WifiOff } from 'lucide-react';

interface QualityBadgeProps {
  state: StationQualityState;
  showIcon?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function QualityBadge({ state, showIcon = true, size = 'sm' }: QualityBadgeProps) {
  const sizeClasses = {
    sm: 'text-[11px] px-2 py-0.5 gap-1 font-semibold',
    md: 'text-xs px-2.5 py-1 gap-1.5 font-bold',
    lg: 'text-sm px-3 py-1.5 gap-2 font-bold',
  }[size];

  switch (state) {
    case 'HEALTHY':
    case 'NO_ANOMALY_DETECTED':
      return (
        <span className={`inline-flex items-center rounded-full bg-emerald-50 text-emerald-800 border border-emerald-300 shadow-sm shadow-emerald-100 ${sizeClasses}`}>
          {showIcon && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />}
          No anomaly detected
        </span>
      );
    case 'GENUINE_WEATHER_EVENT':
      return (
        <span className={`inline-flex items-center rounded-full bg-sky-50 text-sky-800 border border-sky-300 ${sizeClasses}`}>
          {showIcon && <CheckCircle2 className="w-3.5 h-3.5 text-sky-600" />}
          Genuine weather event
        </span>
      );
    case 'WARMING_UP':
      return (
        <span className={`inline-flex items-center rounded-full bg-amber-50 text-amber-800 border border-amber-300 ${sizeClasses}`}>
          {showIcon && <Eye className="w-3.5 h-3.5 text-amber-600" />}
          Warming up
        </span>
      );
    case 'WATCH':
      return (
        <span className={`inline-flex items-center rounded-full bg-amber-50 text-amber-800 border border-amber-300 shadow-sm shadow-amber-100 ${sizeClasses}`}>
          {showIcon && <Eye className="w-3.5 h-3.5 text-amber-600" />}
          Watch
        </span>
      );
    case 'PROBABLE_FAULT':
      return (
        <span className={`inline-flex items-center rounded-full bg-orange-50 text-orange-800 border border-orange-300 shadow-sm shadow-orange-100 ${sizeClasses}`}>
          {showIcon && <AlertTriangle className="w-3.5 h-3.5 text-orange-600" />}
          Probable Fault
        </span>
      );
    case 'CRITICAL':
      return (
        <span className={`inline-flex items-center rounded-full bg-rose-50 text-rose-800 border border-rose-300 shadow-sm shadow-rose-100 ${sizeClasses}`}>
          {showIcon && <ShieldAlert className="w-3.5 h-3.5 text-rose-600 animate-pulse" />}
          Critical Anomaly
        </span>
      );
    case 'MULTI_SENSOR_ANOMALY':
      return (
        <span className={`inline-flex items-center rounded-full bg-purple-50 text-purple-800 border border-purple-300 shadow-sm shadow-purple-100 ${sizeClasses}`}>
          {showIcon && <ShieldAlert className="w-3.5 h-3.5 text-purple-600 animate-pulse" />}
          Multi-Sensor Failure
        </span>
      );
    case 'STALE':
    case 'DELAYED':
    case 'NO_RECENT_REPORT':
    case 'COMMUNICATION_FAILURE':
      return (
        <span className={`inline-flex items-center rounded-full bg-slate-100 text-slate-700 border border-slate-300 ${sizeClasses}`}>
          {showIcon && <WifiOff className="w-3.5 h-3.5 text-slate-500" />}
          {state === 'COMMUNICATION_FAILURE' ? 'Communication gap' : state === 'DELAYED' ? 'Delayed' : state === 'NO_RECENT_REPORT' ? 'No recent report' : 'Stale'}
        </span>
      );
    case 'NOT_OBSERVED_IN_STORE':
    case 'NOT_ASSESSED':
    case 'UNVERIFIED':
    default:
      return (
        <span className={`inline-flex items-center rounded-full bg-sky-50 text-sky-800 border border-sky-300 ${sizeClasses}`}>
          {showIcon && <HelpCircle className="w-3.5 h-3.5 text-sky-600" />}
          {state === 'NOT_OBSERVED_IN_STORE' ? 'Catalog only' : 'Not assessed'}
        </span>
      );
  }
}

export function SourceBadge({ source }: { source: string }) {
  const isImd = source.toUpperCase().includes('IMD');
  const isMetar = source.toUpperCase().includes('METAR');

  return (
    <span className={`inline-flex items-center text-[10px] font-mono uppercase tracking-wider px-1.5 py-0.5 rounded border font-semibold ${
      isImd 
        ? 'bg-blue-50 text-blue-700 border-blue-200' 
        : isMetar 
        ? 'bg-indigo-50 text-indigo-700 border-indigo-200' 
        : 'bg-slate-100 text-slate-700 border-slate-200'
    }`}>
      {source}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' }) {
  const styles = {
    CRITICAL: 'bg-rose-50 text-rose-800 border-rose-300 font-bold',
    HIGH: 'bg-orange-50 text-orange-800 border-orange-300 font-bold',
    MEDIUM: 'bg-amber-50 text-amber-800 border-amber-300 font-semibold',
    LOW: 'bg-slate-100 text-slate-700 border-slate-300',
  }[severity];

  return (
    <span className={`inline-flex items-center text-[10px] px-2 py-0.5 rounded-full border shadow-sm ${styles}`}>
      {severity}
    </span>
  );
}
