'use client';

import React, { useCallback, useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { AlertTriangle, CloudSun, Database, RefreshCw } from 'lucide-react';
import { MapSkeleton } from '@/components/common/Skeleton';
import { LiveIntelligencePanel } from '@/components/station/LiveIntelligencePanel';
import { StationDrawer } from '@/components/station/StationDrawer';
import { useOperational } from '@/context/OperationalContext';
import { mapOperationalIncident, mapOperationalStation } from '@/lib/operational';
import { IncidentRecord, StationObservation } from '@/lib/types';

const LiveMap = dynamic(() => import('@/components/map/LiveMap'), {
  ssr: false,
  loading: () => <MapSkeleton />,
});

export default function NationalCommandCentrePage() {
  const { timeMode, activeView, selectedStation, setSelectedStation, isDrawerOpen, setIsDrawerOpen } = useOperational();
  const [stations, setStations] = useState<StationObservation[]>([]);
  const [incidents, setIncidents] = useState<IncidentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dataMode, setDataMode] = useState<string>('checking');

  const loadData = useCallback(async () => {
    setError(null);
    try {
      const [stationResponse, incidentResponse] = await Promise.all([
        fetch('/api/stations', { cache: 'no-store' }),
        fetch('/api/incidents?limit=100', { cache: 'no-store' }),
      ]);
      if (!stationResponse.ok) throw new Error('Station observation service is unavailable.');
      const stationPayload = await stationResponse.json();
      if (!Array.isArray(stationPayload)) throw new Error('Station response contract is invalid.');
      setStations(stationPayload.map(mapOperationalStation));
      setDataMode(stationResponse.headers.get('x-skyguard-data-mode') || 'unknown');
      if (incidentResponse.ok) {
        const incidentPayload = await incidentResponse.json();
        setIncidents(Array.isArray(incidentPayload) ? incidentPayload.map(mapOperationalIncident) : []);
      } else {
        setIncidents([]);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Operational data is unavailable.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = window.setInterval(() => {
      if (!document.hidden) loadData();
    }, 60_000);
    return () => window.clearInterval(interval);
  }, [loadData]);

  const reporting = stations.filter(station => !station.catalog_only).length;
  return (
    <div className="flex-1 flex flex-col min-h-0 p-3 md:p-4 gap-3">
      <section className="relative overflow-hidden rounded-2xl border border-white/80 bg-white/72 backdrop-blur-xl px-4 py-3 shadow-[0_18px_50px_rgba(23,105,170,0.08)]">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-start gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-sky-500 to-blue-700 text-white shadow-lg shadow-sky-200"><CloudSun className="h-5 w-5" /></span>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[.2em] text-sky-700">Executive command centre</p>
              <h1 className="text-lg md:text-xl font-black tracking-tight text-[#102A43]">India station observation intelligence</h1>
              <p className="mt-1 text-xs text-[#52667A]">Catalog coverage and actual reporting coverage are separate. Every visible value comes from the stored WIS2, METAR or credentialed IMD observation path.</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-[11px] font-mono">
            <span className={dataMode === 'operational-observation-store' ? 'rounded-full border px-2.5 py-1 border-emerald-200 bg-emerald-50 text-emerald-800' : 'rounded-full border px-2.5 py-1 border-amber-200 bg-amber-50 text-amber-800'}>
              <Database className="mr-1 inline h-3 w-3" />{dataMode === 'operational-observation-store' ? reporting + ' stations observed' : 'Metadata-only fallback'}
            </span>
            <button onClick={loadData} className="min-h-11 min-w-11 grid place-items-center rounded-xl border border-sky-200 bg-sky-50 text-sky-800 hover:bg-sky-100" aria-label="Refresh operational observations"><RefreshCw className={loading ? 'h-4 w-4 animate-spin' : 'h-4 w-4'} /></button>
          </div>
        </div>
        {error && <div className="mt-3 flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900"><AlertTriangle className="h-4 w-4" />{error} Catalog metadata may remain visible without fabricated readings.</div>}
      </section>

      <div className="flex-1 flex flex-col lg:flex-row min-h-[620px] overflow-hidden rounded-2xl border border-[#D8E6EF] bg-white/85 shadow-[0_22px_65px_rgba(16,42,67,0.1)]">
        <div className="flex-1 min-h-[520px] relative">
          <LiveMap stations={stations} selectedStation={selectedStation} onSelectStation={station => { setSelectedStation(station); setIsDrawerOpen(true); }} activeView={activeView} timeMode={timeMode} />
        </div>
        <div className="w-full lg:w-[390px] xl:w-[430px] min-h-[420px] lg:min-h-0 flex-shrink-0">
          <LiveIntelligencePanel stations={stations} incidents={incidents} onSelectStation={station => { setSelectedStation(station); setIsDrawerOpen(true); }} />
        </div>
      </div>

      <StationDrawer station={selectedStation} isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)} timeMode={timeMode} allStations={stations} />
    </div>
  );
}
