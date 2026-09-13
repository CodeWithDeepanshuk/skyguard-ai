'use client';

import React, { useEffect, useState } from 'react';
import { useOperational } from '@/context/OperationalContext';
import { mapOperationalStation } from '@/lib/operational';
import { OperationalNetworkKPIs, StationObservation } from '@/lib/types';
import { AtmosphereBackground } from './AtmosphereBackground';
import { CommandPalette } from './CommandPalette';
import { Sidebar } from './Sidebar';
import { StatusBar } from './StatusBar';
import { TopBar } from './TopBar';

export function AppShell({ children }: { children: React.ReactNode }) {
  const {
    timeMode,
    setTimeMode,
    activeView,
    setActiveView,
    isCommandPaletteOpen,
    setIsCommandPaletteOpen,
    setSelectedStation,
  } = useOperational();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [allStations, setAllStations] = useState<StationObservation[]>([]);
  const [kpis, setKpis] = useState<OperationalNetworkKPIs>({
    catalog_stations: null,
    stations_reporting_now: null,
    healthy_count: null,
    watch_count: null,
    probable_fault_count: null,
    critical_count: null,
    stale_count: null,
    open_incidents: null,
    median_data_age_minutes: null,
    engine_status: 'DEGRADED',
    last_eval_timestamp_utc: null,
  });

  useEffect(() => {
    let cancelled = false;

    async function loadNetworkData() {
      try {
        const [stationResponse, incidentResponse] = await Promise.all([
          fetch('/api/stations', { cache: 'no-store' }),
          fetch('/api/incidents?limit=500', { cache: 'no-store' }),
        ]);
        if (!stationResponse.ok) throw new Error('Station service unavailable');
        const data = await stationResponse.json();
        if (!Array.isArray(data)) throw new Error('Invalid station response');
        const mapped = data.map(mapOperationalStation);
        const incidents = incidentResponse.ok ? await incidentResponse.json() : [];
        if (cancelled) return;
        setAllStations(mapped);

        const ages = mapped
          .map(station => station.observation_age_minutes)
          .filter((value): value is number => value !== null)
          .sort((a, b) => a - b);
        const midpoint = Math.floor(ages.length / 2);
        const medianAge = ages.length
          ? (ages.length % 2 ? ages[midpoint] : (ages[midpoint - 1] + ages[midpoint]) / 2)
          : null;
        const latestTimestamp = mapped
          .map(station => station.timestamp_utc)
          .filter((value): value is string => Boolean(value))
          .sort()
          .at(-1) ?? null;

        setKpis({
          catalog_stations: mapped.length,
          stations_reporting_now: mapped.filter(station =>
            ['FRESH', 'DELAYED', 'STALE'].includes(station.observation_status || '')
          ).length,
          healthy_count: mapped.filter(station => station.quality_state === 'NO_ANOMALY_DETECTED').length,
          watch_count: mapped.filter(station => ['WATCH', 'WARMING_UP'].includes(station.quality_state)).length,
          probable_fault_count: mapped.filter(station => station.quality_state === 'PROBABLE_FAULT').length,
          critical_count: mapped.filter(station => station.quality_state === 'CRITICAL').length,
          stale_count: mapped.filter(station =>
            ['DELAYED', 'STALE', 'NO_RECENT_REPORT', 'NOT_OBSERVED_IN_STORE', 'COMMUNICATION_FAILURE'].includes(station.quality_state)
          ).length,
          open_incidents: Array.isArray(incidents) ? incidents.length : null,
          median_data_age_minutes: medianAge,
          engine_status: stationResponse.headers.get('x-skyguard-data-mode') === 'operational-observation-store'
            ? 'OPERATIONAL'
            : 'DEGRADED',
          last_eval_timestamp_utc: latestTimestamp,
        });
      } catch {
        if (!cancelled) setKpis(previous => ({ ...previous, engine_status: 'DEGRADED' }));
      }
    }

    loadNetworkData();
    const interval = window.setInterval(() => {
      if (!document.hidden) loadNetworkData();
    }, 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  return (
    <div className="relative min-h-screen bg-[#F5F9FC] text-[#102A43] flex flex-col font-sans antialiased overflow-x-hidden selection:bg-sky-200 selection:text-slate-950">
      <AtmosphereBackground />
      <div className="relative z-10 min-h-screen flex flex-col">
        <TopBar
          timeMode={timeMode}
          setTimeMode={setTimeMode}
          activeView={activeView}
          setActiveView={setActiveView}
          onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
          engineStatus={kpis.engine_status}
          lastObservationUtc={kpis.last_eval_timestamp_utc ?? undefined}
        />
        <StatusBar kpis={kpis} timeMode={timeMode} />
        <div className="flex-1 flex min-h-0">
          <Sidebar collapsed={sidebarCollapsed} setCollapsed={setSidebarCollapsed} />
          <main className="flex-1 min-w-0 overflow-y-auto bg-white/28 relative flex flex-col">
            {children}
          </main>
        </div>
      </div>
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        stations={allStations}
        onSelectStation={station => setSelectedStation(station)}
      />
    </div>
  );
}
