'use client';

import React, { useState } from 'react';
import { Layers, Minus, Mountain, Plus, RotateCcw } from 'lucide-react';
import { MapLayerType } from './MapLegend';

const layers: Array<{ id: MapLayerType; label: string }> = [
  { id: 'STATION_HEALTH', label: 'Operational QC state' },
  { id: 'TEMPERATURE', label: 'Observed temperature' },
  { id: 'PRESSURE', label: 'Observed pressure' },
  { id: 'RELATIVE_HUMIDITY', label: 'Observed relative humidity' },
  { id: 'ANOMALY_SCORE', label: 'Anomaly evidence score' },
  { id: 'FRESHNESS', label: 'Observation freshness' },
];

export function MapToolbar({
  activeLayer,
  setActiveLayer,
  showTerrainContext,
  setShowTerrainContext,
  onZoomIn,
  onZoomOut,
  onResetView,
}: {
  activeLayer: MapLayerType;
  setActiveLayer: (layer: MapLayerType) => void;
  showTerrainContext?: boolean;
  setShowTerrainContext?: (show: boolean) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetView: () => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="flex items-start gap-2">
      <div className="relative">
        <button onClick={() => setOpen(value => !value)} className="min-h-11 rounded-xl border border-[#D8E6EF] bg-white/95 px-3 text-xs font-semibold text-[#102A43] shadow-lg backdrop-blur-xl">
          <Layers className="mr-2 inline h-4 w-4 text-[#1769AA]" />{layers.find(layer => layer.id === activeLayer)?.label}
        </button>
        {open && (
          <div className="absolute left-0 top-12 w-64 overflow-hidden rounded-xl border border-[#D8E6EF] bg-white shadow-2xl">
            {layers.map(layer => (
              <button key={layer.id} onClick={() => { setActiveLayer(layer.id); setOpen(false); }} className={activeLayer === layer.id ? 'block min-h-11 w-full bg-sky-50 px-3 text-left text-xs font-bold text-[#1769AA]' : 'block min-h-11 w-full px-3 text-left text-xs text-[#52667A] hover:bg-slate-50'}>
                {layer.label}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="flex overflow-hidden rounded-xl border border-[#D8E6EF] bg-white/95 shadow-lg">
        <button onClick={onZoomIn} className="grid min-h-11 min-w-11 place-items-center hover:bg-sky-50" aria-label="Zoom in"><Plus className="h-4 w-4" /></button>
        <button onClick={onZoomOut} className="grid min-h-11 min-w-11 place-items-center border-l border-slate-100 hover:bg-sky-50" aria-label="Zoom out"><Minus className="h-4 w-4" /></button>
        <button onClick={onResetView} className="grid min-h-11 min-w-11 place-items-center border-l border-slate-100 hover:bg-sky-50" aria-label="Reset India view"><RotateCcw className="h-4 w-4" /></button>
        {setShowTerrainContext && (
          <button
            onClick={() => setShowTerrainContext(!showTerrainContext)}
            className={`grid min-h-11 min-w-11 place-items-center border-l border-slate-100 ${
              showTerrainContext ? 'bg-sky-100 text-[#1769AA]' : 'hover:bg-sky-50 text-[#52667A]'
            }`}
            aria-label="Toggle terrain context"
            title="Toggle terrain context"
          >
            <Mountain className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
