'use client';

import React, { useState, useEffect, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { useOperational } from '@/context/OperationalContext';
import { StationObservation } from '@/lib/types';
import { QualityBadge, SourceBadge } from '@/components/common/Badge';
import { StationDrawer } from '@/components/station/StationDrawer';
import { MapSkeleton, TableRowSkeleton } from '@/components/common/Skeleton';
import { formatAge, formatTemp, formatPressure, formatHumidity } from '@/lib/formatters';
import { mapOperationalStation } from '@/lib/operational';
import { 
  ArrowUpDown, 
  ChevronLeft, 
  ChevronRight, 
  Columns, 
  Filter, 
  Map, 
  RadioTower, 
  Search, 
  SlidersHorizontal, 
  Table 
} from 'lucide-react';

const LiveMap = dynamic(() => import('@/components/map/LiveMap'), {
  ssr: false,
  loading: () => <MapSkeleton />,
});

export default function StationsNetworkPage() {
  const { timeMode, activeView, selectedStation, setSelectedStation, isDrawerOpen, setIsDrawerOpen } = useOperational();

  const [stations, setStations] = useState<StationObservation[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'SPLIT' | 'TABLE' | 'MAP'>('SPLIT');

  // Filters
  const [search, setSearch] = useState('');
  const [zoneFilter, setZoneFilter] = useState('ALL');
  const [healthFilter, setHealthFilter] = useState('ALL');
  const [sortField, setSortField] = useState<'station_name' | 'temperature' | 'pressure' | 'relative_humidity' | 'quality_state'>('station_name');
  const [sortAsc, setSortAsc] = useState(true);

  // Pagination
  const [page, setPage] = useState(1);
  const pageSize = 20;

  useEffect(() => {
    async function loadStations() {
      setLoading(true);
      try {
        const res = await fetch('/api/stations');
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) {
            const mapped: StationObservation[] = data.map(mapOperationalStation);
            setStations(mapped);
          }
        }
      } catch (err) {
        console.error('Failed to load stations catalog', err);
      } finally {
        setLoading(false);
      }
    }

    loadStations();
  }, []);

  // Filter and sort stations
  const filteredStations = useMemo(() => {
    let result = stations;

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (s) =>
          s.station_name.toLowerCase().includes(q) ||
          s.station_id.toLowerCase().includes(q) ||
          (s.state && s.state.toLowerCase().includes(q))
      );
    }

    if (zoneFilter !== 'ALL') {
      result = result.filter((s) => s.state?.toLowerCase() === zoneFilter.toLowerCase());
    }

    if (healthFilter !== 'ALL') {
      result = result.filter((s) => s.quality_state === healthFilter);
    }

    result = [...result].sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      if (aVal < bVal) return sortAsc ? -1 : 1;
      if (aVal > bVal) return sortAsc ? 1 : -1;
      return 0;
    });

    return result;
  }, [stations, search, zoneFilter, healthFilter, sortField, sortAsc]);

  // Paginated rows
  const paginatedStations = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredStations.slice(start, start + pageSize);
  }, [filteredStations, page, pageSize]);

  const totalPages = Math.ceil(filteredStations.length / pageSize) || 1;

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden p-4 space-y-4 select-none">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
        <div>
          <div className="flex items-center gap-2 text-slate-900 font-extrabold text-base tracking-tight">
            <RadioTower className="w-5 h-5 text-blue-600" />
            <h1>Indian Automatic Weather Station Network</h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 font-semibold">
              {loading ? 'Loading catalog' : `${stations.length.toLocaleString('en-IN')} catalog stations`}
            </span>
          </div>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            Catalog metadata, received observations, pressure semantics, freshness and evidence-backed QC state.
          </p>
        </div>

        {/* View Switcher: Map | Table | Split */}
        <div className="flex items-center bg-slate-100 border border-slate-200 rounded-lg p-1 text-xs font-mono">
          <button
            onClick={() => setViewMode('SPLIT')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded transition-all ${
              viewMode === 'SPLIT' ? 'bg-white text-blue-700 font-bold shadow-xs' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <Columns className="w-3.5 h-3.5" />
            <span>Split</span>
          </button>
          <button
            onClick={() => setViewMode('TABLE')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded transition-all ${
              viewMode === 'TABLE' ? 'bg-white text-blue-700 font-bold shadow-xs' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <Table className="w-3.5 h-3.5" />
            <span>Table</span>
          </button>
          <button
            onClick={() => setViewMode('MAP')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded transition-all ${
              viewMode === 'MAP' ? 'bg-white text-blue-700 font-bold shadow-xs' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <Map className="w-3.5 h-3.5" />
            <span>Map</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 bg-white border border-slate-200 rounded-xl p-3 shadow-xs text-xs">
        {/* Search */}
        <div className="relative sm:col-span-2">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search stations by name, ID, or state..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* Climate Zone Filter */}
        <div>
          <select
            value={zoneFilter}
            onChange={(e) => {
              setZoneFilter(e.target.value);
              setPage(1);
            }}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-blue-500"
          >
            <option value="ALL">All Climate Zones (8)</option>
            <option value="Central Plateau">Central Plateau</option>
            <option value="Indo-Gangetic Plain">Indo-Gangetic Plain</option>
            <option value="Western Coast">Western Coast</option>
            <option value="Eastern Coast">Eastern Coast</option>
            <option value="Himalayan">Himalayan</option>
            <option value="Arid / Desert">Arid / Desert</option>
          </select>
        </div>

        {/* Health State Filter */}
        <div>
          <select
            value={healthFilter}
            onChange={(e) => {
              setHealthFilter(e.target.value);
              setPage(1);
            }}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-900 focus:outline-none focus:border-blue-500"
          >
            <option value="ALL">All Health States</option>
            <option value="NO_ANOMALY_DETECTED">No anomaly detected</option>
            <option value="WARMING_UP">Warming up</option>
            <option value="WATCH">Watch</option>
            <option value="PROBABLE_FAULT">Probable Fault</option>
            <option value="CRITICAL">Critical Anomaly</option>
            <option value="MULTI_SENSOR_ANOMALY">Multi-Sensor Anomaly</option>
            <option value="GENUINE_WEATHER_EVENT">Genuine weather event</option>
            <option value="DELAYED">Delayed</option>
            <option value="STALE">Stale</option>
            <option value="NO_RECENT_REPORT">No recent report</option>
            <option value="NOT_OBSERVED_IN_STORE">Catalog only</option>
          </select>
        </div>
      </div>

      {/* Main Content Area based on viewMode */}
      <div className="flex-1 flex flex-col lg:flex-row gap-4 overflow-hidden min-h-[400px]">
        {/* Map View */}
        {(viewMode === 'MAP' || viewMode === 'SPLIT') && (
          <div className={`${viewMode === 'SPLIT' ? 'w-full lg:w-1/2' : 'w-full'} h-full rounded-xl overflow-hidden border border-slate-200 shadow-xs`}>
            <LiveMap
              stations={filteredStations}
              selectedStation={selectedStation}
              onSelectStation={(stn) => {
                setSelectedStation(stn);
                setIsDrawerOpen(true);
              }}
              activeView={activeView}
              timeMode={timeMode}
            />
          </div>
        )}

        {/* Table View */}
        {(viewMode === 'TABLE' || viewMode === 'SPLIT') && (
          <div className={`${viewMode === 'SPLIT' ? 'w-full lg:w-1/2' : 'w-full'} h-full flex flex-col bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs`}>
            {/* Table Container */}
            <div className="flex-1 overflow-x-auto overflow-y-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="sticky top-0 bg-slate-50 border-b border-slate-200 text-[11px] font-mono text-slate-600 z-10">
                  <tr>
                    <th className="py-2.5 px-3 cursor-pointer" onClick={() => handleSort('station_name')}>
                      <div className="flex items-center gap-1">
                        <span>Station</span>
                        <ArrowUpDown className="w-3 h-3 text-slate-400" />
                      </div>
                    </th>
                    <th className="py-2.5 px-3">State</th>
                    <th className="py-2.5 px-3 cursor-pointer" onClick={() => handleSort('temperature')}>
                      <div className="flex items-center gap-1">
                        <span>Temp</span>
                        <ArrowUpDown className="w-3 h-3 text-slate-400" />
                      </div>
                    </th>
                    <th className="py-2.5 px-3 cursor-pointer" onClick={() => handleSort('pressure')}>
                      <div className="flex items-center gap-1">
                        <span>Pressure</span>
                        <ArrowUpDown className="w-3 h-3 text-slate-400" />
                      </div>
                    </th>
                    <th className="py-2.5 px-3 cursor-pointer" onClick={() => handleSort('relative_humidity')}>
                      <div className="flex items-center gap-1">
                        <span>RH</span>
                        <ArrowUpDown className="w-3 h-3 text-slate-400" />
                      </div>
                    </th>
                    <th className="py-2.5 px-3 cursor-pointer" onClick={() => handleSort('quality_state')}>
                      <div className="flex items-center gap-1">
                        <span>Health State</span>
                        <ArrowUpDown className="w-3 h-3 text-slate-400" />
                      </div>
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                  {loading ? (
                    Array.from({ length: 10 }).map((_, i) => <TableRowSkeleton key={i} cols={6} />)
                  ) : paginatedStations.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-12 text-center text-slate-400 italic">
                        No weather stations match current filter criteria.
                      </td>
                    </tr>
                  ) : (
                    paginatedStations.map((station) => (
                      <tr
                        key={station.station_id}
                        onClick={() => {
                          setSelectedStation(station);
                          setIsDrawerOpen(true);
                        }}
                        className={`hover:bg-blue-50/50 cursor-pointer transition-colors ${
                          selectedStation?.station_id === station.station_id ? 'bg-blue-50 border-l-2 border-l-blue-600' : ''
                        }`}
                      >
                        <td className="py-2.5 px-3 font-sans">
                          <div className="font-bold text-slate-900 truncate max-w-[140px] sm:max-w-[180px]">
                            {station.station_name}
                          </div>
                          <div className="text-[10px] font-mono text-slate-500 truncate">
                            {station.station_id}
                          </div>
                        </td>
                        <td className="py-2.5 px-3 text-slate-600">{station.state || '—'}</td>
                        <td className="py-2.5 px-3 text-amber-700 font-semibold">{formatTemp(station.temperature)}</td>
                        <td className="py-2.5 px-3 text-blue-700 font-semibold">{formatPressure(station.pressure)}</td>
                        <td className="py-2.5 px-3 text-indigo-700 font-semibold">{formatHumidity(station.relative_humidity)}</td>
                        <td className="py-2.5 px-3">
                          <QualityBadge state={station.quality_state} size="sm" showIcon={false} />
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div className="p-3 bg-white border-t border-slate-200 flex items-center justify-between text-xs font-mono text-slate-500">
              <div>
                Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, filteredStations.length)} of {filteredStations.length}
              </div>

              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 disabled:opacity-40 transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="px-2 font-bold text-slate-900">
                  {page} / {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="p-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 disabled:opacity-40 transition-colors"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Station Intelligence Drawer */}
      <StationDrawer
        station={selectedStation}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        timeMode={timeMode}
        allStations={stations}
      />
    </div>
  );
}
