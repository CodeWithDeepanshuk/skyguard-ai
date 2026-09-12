'use client';

import React, { useState, useEffect } from 'react';
import { 
  AlertOctagon, 
  Search, 
  Download, 
  Filter, 
  CheckCircle2, 
  AlertTriangle,
  Info,
  ChevronDown
} from 'lucide-react';

interface Incident {
  incident_id: string;
  station_id: string;
  timestamp_utc: string;
  decision: string;
  severity: string;
  fault_probability: number;
  root_cause: string;
  root_cause_confidence: number;
  affected_sensors: string[];
  corrections?: Array<{
    sensor: string;
    reported_value: number;
    estimate: number;
    interval_lower: number;
    interval_upper: number;
  }>;
  explanation: string;
  recommended_action: string;
}

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [faultFilter, setFaultFilter] = useState('all');

  useEffect(() => {
    fetch('/api/incidents?limit=100')
      .then(async res => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Live incident service unavailable');
        return data;
      })
      .then(data => {
        setIncidents(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Live incident service unavailable');
        setIncidents([]);
        setLoading(false);
      });
  }, []);

  const filtered = incidents.filter(inc => {
    const q = search.toLowerCase();
    const matchesSearch = inc.station_id.includes(q) || 
      (inc.root_cause && inc.root_cause.toLowerCase().includes(q)) ||
      (inc.incident_id && inc.incident_id.toLowerCase().includes(q));
    
    const matchesSeverity = severityFilter === 'all' || 
      inc.severity.toLowerCase() === severityFilter.toLowerCase();

    const matchesFault = faultFilter === 'all' || 
      (inc.root_cause && inc.root_cause.toLowerCase().includes(faultFilter.toLowerCase()));

    return matchesSearch && matchesSeverity && matchesFault;
  });

  const exportCSV = () => {
    if (filtered.length === 0) return;
    const headers = ['incident_id', 'station_id', 'timestamp_utc', 'severity', 'root_cause', 'fault_probability', 'affected_sensors', 'explanation'];
    const rows = filtered.map(i => [
      i.incident_id,
      i.station_id,
      i.timestamp_utc,
      i.severity,
      i.root_cause,
      i.fault_probability,
      (i.affected_sensors || []).join(';'),
      `"${(i.explanation || '').replace(/"/g, '""')}"`
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `skyguard_incidents_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {error && <p role="alert" className="rounded-xl border border-amber-800 p-4 text-amber-300">{error}. No historical incidents are substituted.</p>}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1a4163] pb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-white flex items-center gap-2.5">
            <AlertOctagon className="w-6 h-6 text-rose-400" />
            Incident Command Centre
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Stateful multi-observation incident aggregation. Enforces k-of-n persistence so single-packet noise never triggers false alarms.
          </p>
        </div>

        <button
          type="button"
          onClick={exportCSV}
          className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-[#143652] hover:bg-cyan-900 text-white text-xs font-bold border border-[#1a4163] transition-colors"
        >
          <Download className="w-4 h-4" />
          <span>Export Incidents CSV</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-[#0c2234] border border-[#1a4163] p-4 rounded-xl">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Filter by station ID, fault, or incident ID..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-[#071521] border border-[#1a4163] rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div>
          <select
            value={severityFilter}
            onChange={e => setSeverityFilter(e.target.value)}
            className="w-full bg-[#071521] border border-[#1a4163] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
          >
            <option value="all">All Severities</option>
            <option value="high">Critical / High Severity</option>
            <option value="medium">Moderate / Medium Severity</option>
            <option value="low">Low Severity</option>
          </select>
        </div>

        <div>
          <select
            value={faultFilter}
            onChange={e => setFaultFilter(e.target.value)}
            className="w-full bg-[#071521] border border-[#1a4163] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
          >
            <option value="all">All Fault Categories</option>
            <option value="spike">Spike Anomaly</option>
            <option value="drift">Sensor Drift</option>
            <option value="freeze">Frozen Sensor</option>
            <option value="communication">Transport / Telemetry Gap</option>
            <option value="noise">Gaussian Noise</option>
          </select>
        </div>
      </div>

      {/* Incidents Table */}
      <div className="rounded-xl border border-[#1a4163] bg-[#0c2234] overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-16 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
            <div className="w-6 h-6 border-2 border-rose-400 border-t-transparent rounded-full animate-spin"></div>
            <span>Loading incident stream...</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
            <p className="font-semibold text-white">No active incidents match current criteria.</p>
            <p className="text-xs text-slate-400 mt-1">All monitored Automatic Weather Stations reporting normal behavior.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-[#071521] text-xs uppercase text-slate-400 font-semibold border-b border-[#1a4163]">
                <tr>
                  <th className="px-4 py-3">Incident ID</th>
                  <th className="px-4 py-3">Station</th>
                  <th className="px-4 py-3">Root Cause</th>
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Confidence</th>
                  <th className="px-4 py-3">Timestamp (UTC)</th>
                  <th className="px-4 py-3">Explanation & Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1a4163]/50">
                {filtered.slice(0, 100).map(inc => (
                  <tr key={inc.incident_id} className="hover:bg-[#143652]/30 transition-colors">
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-400">{inc.incident_id}</td>
                    <td className="px-4 py-3.5 font-bold text-white font-mono">{inc.station_id}</td>
                    <td className="px-4 py-3.5">
                      <span className="px-2.5 py-1 rounded bg-[#143652] text-xs font-semibold text-cyan-300 border border-slate-700">
                        {inc.root_cause || 'SENSOR_FAULT'}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`px-2 py-0.5 rounded text-xs font-extrabold uppercase ${
                        inc.severity === 'high' || inc.severity === 'critical'
                          ? 'bg-rose-950 text-rose-400 border border-rose-800'
                          : 'bg-amber-950 text-amber-400 border border-amber-800'
                      }`}>
                        {inc.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs text-white">
                      {+((inc.fault_probability || 0.95) * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-400 whitespace-nowrap">
                      {new Date(inc.timestamp_utc).toLocaleString()}
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-300 max-w-md">
                      <p className="line-clamp-2">{inc.explanation}</p>
                      {inc.recommended_action && (
                        <span className="text-[11px] text-cyan-400 block mt-0.5 font-medium">
                          Action: {inc.recommended_action}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
