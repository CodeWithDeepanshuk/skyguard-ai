'use client';

import React from 'react';
import { StationObservation } from '@/lib/types';
import { QualityBadge, SourceBadge } from '@/components/common/Badge';
import { formatAge, formatCoord, formatTime } from '@/lib/formatters';
import { MapPin, Mountain, RadioTower, X } from 'lucide-react';

interface StationHeaderProps {
  station: StationObservation;
  timeMode: 'UTC' | 'IST';
  onClose: () => void;
}

export function StationHeader({ station, timeMode, onClose }: StationHeaderProps) {
  return (
    <div className="bg-white border-b border-slate-200 p-4 select-none">
      {/* Top action row */}
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <QualityBadge state={station.quality_state} size="md" />
          <SourceBadge source={station.source_type} />
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          title="Close Station Drawer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Station Name & Primary ID */}
      <h2 className="text-base font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
        <RadioTower className="w-4 h-4 text-blue-600 flex-shrink-0" />
        <span className="truncate">{station.station_name}</span>
      </h2>
      <div className="text-xs font-mono text-blue-700/90 mt-0.5 font-medium">
        Station ID: {station.station_id}
      </div>

      {/* Metadata Badges Strip */}
      <div className="flex flex-wrap items-center gap-3 mt-3 text-[11px] font-mono text-slate-500 border-t border-slate-100 pt-2.5">
        <div className="flex items-center gap-1 text-slate-700">
          <MapPin className="w-3 h-3 text-slate-400" />
          <span>{formatCoord(station.latitude, station.longitude)}</span>
        </div>

        <span className="text-slate-300">•</span>

        <div className="flex items-center gap-1 text-slate-700">
          <Mountain className="w-3 h-3 text-slate-400" />
          <span>{station.elevation === null ? 'Elevation not available' : `${station.elevation} m MSL`}</span>
        </div>

        <span className="text-slate-300">•</span>

        <div className="flex items-center gap-1">
          <span className="text-slate-500">Telemetry Age:</span>
          <span className="text-slate-900 font-semibold">{formatAge(station.observation_age_minutes)}</span>
        </div>
      </div>
    </div>
  );
}
