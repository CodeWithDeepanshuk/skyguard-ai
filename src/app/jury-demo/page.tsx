'use client';

import React, { useState } from 'react';
import { 
  AlertTriangle, 
  CheckCircle2, 
  CloudLightning, 
  CloudSun, 
  Cpu, 
  FlaskConical, 
  Gauge, 
  Info, 
  MapPin, 
  Mountain, 
  Play, 
  RefreshCw, 
  ShieldAlert, 
  ShieldCheck, 
  Sliders, 
  Thermometer, 
  Waves, 
  Wrench 
} from 'lucide-react';

interface NeighborState {
  station_id: string;
  name: string;
  distance_km: number;
  elevation: number;
  temperature: number;
  pressure: number;
  humidity: number;
  is_coastal: boolean;
}

interface EvaluationResult {
  decision: string;
  severity: string;
  anomaly_score: number;
  fault_probability: number;
  root_cause: string;
  root_cause_explanation?: string;
  fault_signature_hypothesis?: string;
  recommended_technician_action?: string;
  engine?: string;
  evidence?: {
    neural_reconstruction_score?: number;
    temporal_drift_score?: number;
    spatial_consensus_score?: number;
    expected_values?: { temperature?: number; pressure?: number; humidity?: number };
    residuals?: { temperature?: number; pressure?: number; humidity?: number };
    neighbor_count?: number;
    tier1_20km?: { count: number; max_delta?: number; tolerance: number };
    tier2_50km?: { count: number; max_delta?: number; tolerance: number };
    tier3_100km?: { count: number; max_delta?: number; tolerance: number };
    climate_zone?: string;
    is_coastal?: boolean;
    synoptic_weather_detected?: boolean;
  };
}

