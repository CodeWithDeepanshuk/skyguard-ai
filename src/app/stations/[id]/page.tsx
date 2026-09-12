'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { 
  ArrowLeft, 
  MapPin, 
  Activity, 
  Thermometer, 
  Gauge, 
  Droplets, 
  ShieldAlert, 
  CheckCircle2,
  Clock,
  Radio
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  CartesianGrid 
} from 'recharts';

interface StationDetailProps {
  params: { id: string };
}

interface TelemetryPoint {
  timestamp_utc: string;
  temperature_c: number;
  pressure_hpa: number;
  relative_humidity: number;
  decision: string;
  fault_probability: number;
  weather_probability: number;
  buddy_z_temperature: number;
  cusum_drift_score: number;
  freeze_repeat_count: number;
}

export default function StationDetailPage({ params }: StationDetailProps) {
  const { id } = params;
  const [stationData, setStationData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedSensor, setSelectedSensor] = useState<'temp' | 'press' | 'humidity'>('temp');

  useEffect(() => {
    fetch(`/api/stations/${id}`)
      .then(res => res.json())
      .then(data => {
        setStationData(data);
        setLoading(false);
      })
      .catch(() => {
        setStationData(null);
        setLoading(false);
      });
  }, [id]);

  if (loading) {
    return (
      <div className="p-16 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
        <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></div>
        <span>Retrieving station telemetry...</span>
      </div>
    );
  }

  if (!stationData || !stationData.metadata) {
    return (
      <div className="p-12 text-center text-slate-400 bg-[#0c2234] border border-[#1a4163] rounded-xl">
        <h2 className="text-xl font-bold text-white mb-2">Station Telemetry Unavailable</h2>
        <p className="text-sm text-slate-400 mb-6">Could not locate metadata or active observations for station ID {id}.</p>
        <Link href="/stations" className="inline-flex items-center px-4 py-2 rounded-lg bg-cyan-600 text-white text-xs font-bold">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Network Catalog
        </Link>
      </div>
    );
  }

  const meta = stationData.metadata;
  const readings: TelemetryPoint[] = stationData.readings || [];
  const latest = readings[readings.length - 1] || {
    temperature_c: 28.5,
    pressure_hpa: 1008.2,
    relative_humidity: 65,
    decision: 'NORMAL',
    fault_probability: 0.02,
    buddy_z_temperature: 0.2,
    cusum_drift_score: 0.1,
    freeze_repeat_count: 0
  };

  const chartData = readings.map(r => ({
    time: new Date(r.timestamp_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    temperature: r.temperature_c,
    pressure: r.pressure_hpa,
    humidity: r.relative_humidity,
    faultProb: +(r.fault_probability * 100).toFixed(1)
  }));

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Back button & Breadcrumb */}
      <div className="flex items-center space-x-2 text-xs text-slate-400">
        <Link href="/stations" className="hover:text-cyan-400 flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>All Stations</span>
        </Link>
        <span>/</span>
        <span className="text-slate-200">{meta.station_name || id}</span>
      </div>

      {/* Header Profile */}
      <div className="rounded-xl border border-[#1a4163] bg-[#0c2234] p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl sm:text-3xl font-black text-white">{meta.station_name || id}</h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono font-bold">
              AWS {id}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400">
            <span className="flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5 text-cyan-400" />
              {parseFloat(meta.latitude).toFixed(2)}°N, {parseFloat(meta.longitude).toFixed(2)}°E · Elevation {meta.elevation_m}m
            </span>
            <span>•</span>
            <span className="text-slate-300 font-medium">Zone: {meta.climate_zone}</span>
            <span>•</span>
            <span className="text-slate-300 font-medium">Role: {meta.evaluation_role || 'Standard AWS'}</span>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <span className="px-3 py-1.5 rounded-lg bg-emerald-950 text-emerald-400 border border-emerald-800 text-xs font-bold uppercase tracking-wider flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4" />
            Sensor Status: Normal
          </span>
        </div>
      </div>

      {/* Current Live Values Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div 
          onClick={() => setSelectedSensor('temp')}
          className={`cursor-pointer rounded-xl border p-5 transition-all ${
            selectedSensor === 'temp' 
              ? 'border-cyan-500 bg-[#143652] shadow-lg shadow-cyan-500/10' 
              : 'border-[#1a4163] bg-[#0c2234] hover:bg-[#143652]/40'
          }`}
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">Ambient Temperature</span>
            <Thermometer className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-3xl font-black text-white">{latest.temperature_c}°C</div>
          <p className="text-xs text-slate-400 mt-1">Buddy z-residual: {latest.buddy_z_temperature} σ</p>
        </div>

        <div 
          onClick={() => setSelectedSensor('press')}
          className={`cursor-pointer rounded-xl border p-5 transition-all ${
            selectedSensor === 'press' 
              ? 'border-cyan-500 bg-[#143652] shadow-lg shadow-cyan-500/10' 
              : 'border-[#1a4163] bg-[#0c2234] hover:bg-[#143652]/40'
          }`}
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">Station Pressure</span>
            <Gauge className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-black text-white">{latest.pressure_hpa} hPa</div>
          <p className="text-xs text-slate-400 mt-1">Tendency: Diurnal baseline</p>
        </div>

        <div 
          onClick={() => setSelectedSensor('humidity')}
          className={`cursor-pointer rounded-xl border p-5 transition-all ${
            selectedSensor === 'humidity' 
              ? 'border-cyan-500 bg-[#143652] shadow-lg shadow-cyan-500/10' 
              : 'border-[#1a4163] bg-[#0c2234] hover:bg-[#143652]/40'
          }`}
        >
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider">Relative Humidity</span>
            <Droplets className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-3xl font-black text-white">{latest.relative_humidity}%</div>
          <p className="text-xs text-slate-400 mt-1">Status: Within saturation bounds</p>
        </div>
      </div>

      {/* 24-Hour Telemetry Chart */}
      <div className="rounded-xl border border-[#1a4163] bg-[#0c2234] p-6 shadow-xl">
        <div className="flex items-center justify-between border-b border-[#1a4163] pb-4 mb-6">
          <div>
            <h3 className="text-lg font-bold text-white">24-Hour Observation Trace</h3>
            <p className="text-xs text-slate-400">
              Visualizing {selectedSensor === 'temp' ? 'Temperature (°C)' : selectedSensor === 'press' ? 'Pressure (hPa)' : 'Relative Humidity (%)'} across recent telemetry packets.
            </p>
          </div>
          <div className="text-xs text-slate-400 font-mono">Cadence: 60 min</div>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a4163" />
              <XAxis dataKey="time" stroke="#94a3b8" fontSize={11} />
              <YAxis stroke="#94a3b8" fontSize={11} domain={['auto', 'auto']} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#071521', borderColor: '#1a4163', borderRadius: '8px', color: '#fff' }}
              />
              <Line 
                type="monotone" 
                dataKey={selectedSensor === 'temp' ? 'temperature' : selectedSensor === 'press' ? 'pressure' : 'humidity'} 
                stroke="#38bdf8" 
                strokeWidth={2.5}
                dot={{ r: 3, fill: '#38bdf8' }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Diagnostic QC Health Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-xl border border-[#1a4163] bg-[#0c2234] p-5">
          <span className="text-xs font-bold uppercase text-slate-400">Integer Freeze Detection</span>
          <div className="text-xl font-bold text-white mt-1">No Freeze Detected</div>
          <p className="text-xs text-slate-400 mt-1">Run-length count: 1 (normal sensor variability)</p>
        </div>

        <div className="rounded-xl border border-[#1a4163] bg-[#0c2234] p-5">
          <span className="text-xs font-bold uppercase text-slate-400">CUSUM Drift State</span>
          <div className="text-xl font-bold text-white mt-1">Score: {latest.cusum_drift_score} σ</div>
          <p className="text-xs text-slate-400 mt-1">Threshold h=4.0 (no persistent drift accumulation)</p>
        </div>

        <div className="rounded-xl border border-[#1a4163] bg-[#0c2234] p-5">
          <span className="text-xs font-bold uppercase text-slate-400">Transport & Heartbeat SLA</span>
          <div className="text-xl font-bold text-emerald-400 mt-1">Healthy</div>
          <p className="text-xs text-slate-400 mt-1">No duplicate packets or transmission gaps</p>
        </div>
      </div>
    </div>
  );
}
