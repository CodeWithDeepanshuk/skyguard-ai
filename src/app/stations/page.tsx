'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Radio, Search, Filter, MapPin, ChevronRight, ExternalLink } from 'lucide-react';

interface Station {
  station_id: string;
  station_name: string;
  climate_zone: string;
  cluster: string;
  evaluation_role: string;
  latitude: number;
  longitude: number;
  elevation_m: number;
  icao?: string;
  is_benchmark: boolean;
  is_active_2024_plus: boolean;
  status?: string;
}

export default function StationsPage() {
  const [stations, setStations] = useState<Station[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [networkFilter, setNetworkFilter] = useState<'all' | 'active' | 'benchmark'>('all');
  const [zoneFilter, setZoneFilter] = useState('all');

  useEffect(() => {
    setLoading(true);
    fetch(`/api/stations?network=${networkFilter}&climate_zone=${zoneFilter}`)
      .then(res => res.json())
      .then(data => {
        setStations(data);
        setLoading(false);
      })
      .catch(() => {
        setStations([]);
        setLoading(false);
      });
  }, [networkFilter, zoneFilter]);

  const filteredStations = stations.filter(s => {
    const q = search.toLowerCase();
    return s.station_name.toLowerCase().includes(q) || s.station_id.includes(q);
  });

  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1a4163] pb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-white flex items-center gap-2.5">
            <Radio className="w-6 h-6 text-cyan-400" />
            Indian Weather Station Catalog
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Catalog locations are not proof of live reporting or sensor health. Open a station to check its source observations.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-xs px-3 py-1.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono font-bold">
            {filteredStations.length} Stations Found
          </span>
        </div>
      </div>

      {/* Filter Controls Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 bg-[#0c2234] border border-[#1a4163] p-4 rounded-xl">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            placeholder="Search by station name or ID..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-[#071521] border border-[#1a4163] rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>

        <div>
          <select
            value={networkFilter}
            onChange={e => setNetworkFilter(e.target.value as any)}
            className="w-full bg-[#071521] border border-[#1a4163] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
          >
            <option value="all">All Catalog Stations</option>
            <option value="active">Active 2024+ Fleet (410)</option>
            <option value="benchmark">Benchmark Core Stations (24)</option>
          </select>
        </div>

        <div>
          <select
            value={zoneFilter}
            onChange={e => setZoneFilter(e.target.value)}
            className="w-full bg-[#071521] border border-[#1a4163] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
          >
            <option value="all">All Climate Zones (8)</option>
            <option value="Central Plateau">Central Plateau</option>
            <option value="Coastal Plains">Coastal Plains</option>
            <option value="Indo-Gangetic Plains">Indo-Gangetic Plains</option>
            <option value="Deccan Plateau">Deccan Plateau</option>
            <option value="Northeast Hills">Northeast Hills</option>
            <option value="Western Arid/Semi-Arid">Western Arid</option>
            <option value="Northern Himalayas">Northern Himalayas</option>
            <option value="Island Territories">Island Territories</option>
          </select>
        </div>
      </div>

      {/* Stations Table */}
      <div className="rounded-xl border border-[#1a4163] bg-[#0c2234] overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-12 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
            <div className="w-6 h-6 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></div>
            <span>Loading network stations...</span>
          </div>
        ) : filteredStations.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            <p>No weather stations match the selected filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-[#071521] text-xs uppercase text-slate-400 font-semibold border-b border-[#1a4163]">
                <tr>
                  <th className="px-4 py-3">Station</th>
                  <th className="px-4 py-3">Station ID</th>
                  <th className="px-4 py-3">Climate Zone</th>
                  <th className="px-4 py-3">Coordinates</th>
                  <th className="px-4 py-3">Elevation</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Telemetry</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1a4163]/50">
                {filteredStations.map(s => (
                  <tr key={s.station_id} className="hover:bg-[#143652]/40 transition-colors">
                    <td className="px-4 py-3.5 font-bold text-white flex items-center gap-2">
                      <MapPin className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                      <span>{s.station_name}</span>
                      {s.is_benchmark && (
                        <span className="text-[10px] uppercase font-extrabold px-1.5 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800">
                          Benchmark
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-400">{s.station_id}</td>
                    <td className="px-4 py-3.5 text-xs text-slate-300">{s.climate_zone}</td>
                    <td className="px-4 py-3.5 text-xs font-mono text-slate-400">
                      {s.latitude.toFixed(2)}°N, {s.longitude.toFixed(2)}°E
                    </td>
                    <td className="px-4 py-3.5 text-xs font-mono text-slate-400">{s.elevation_m} m</td>
                    <td className="px-4 py-3.5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
                        Unverified
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <Link
                        href={`/stations/${s.station_id}`}
                        className="inline-flex items-center space-x-1 text-xs text-cyan-400 hover:text-cyan-300 font-semibold transition-colors"
                      >
                        <span>View Station</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
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