const PRESET_SCENARIOS = [
  {
    id: 'nominal',
    title: 'Nominal Atmospheric State',
    subtitle: 'Consensus across Tier 1, 2, and 3 concentric rings',
    icon: CloudSun,
    badgeColor: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    data: {
      station_id: 'DELHI_SAF',
      name: 'Delhi Safdarjung (Target)',
      temperature: 30.2,
      pressure: 1005.0,
      humidity: 62.0,
      elevation: 216.0,
      climate_zone: 'Indo-Gangetic Plains',
      is_coastal: false,
      history: [
        { temperature: 29.8, pressure: 1005.2, humidity: 64.0 },
        { temperature: 30.0, pressure: 1005.1, humidity: 63.0 },
      ],
      neighbors: [
        { station_id: 'DELHI_PALAM', name: 'Delhi Palam Airport', distance_km: 14.0, elevation: 230.0, temperature: 30.0, pressure: 1004.8, humidity: 63.0, is_coastal: false },
        { station_id: 'NOIDA_SEC62', name: 'Noida Observation Stn', distance_km: 24.0, elevation: 205.0, temperature: 30.5, pressure: 1005.3, humidity: 61.0, is_coastal: false },
        { station_id: 'MEERUT_OBS', name: 'Meerut Met Office', distance_km: 68.0, elevation: 220.0, temperature: 29.8, pressure: 1004.9, humidity: 64.0, is_coastal: false },
      ],
    },
  },
  {
    id: 'sensor_outlier',
    title: 'Temperature Sensor Outlier',
    subtitle: 'Single station diverges +7.6°C from Tier 1 neighbors',
    icon: AlertTriangle,
    badgeColor: 'border-rose-200 bg-rose-50 text-rose-800',
    data: {
      station_id: 'DELHI_SAF',
      name: 'Delhi Safdarjung (Target)',
      temperature: 37.8,
      pressure: 1005.0,
      humidity: 62.0,
      elevation: 216.0,
      climate_zone: 'Indo-Gangetic Plains',
      is_coastal: false,
      history: [
        { temperature: 30.0, pressure: 1005.2, humidity: 64.0 },
        { temperature: 30.1, pressure: 1005.1, humidity: 63.0 },
      ],
      neighbors: [
        { station_id: 'DELHI_PALAM', name: 'Delhi Palam Airport', distance_km: 14.0, elevation: 230.0, temperature: 30.0, pressure: 1004.8, humidity: 63.0, is_coastal: false },
        { station_id: 'NOIDA_SEC62', name: 'Noida Observation Stn', distance_km: 24.0, elevation: 205.0, temperature: 30.2, pressure: 1005.3, humidity: 61.0, is_coastal: false },
        { station_id: 'MEERUT_OBS', name: 'Meerut Met Office', distance_km: 68.0, elevation: 220.0, temperature: 29.8, pressure: 1004.9, humidity: 64.0, is_coastal: false },
      ],
    },
  },
  {
    id: 'thunderstorm',
    title: 'Severe Thunderstorm Front',
    subtitle: 'Coherent regional temperature drop (Suppresses false alarm!)',
    icon: CloudLightning,
    badgeColor: 'border-sky-200 bg-sky-50 text-sky-800',
    data: {
      station_id: 'DELHI_SAF',
      name: 'Delhi Safdarjung (Target)',
      temperature: 24.2,
      pressure: 1001.0,
      humidity: 89.0,
      elevation: 216.0,
      climate_zone: 'Indo-Gangetic Plains',
      is_coastal: false,
      history: [
        { temperature: 32.5, pressure: 1006.0, humidity: 55.0 },
        { temperature: 29.0, pressure: 1003.5, humidity: 72.0 },
      ],
      neighbors: [
        { station_id: 'DELHI_PALAM', name: 'Delhi Palam Airport', distance_km: 14.0, elevation: 230.0, temperature: 24.0, pressure: 1001.2, humidity: 88.0, is_coastal: false },
        { station_id: 'NOIDA_SEC62', name: 'Noida Observation Stn', distance_km: 24.0, elevation: 205.0, temperature: 24.5, pressure: 1001.5, humidity: 86.0, is_coastal: false },
        { station_id: 'MEERUT_OBS', name: 'Meerut Met Office', distance_km: 68.0, elevation: 220.0, temperature: 23.8, pressure: 1000.8, humidity: 90.0, is_coastal: false },
      ],
    },
  },
  {
    id: 'flatline',
    title: 'Stuck Sensor Flatline (ADC Jam)',
    subtitle: 'Five identical float readings repeated across time',
    icon: Cpu,
    badgeColor: 'border-amber-200 bg-amber-50 text-amber-800',
    data: {
      station_id: 'JAIPUR_SANGANER',
      name: 'Jaipur Sanganer AWS',
      temperature: 28.4,
      pressure: 980.0,
      humidity: 45.0,
      elevation: 390.0,
      climate_zone: 'Western Arid & Semi-Arid',
      is_coastal: false,
      history: [
        { temperature: 28.4, pressure: 980.0, humidity: 45.0 },
        { temperature: 28.4, pressure: 980.0, humidity: 45.0 },
        { temperature: 28.4, pressure: 980.0, humidity: 45.0 },
        { temperature: 28.4, pressure: 980.0, humidity: 45.0 },
        { temperature: 28.4, pressure: 980.0, humidity: 45.0 },
      ],
      neighbors: [
        { station_id: 'JAIPUR_CITY', name: 'Jaipur City Obs', distance_km: 12.0, elevation: 430.0, temperature: 31.2, pressure: 978.0, humidity: 40.0, is_coastal: false },
        { station_id: 'AJMER_AWS', name: 'Ajmer Station', distance_km: 48.0, elevation: 480.0, temperature: 32.0, pressure: 972.0, humidity: 38.0, is_coastal: false },
      ],
    },
  },
  {
    id: 'himalayas',
    title: 'High-Altitude Station (Leh)',
    subtitle: 'Elevation barometric scaling (675 hPa at 3,500m ASL)',
    icon: Mountain,
    badgeColor: 'border-indigo-200 bg-indigo-50 text-indigo-800',
    data: {
      station_id: 'LEH_HIMALAYAS',
      name: 'Leh Surface AWS',
      temperature: 12.0,
      pressure: 675.0,
      humidity: 30.0,
      elevation: 3500.0,
      climate_zone: 'Northern Himalayas',
      is_coastal: false,
      history: [
        { temperature: 11.5, pressure: 676.0, humidity: 32.0 },
      ],
      neighbors: [
        { station_id: 'KARGIL_AWS', name: 'Kargil Surface Stn', distance_km: 85.0, elevation: 2676.0, temperature: 15.0, pressure: 740.0, humidity: 34.0, is_coastal: false },
      ],
    },
  },
];

