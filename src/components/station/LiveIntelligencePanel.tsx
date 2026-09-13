'use client';

import React from 'react';
import { StationObservation, IncidentRecord } from '@/lib/types';
import { QualityBadge, SeverityBadge } from '@/components/common/Badge';
import { formatAge } from '@/lib/formatters';
import { 
  AlertTriangle, 
  ArrowRight, 
  BrainCircuit, 
  Flame, 
  RadioTower, 
  ShieldAlert, 
  Sparkles, 
  TrendingUp 
} from 'lucide-react';

interface LiveIntelligencePanelProps {
  stations: StationObservation[];
  incidents: IncidentRecord[];
  onSelectStation: (station: StationObservation) => void;
}

export function LiveIntelligencePanel({
  stations,
  incidents,
  onSelectStation,
}: LiveIntelligencePanelProps) {
  // Filter top anomalous and watch stations
  const anomalousStations = stations
    .filter(
      (s) =>
        s.quality_state === 'CRITICAL' ||
        s.quality_state === 'MULTI_SENSOR_ANOMALY' ||
        s.quality_state === 'PROBABLE_FAULT' ||
        s.quality_state === 'WATCH'
    )
    .sort((a, b) => (b.anomaly_score ?? -1) - (a.anomaly_score ?? -1))
    .slice(0, 8);

  const topIncidents = incidents.slice(0, 5);

  // Deterministic briefing derived only from the returned station states.
  const criticalCount = stations.filter(s => ['PROBABLE_FAULT', 'CRITICAL', 'MULTI_SENSOR_ANOMALY'].includes(s.quality_state)).length;
  const watchCount = stations.filter(s => s.quality_state === 'WATCH').length;
  const reportingCount = stations.filter(s => s.observation_age_minutes !== null && s.observation_age_minutes <= 180).length;

  const briefText = criticalCount > 0
    ? `${criticalCount} station${criticalCount > 1 ? 's have' : ' has'} probable fault evidence requiring operator review. This is not a verified hardware diagnosis; open the station dossier to inspect temporal, spatial and physical evidence.`
    : `${reportingCount} catalog-mapped stations have observations in the current operational view. No station currently meets the probable-fault decision rule; stations without enough causal history remain explicitly marked as warming up.`;

  return (
    <div className="w-full h-full bg-slate-50/50 border-l border-slate-200 flex flex-col overflow-hidden select-none">
      {/* Panel Header */}
      <div className="p-3.5 border-b border-slate-200 bg-white flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BrainCircuit className="w-4 h-4 text-blue-600" />
          <h2 className="text-xs font-black uppercase tracking-wider text-slate-900">
            Operational Intelligence
          </h2>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 font-semibold">
          Ranked Priority
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* 1. SkyGuard Brief (Deterministic Natural Language Operations Briefing) */}
        <div className="bg-white border border-blue-200 rounded-xl p-3.5 shadow-xs relative overflow-hidden card-lift">
          <div className="flex items-center gap-2 text-blue-900 font-extrabold text-xs mb-1.5">
            <Sparkles className="w-3.5 h-3.5 text-blue-600" />
            <span>SkyGuard Operational Brief</span>
          </div>
          <p className="text-xs text-slate-700 leading-relaxed font-sans">
            {briefText}
          </p>
          <div className="flex items-center gap-2 mt-2.5 pt-2 border-t border-slate-100 text-[10px] font-mono text-slate-500">
            <span>Deterministic summary</span>
            <span>•</span>
            <span>Observation-backed</span>
            <span>•</span>
            <span className="text-blue-700 font-semibold">No generated readings</span>
          </div>
        </div>

        {/* 2. Ranked Anomalies Feed */}
        <div>
          <div className="flex items-center justify-between text-[11px] font-mono uppercase text-slate-500 mb-2 font-semibold">
            <span>Stations Requiring Attention</span>
            <span className="text-blue-700">{anomalousStations.length} Flagged</span>
          </div>

          {anomalousStations.length === 0 ? (
            <div className="p-4 bg-white border border-slate-200 rounded-xl text-center text-xs text-slate-500">
              Zero active anomalies detected in current working view.
            </div>
          ) : (
            <div className="space-y-1.5">
              {anomalousStations.map((stn, index) => {
                const isCritical = stn.quality_state === 'CRITICAL' || stn.quality_state === 'MULTI_SENSOR_ANOMALY';
                const score = stn.anomaly_score;

                return (
                  <button
                    key={stn.station_id}
                    onClick={() => onSelectStation(stn)}
                    className="w-full text-left p-2.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 hover:border-blue-300 transition-all flex items-center justify-between gap-3 group shadow-xs card-lift"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="font-mono text-[10px] text-slate-400 font-bold w-4">
                        {String(index + 1).padStart(2, '0')}
                      </span>
                      <div className="min-w-0">
                        <div className="font-bold text-slate-900 group-hover:text-blue-600 truncate text-xs">
                          {stn.station_name}
                        </div>
                        <div className="text-[10px] font-mono text-slate-500 flex items-center gap-1.5 mt-0.5">
                          <span>{stn.fault_type || 'Sensor Divergence'}</span>
                          <span>•</span>
                          <span>{formatAge(stn.observation_age_minutes)}</span>
                        </div>
                      </div>
                    </div>

                    <div className="text-right flex-shrink-0">
                      <span
                        className={`text-[11px] font-mono font-bold px-1.5 py-0.5 rounded border ${
                          isCritical
                            ? 'bg-rose-50 text-rose-800 border-rose-300'
                            : 'bg-amber-50 text-amber-800 border-amber-300'
                        }`}
                      >
                        {score === null || score === undefined ? 'Score N/A' : `Score ${score.toFixed(2)}`}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* 3. Top Active Incidents */}
        {topIncidents.length > 0 && (
          <div>
            <div className="flex items-center justify-between text-[11px] font-mono uppercase text-slate-500 mb-2 font-semibold">
              <span>Operational evidence incidents</span>
              <span className="text-rose-600 font-bold">{topIncidents.length} Active</span>
            </div>

            <div className="space-y-1.5">
              {topIncidents.map((inc) => (
                <div
                  key={inc.incident_id}
                  className="p-2.5 rounded-xl bg-white border border-rose-200 text-xs font-mono shadow-xs card-lift"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-slate-900">{inc.station_name}</span>
                    <SeverityBadge severity={inc.severity} />
                  </div>
                  <div className="text-[11px] text-slate-500 flex items-center justify-between">
                    <span>{inc.fault_class}</span>
                    <span className="text-blue-700 font-semibold">{inc.calibrated_probability_available ? 'Calibrated probability' : 'Evidence score only'}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