export default function JuryDemoPage() {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('nominal');
  const [stationId, setStationId] = useState<string>('DELHI_SAF');
  const [stationName, setStationName] = useState<string>('Delhi Safdarjung (Target)');
  const [temperature, setTemperature] = useState<number>(30.2);
  const [pressure, setPressure] = useState<number>(1005.0);
  const [humidity, setHumidity] = useState<number>(62.0);
  const [elevation, setElevation] = useState<number>(216.0);
  const [climateZone, setClimateZone] = useState<string>('Indo-Gangetic Plains');
  const [isCoastal, setIsCoastal] = useState<boolean>(false);

  const [history, setHistory] = useState<Array<{ temperature: number; pressure: number; humidity: number }>>([
    { temperature: 29.8, pressure: 1005.2, humidity: 64.0 },
    { temperature: 30.0, pressure: 1005.1, humidity: 63.0 },
  ]);

  const [neighbors, setNeighbors] = useState<NeighborState[]>([
    { station_id: 'DELHI_PALAM', name: 'Delhi Palam Airport', distance_km: 14.0, elevation: 230.0, temperature: 30.0, pressure: 1004.8, humidity: 63.0, is_coastal: false },
    { station_id: 'NOIDA_SEC62', name: 'Noida Observation Stn', distance_km: 24.0, elevation: 205.0, temperature: 30.5, pressure: 1005.3, humidity: 61.0, is_coastal: false },
    { station_id: 'MEERUT_OBS', name: 'Meerut Met Office', distance_km: 68.0, elevation: 220.0, temperature: 29.8, pressure: 1004.9, humidity: 64.0, is_coastal: false },
  ]);

  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const applyPreset = (presetId: string) => {
    const preset = PRESET_SCENARIOS.find(p => p.id === presetId);
    if (!preset) return;
    setSelectedScenarioId(presetId);
    setStationId(preset.data.station_id);
    setStationName(preset.data.name);
    setTemperature(preset.data.temperature);
    setPressure(preset.data.pressure);
    setHumidity(preset.data.humidity);
    setElevation(preset.data.elevation);
    setClimateZone(preset.data.climate_zone);
    setIsCoastal(preset.data.is_coastal);
    setHistory(preset.data.history);
    setNeighbors(preset.data.neighbors);
    setResult(null);
    setError(null);
  };

  const runEvaluation = async () => {
    setEvaluating(true);
    setError(null);
    try {
      const payload = {
        station_data: {
          station_id: stationId,
          name: stationName,
          temperature,
          pressure,
          humidity,
          elevation,
          climate_zone: climateZone,
          is_coastal: isCoastal,
        },
        recent_history: history,
        neighbor_observations: neighbors,
      };

      const response = await fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Inference returned HTTP ${response.status}`);
      }
      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Evaluation failed.');
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col p-4 md:p-6 gap-5 max-w-7xl mx-auto w-full">
      {/* 1. Mandatory Scientific Integrity Banner */}
      <section className="rounded-2xl border-2 border-indigo-200 bg-gradient-to-r from-indigo-50 via-sky-50 to-white p-4 sm:p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-start gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-indigo-600 text-white shadow-md shadow-indigo-200 flex-shrink-0">
              <FlaskConical className="h-5 w-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-black uppercase tracking-[.2em] text-indigo-700 bg-indigo-100/80 px-2 py-0.5 rounded-md">
                  Controlled Demonstration Environment
                </span>
                <span className="text-[10px] font-mono text-slate-500">SIH 26073 Interactive Sandbox</span>
              </div>
              <h1 className="text-xl md:text-2xl font-black tracking-tight text-[#102A43] mt-1">
                Jury Demonstration & Synthetic Fault Sandbox
              </h1>
              <p className="mt-1 text-xs text-[#52667A] max-w-4xl">
                Inject controlled sensor faults, weather fronts, and terrain variations in real time. 
                <strong className="text-indigo-900 font-semibold"> Zero Production Pollution:</strong> All operations are isolated in memory and evaluate against the live concentric spatial consensus engine.
              </p>
            </div>
          </div>
          <button
            onClick={runEvaluation}
            disabled={evaluating}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-blue-500/25 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 transition-all flex-shrink-0"
          >
            {evaluating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4 fill-white" />}
            Execute Detector
          </button>
        </div>
      </section>

      {/* 2. Scenario Presets Selector */}
      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5">
            <Sliders className="h-3.5 w-3.5 text-indigo-600" />
            1-Click Demonstration Scenarios for Evaluators
          </h2>
          <span className="text-[11px] text-slate-500">Select any scenario to prefill telemetry</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
          {PRESET_SCENARIOS.map(preset => {
            const Icon = preset.icon;
            const isSelected = selectedScenarioId === preset.id;
            return (
              <button
                key={preset.id}
                onClick={() => applyPreset(preset.id)}
                className={`text-left p-3 rounded-xl border transition-all ${
                  isSelected
                    ? 'border-indigo-500 bg-white ring-2 ring-indigo-500/20 shadow-md'
                    : 'border-slate-200 bg-white/70 hover:bg-white hover:border-slate-300'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className={`p-1.5 rounded-lg border text-xs ${preset.badgeColor}`}>
                    <Icon className="h-4 w-4" />
                  </span>
                  {isSelected && <span className="text-[9px] font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">Active</span>}
                </div>
                <h3 className="text-xs font-bold text-slate-900 leading-tight">{preset.title}</h3>
                <p className="text-[10px] text-slate-500 mt-1 line-clamp-2">{preset.subtitle}</p>
              </button>
            );
          })}
        </div>
      </section>

      {/* 3. Main Workspace: Controls vs Evidence Output */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        {/* Left Column: Target Station Telemetry & Neighbors (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          
          {/* Target Station Card */}
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-3">
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-sky-600" />
                <span className="text-xs font-black uppercase tracking-wider text-slate-800">Target AWS Telemetry</span>
              </div>
              <span className="text-[10px] font-mono bg-sky-50 text-sky-700 px-2 py-0.5 rounded-md font-semibold">
                ID: {stationId}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {/* Temperature */}
              <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                <div className="flex items-center justify-between text-[11px] font-bold text-slate-600 mb-1">
                  <span className="flex items-center gap-1"><Thermometer className="h-3.5 w-3.5 text-rose-500" /> Air Temp</span>
                  <span className="font-mono text-xs text-slate-900">{temperature.toFixed(1)} °C</span>
                </div>
                <input
                  type="range"
                  min="-20"
                  max="52"
                  step="0.1"
                  value={temperature}
                  onChange={e => setTemperature(parseFloat(e.target.value))}
                  className="w-full accent-rose-600 cursor-pointer"
                />
                <div className="flex justify-between text-[9px] font-mono text-slate-400 mt-1">
                  <span>-20°C</span>
                  <span>Freezing</span>
                  <span>52°C</span>
                </div>
              </div>

              {/* Station Pressure */}
              <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                <div className="flex items-center justify-between text-[11px] font-bold text-slate-600 mb-1">
                  <span className="flex items-center gap-1"><Gauge className="h-3.5 w-3.5 text-indigo-500" /> Pressure</span>
                  <span className="font-mono text-xs text-slate-900">{pressure.toFixed(1)} hPa</span>
                </div>
                <input
                  type="range"
                  min="600"
                  max="1050"
                  step="0.5"
                  value={pressure}
                  onChange={e => setPressure(parseFloat(e.target.value))}
                  className="w-full accent-indigo-600 cursor-pointer"
                />
                <div className="flex justify-between text-[9px] font-mono text-slate-400 mt-1">
                  <span>600 hPa</span>
                  <span>MSLP: 1013</span>
                  <span>1050</span>
                </div>
              </div>

              {/* Relative Humidity */}
              <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
                <div className="flex items-center justify-between text-[11px] font-bold text-slate-600 mb-1">
                  <span className="flex items-center gap-1"><Waves className="h-3.5 w-3.5 text-sky-500" /> Humidity</span>
                  <span className="font-mono text-xs text-slate-900">{humidity.toFixed(0)} %</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="100"
                  step="1"
                  value={humidity}
                  onChange={e => setHumidity(parseInt(e.target.value, 10))}
                  className="w-full accent-sky-600 cursor-pointer"
                />
                <div className="flex justify-between text-[9px] font-mono text-slate-400 mt-1">
                  <span>0%</span>
                  <span>50%</span>
                  <span>100%</span>
                </div>
              </div>
            </div>

            {/* Geographical & Climatological Configuration */}
            <div className="mt-3 pt-3 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
              <div>
                <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                  Climate Envelope
                </label>
                <select
                  value={climateZone}
                  onChange={e => setClimateZone(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white p-1.5 text-xs font-medium text-slate-800"
                >
                  <option value="Indo-Gangetic Plains">Indo-Gangetic Plains</option>
                  <option value="Northern Himalayas">Northern Himalayas</option>
                  <option value="Western Arid & Semi-Arid">Western Arid</option>
                  <option value="Central Plateau">Central Plateau</option>
                  <option value="Deccan Plateau">Deccan Plateau</option>
                  <option value="Coastal Plains">Coastal Plains</option>
                  <option value="Northeast Hills">Northeast Hills</option>
                  <option value="Island Territories">Island Territories</option>
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">
                  Station Elevation
                </label>
                <div className="flex items-center gap-1">
                  <input
                    type="number"
                    value={elevation}
                    onChange={e => setElevation(parseFloat(e.target.value) || 0)}
                    className="w-full rounded-lg border border-slate-200 bg-white p-1.5 text-xs font-mono text-slate-800"
                  />
                  <span className="text-[10px] text-slate-400 font-mono">m</span>
                </div>
              </div>

              <div className="flex items-center sm:justify-center pt-4 sm:pt-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isCoastal}
                    onChange={e => setIsCoastal(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                  />
                  <span className="text-[11px] font-semibold text-slate-700">Coastal Maritime Flag</span>
                </label>
              </div>
            </div>
          </div>

          {/* Concentric Neighbor Configuration Table */}
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-3">
              <div>
                <h3 className="text-xs font-black uppercase tracking-wider text-slate-800">
                  Concentric Spatial Peer Network (Tiers 1, 2, 3)
                </h3>
                <p className="text-[10px] text-slate-500 mt-0.5">
                  Lapse-Rate corrected (-0.0065°C/m) baseline buddies for spatial consensus voting
                </p>
              </div>
              <span className="text-[10px] font-mono text-slate-500 font-medium">
                {neighbors.length} Peers Configured
              </span>
            </div>

            <div className="space-y-2">
              {neighbors.map((n, idx) => {
                const tier = n.distance_km <= 20 ? 'Tier 1 (<20km)' : n.distance_km <= 50 ? 'Tier 2 (20-50km)' : 'Tier 3 (50-100km)';
                const tierColor = n.distance_km <= 20 ? 'text-sky-700 bg-sky-50 border-sky-200' : n.distance_km <= 50 ? 'text-blue-700 bg-blue-50 border-blue-200' : 'text-indigo-700 bg-indigo-50 border-indigo-200';
                const lapseRateCorrection = (-0.0065) * (elevation - n.elevation);
                const adjustedT = n.temperature + lapseRateCorrection;
                const deltaT = Math.abs(temperature - adjustedT);

                return (
                  <div key={n.station_id} className="rounded-xl border border-slate-200 bg-slate-50/50 p-2.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold border ${tierColor}`}>
                        {tier}
                      </span>
                      <div>
                        <div className="font-bold text-slate-800">{n.name}</div>
                        <div className="text-[10px] text-slate-500 font-mono">
                          Dist: {n.distance_km.toFixed(1)} km · Elev: {n.elevation}m
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-end">
                      <div className="text-right">
                        <div className="font-mono text-slate-900 font-bold">{n.temperature.toFixed(1)} °C</div>
                        <div className="text-[9px] font-mono text-slate-500">
                          Adjusted: {adjustedT.toFixed(1)} °C (Δ {deltaT.toFixed(1)}°)
                        </div>
                      </div>
                      <input
                        type="number"
                        step="0.1"
                        value={n.temperature}
                        onChange={e => {
                          const val = parseFloat(e.target.value) || 0;
                          setNeighbors(prev => prev.map((item, i) => i === idx ? { ...item, temperature: val } : item));
                        }}
                        className="w-16 rounded border border-slate-300 bg-white p-1 text-center font-mono text-xs"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Live Detection Evidence & Guidance (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                <h3 className="text-xs font-black uppercase tracking-wider text-slate-800">
                  Real-Time Decision & Evidence Output
                </h3>
              </div>
              {result && (
                <span className="text-[9px] font-mono text-slate-500">
                  Engine: {result.engine || 'live'}
                </span>
              )}
            </div>

            {error && (
              <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                {error}
              </div>
            )}

            {!result && !evaluating && (
              <div className="text-center py-12 px-4 text-slate-400">
                <FlaskConical className="h-10 w-10 mx-auto mb-2 text-slate-300 stroke-[1.5]" />
                <p className="text-xs font-medium text-slate-600">No active evaluation result</p>
                <p className="text-[11px] text-slate-400 mt-1 max-w-xs mx-auto">
                  Click "Execute Detector" or pick a scenario above to test the multi-stage quality control engine.
                </p>
                <button
                  onClick={runEvaluation}
                  className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-sky-50 text-sky-700 font-bold text-xs hover:bg-sky-100 transition-colors"
                >
                  <Play className="h-3.5 w-3.5 fill-sky-700" /> Run Evaluation Now
                </button>
              </div>
            )}

            {evaluating && (
              <div className="text-center py-12 px-4 text-slate-500 space-y-3">
                <RefreshCw className="h-8 w-8 mx-auto animate-spin text-indigo-600" />
                <p className="text-xs font-bold text-slate-800">Evaluating Concentric Spatial Consensus...</p>
                <p className="text-[10px] text-slate-400 font-mono">Running ELR correction · Mesoscale coherence · Calibrated fusion</p>
              </div>
            )}

            {result && !evaluating && (
              <div className="space-y-4">
                
                {/* 1. Primary Decision Banner */}
                <div className={`rounded-xl border p-4 ${
                  result.decision === 'NORMAL'
                    ? 'border-emerald-200 bg-emerald-50/80 text-emerald-950'
                    : result.decision === 'GENUINE_WEATHER_EVENT'
                    ? 'border-sky-200 bg-sky-50/80 text-sky-950'
                    : 'border-rose-200 bg-rose-50/80 text-rose-950'
                }`}>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-black uppercase tracking-wider">
                      Operational Classification
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      result.severity === 'NOMINAL' ? 'bg-emerald-100 text-emerald-800' :
                      result.severity === 'ADVISORY' ? 'bg-sky-100 text-sky-800' :
                      'bg-rose-100 text-rose-800'
                    }`}>
                      {result.severity}
                    </span>
                  </div>
                  
                  <div className="mt-2 flex items-center gap-2">
                    {result.decision === 'NORMAL' && <CheckCircle2 className="h-6 w-6 text-emerald-600" />}
                    {result.decision === 'GENUINE_WEATHER_EVENT' && <CloudLightning className="h-6 w-6 text-sky-600" />}
                    {result.decision === 'SENSOR_FAULT' && <ShieldAlert className="h-6 w-6 text-rose-600" />}
                    <div>
                      <div className="text-base font-black tracking-tight">{result.decision}</div>
                      <div className="text-[11px] opacity-80">{result.root_cause}</div>
                    </div>
                  </div>

                  <p className="text-xs mt-2.5 pt-2.5 border-t border-black/5 leading-relaxed">
                    {result.root_cause_explanation || 'Observation consistency checked across all concentric spatial rings.'}
                  </p>
                </div>

                {/* 2. Scientific Fault Hypothesis & Actionable Guidance */}
                {result.fault_signature_hypothesis && (
                  <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-3 space-y-2">
                    <div className="flex items-start gap-2">
                      <Info className="h-4 w-4 text-indigo-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                          Scientific Fault Signature Hypothesis
                        </div>
                        <div className="text-xs font-bold text-slate-900 mt-0.5">
                          {result.fault_signature_hypothesis}
                        </div>
                      </div>
                    </div>

                    {result.recommended_technician_action && (
                      <div className="flex items-start gap-2 pt-2 border-t border-slate-200/80">
                        <Wrench className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                        <div>
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                            Recommended Technician Action (Field Guidance)
                          </div>
                          <div className="text-xs text-slate-700 mt-0.5 leading-snug">
                            {result.recommended_technician_action}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* 3. Numerical Evidence Grid */}
                <div className="grid grid-cols-2 gap-2 text-center">
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-2.5">
                    <span className="block text-[10px] font-bold text-slate-500 uppercase">Anomaly Score</span>
                    <span className="font-mono text-base font-black text-slate-900">
                      {result.anomaly_score.toFixed(3)}
                    </span>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-2.5">
                    <span className="block text-[10px] font-bold text-slate-500 uppercase">Fault Probability</span>
                    <span className="font-mono text-base font-black text-slate-900">
                      {(result.fault_probability * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>

                {/* 4. Concentric Ring Breakdown */}
                {result.evidence && (
                  <div className="rounded-xl border border-slate-200 bg-white p-3 space-y-2">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                      Concentric Ring Spatial Agreement
                    </div>
                    <div className="space-y-1.5 text-xs font-mono">
                      <div className="flex justify-between items-center bg-slate-50 px-2 py-1 rounded">
                        <span>Tier 1 (&lt; 20 km)</span>
                        <span className="font-bold text-slate-700">Tol: 2.0 °C</span>
                      </div>
                      <div className="flex justify-between items-center bg-slate-50 px-2 py-1 rounded">
                        <span>Tier 2 (20 – 50 km)</span>
                        <span className="font-bold text-slate-700">Tol: 3.5 °C</span>
                      </div>
                      <div className="flex justify-between items-center bg-slate-50 px-2 py-1 rounded">
                        <span>Tier 3 (50 – 100 km)</span>
                        <span className="font-bold text-slate-700">Tol: 5.0 °C (Coherence)</span>
                      </div>
                    </div>
                  </div>
                )}

              </div>
            )}
          </div>

        </div>

      </div>
    </div>
  );
}
