'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { NeighbourStation, StationObservation, WorkingViewFilter } from '@/lib/types';
import { REGIONAL_BOUNDS } from '@/lib/geo';
import { SKYGUARD_TOKENS } from '@/lib/designTokens';
import { MapLayerType, MapLegend } from './MapLegend';
import { MapToolbar } from './MapToolbar';
import { TimeScrubber } from './TimeScrubber';

interface LiveMapProps {
  stations: StationObservation[];
  selectedStation: StationObservation | null;
  onSelectStation: (station: StationObservation) => void;
  activeView: WorkingViewFilter;
  timeMode: 'UTC' | 'IST';
  neighbours?: NeighbourStation[];
}

function escapeHtml(value: unknown): string {
  return String(value ?? '').replace(/[&<>'"]/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  }[character] || character));
}

function display(value: unknown, suffix: string, digits = 1): string {
  const number = Number(value);
  return value === null || value === undefined || !Number.isFinite(number)
    ? '—'
    : `${number.toFixed(digits)}${suffix}`;
}

const healthColour: any[] = [
  'match', ['get', 'quality_state'],
  'HEALTHY', '#0F9D8A',
  'NO_ANOMALY_DETECTED', '#0F9D8A',
  'NORMAL', '#0F9D8A',
  'normal', '#0F9D8A',
  'GENUINE_WEATHER_EVENT', '#0EA5E9',
  'genuine_weather', '#0EA5E9',
  'WARMING_UP', '#D97706',
  'WATCH', '#D97706',
  'DELAYED', '#D97706',
  'PROBABLE_FAULT', '#EA580C',
  'probable_fault', '#EA580C',
  'CRITICAL', '#DC2626',
  'critical', '#DC2626',
  'SENSOR_FAULT', '#DC2626',
  'sensor_fault', '#DC2626',
  'MULTI_SENSOR_ANOMALY', '#DC2626',
  'COMMUNICATION_FAILURE', '#D97706',
  'STALE', '#64748B',
  'NO_RECENT_REPORT', '#64748B',
  'NOT_OBSERVED_IN_STORE', '#94A3B8',
  'NOT_ASSESSED', '#94A3B8',
  '#0F9D8A',
];

export default function LiveMap({ stations, selectedStation, onSelectStation, activeView, timeMode, neighbours = [] }: LiveMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const popupRef = useRef<any>(null);
  const stationsRef = useRef(stations);
  const onSelectRef = useRef(onSelectStation);
  const geojsonRef = useRef<any>(null);
  const neighbourGeojsonRef = useRef<any>(null);
  const [loaded, setLoaded] = useState(false);
  const [webglSupported, setWebglSupported] = useState(true);
  const [activeLayer, setActiveLayer] = useState<MapLayerType>('STATION_HEALTH');
  const [showTerrain, setShowTerrain] = useState(false);

  const filteredStations = useMemo(() => {
    let rows = stations.filter(station => Number.isFinite(station.latitude) && Number.isFinite(station.longitude) && station.latitude >= 5 && station.latitude <= 39 && station.longitude >= 65 && station.longitude <= 100);
    if (['NORTH_INDIA', 'SOUTH_INDIA', 'EAST_INDIA', 'WEST_CENTRAL'].includes(activeView)) {
      const bounds = REGIONAL_BOUNDS[activeView];
      rows = rows.filter(station => station.latitude >= bounds.minLat && station.latitude <= bounds.maxLat && station.longitude >= bounds.minLon && station.longitude <= bounds.maxLon);
    } else if (activeView === 'CRITICAL_STATIONS') {
      rows = rows.filter(station => ['PROBABLE_FAULT', 'CRITICAL', 'MULTI_SENSOR_ANOMALY', 'SENSOR_FAULT'].includes(station.quality_state));
    } else if (activeView === 'ACTIVE_INCIDENTS') {
      rows = rows.filter(station => (station.active_incident_count || 0) > 0 || ['PROBABLE_FAULT', 'CRITICAL', 'MULTI_SENSOR_ANOMALY', 'SENSOR_FAULT', 'COMMUNICATION_FAILURE'].includes(station.quality_state));
    } else if (activeView === 'HOLDOUT_SET') {
      rows = rows.filter(station => station.is_benchmark === true);
    }
    return rows;
  }, [activeView, stations]);

  const geojson = useMemo(() => ({
    type: 'FeatureCollection',
    features: filteredStations.map(station => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [station.longitude, station.latitude] },
      properties: {
        station_id: station.station_id,
        station_name: station.station_name,
        state: station.state || 'India AWS',
        district: station.district || '',
        quality_state: station.quality_state || 'NO_ANOMALY_DETECTED',
        temperature: station.temperature,
        pressure: station.pressure,
        relative_humidity: station.relative_humidity,
        anomaly_score: station.anomaly_score,
        root_cause: station.root_cause || '',
        observation_age_minutes: station.observation_age_minutes,
        source: station.source,
        pressure_type: station.pressure_type || 'STATION_PRESSURE',
        humidity_type: station.humidity_observation_type || 'DIRECT_SENSOR',
        has_temperature: station.temperature === null ? 0 : 1,
        has_pressure: station.pressure === null ? 0 : 1,
        has_humidity: station.relative_humidity === null ? 0 : 1,
        has_score: station.anomaly_score === null || station.anomaly_score === undefined ? 0 : 1,
        has_observation: station.timestamp_utc ? 1 : 0,
        is_selected: selectedStation?.station_id === station.station_id ? 1 : 0,
      },
    })),
  }), [filteredStations, selectedStation]);

  const neighbourGeojson = useMemo(() => ({
    type: 'FeatureCollection',
    features: selectedStation ? neighbours
      .filter(neighbour => Number.isFinite(neighbour.latitude) && Number.isFinite(neighbour.longitude))
      .map(neighbour => ({
        type: 'Feature',
        geometry: { type: 'LineString', coordinates: [[selectedStation.longitude, selectedStation.latitude], [neighbour.longitude, neighbour.latitude]] },
        properties: { distance_km: neighbour.distance_km, neighbour_name: neighbour.station_name },
      })) : [],
  }), [neighbours, selectedStation]);

  const latestObservationUtc = useMemo(() => stations.reduce<string | null>((latest, station) => station.timestamp_utc && (!latest || station.timestamp_utc > latest) ? station.timestamp_utc : latest, null), [stations]);
  const reportingCount = useMemo(() => stations.filter(station => station.timestamp_utc !== null).length, [stations]);

  stationsRef.current = stations;
  onSelectRef.current = onSelectStation;
  geojsonRef.current = geojson;
  neighbourGeojsonRef.current = neighbourGeojson;

  useEffect(() => {
    if (!containerRef.current) return;
    let map: any;
    let disposed = false;

    async function initialise() {
      try {
        const maplibreModule: any = await import('maplibre-gl');
        const library = maplibreModule.default || maplibreModule;
        if (typeof library.supported === 'function' && !library.supported()) {
          setWebglSupported(false);
          return;
        }
        const MapConstructor = maplibreModule.Map || library.Map || library;
        const PopupConstructor = maplibreModule.Popup || library.Popup;
        const AttributionControl = maplibreModule.AttributionControl || library.AttributionControl;
        map = new MapConstructor({
          container: containerRef.current,
          style: {
            version: 8,
            glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
            sources: {
              voyager: { type: 'raster', tiles: SKYGUARD_TOKENS.map.cartoVoyagerRasterUrls, tileSize: 256, attribution: '&copy; OpenStreetMap contributors &copy; CARTO' },
              positron: { type: 'raster', tiles: SKYGUARD_TOKENS.map.cartoLightRasterUrls, tileSize: 256, attribution: '&copy; OpenStreetMap contributors &copy; CARTO' },
              terrain: { type: 'raster', tiles: ['https://a.tile.opentopomap.org/{z}/{x}/{y}.png', 'https://b.tile.opentopomap.org/{z}/{x}/{y}.png', 'https://c.tile.opentopomap.org/{z}/{x}/{y}.png'], tileSize: 256, attribution: 'Map data &copy; OpenStreetMap contributors, SRTM | map style &copy; OpenTopoMap' },
            },
            layers: [
              { id: 'voyager', type: 'raster', source: 'voyager', minzoom: 0, maxzoom: 19 },
              { id: 'positron', type: 'raster', source: 'positron', minzoom: 0, maxzoom: 19, layout: { visibility: 'none' } },
              { id: 'terrain', type: 'raster', source: 'terrain', minzoom: 0, maxzoom: 17, layout: { visibility: 'none' } },
            ],
          },
          center: SKYGUARD_TOKENS.map.indiaCenter,
          zoom: SKYGUARD_TOKENS.map.defaultZoom,
          minZoom: SKYGUARD_TOKENS.map.minZoom,
          maxZoom: SKYGUARD_TOKENS.map.maxZoom,
          maxBounds: [[58, 4], [104, 39]],
          attributionControl: false,
        });
        if (AttributionControl) map.addControl(new AttributionControl({ compact: true }), 'bottom-right');
        popupRef.current = new PopupConstructor({ closeButton: false, closeOnClick: false, offset: 12, maxWidth: '320px' });

        map.on('load', () => {
          if (disposed) return;
          mapRef.current = map;
          map.fitBounds(SKYGUARD_TOKENS.map.indiaBounds, { padding: 38, duration: 0 });

          // 1. Neighbour connection lines
          map.addSource('neighbour-lines', { type: 'geojson', data: neighbourGeojsonRef.current });
          map.addLayer({
            id: 'neighbour-lines',
            type: 'line',
            source: 'neighbour-lines',
            paint: {
              'line-color': '#1769AA',
              'line-width': 2,
              'line-dasharray': [2, 2],
              'line-opacity': 0.7,
            },
          });

          // 2. Unclustered station points covering all 1,008 stations across India
          map.addSource('stations', {
            type: 'geojson',
            data: geojsonRef.current,
            cluster: false,
          });

          // 3. Glowing halo on anomalous stations
          map.addLayer({
            id: 'fault-glow',
            type: 'circle',
            source: 'stations',
            filter: [
              'any',
              ['==', ['get', 'quality_state'], 'PROBABLE_FAULT'],
              ['==', ['get', 'quality_state'], 'CRITICAL'],
              ['==', ['get', 'quality_state'], 'MULTI_SENSOR_ANOMALY'],
              ['==', ['get', 'quality_state'], 'SENSOR_FAULT'],
            ],
            paint: {
              'circle-radius': ['interpolate', ['linear'], ['zoom'], 3.5, 9.0, 5.5, 12.0, 8.0, 18.0],
              'circle-color': 'rgba(220, 38, 38, 0.22)',
              'circle-stroke-color': '#DC2626',
              'circle-stroke-width': 1.4,
            },
          });

          // 4. Highlight ring around selected station
          map.addLayer({
            id: 'selected-ring',
            type: 'circle',
            source: 'stations',
            filter: ['==', ['get', 'is_selected'], 1],
            paint: {
              'circle-radius': ['interpolate', ['linear'], ['zoom'], 3.5, 10.0, 5.5, 13.0, 8.0, 20.0],
              'circle-color': 'rgba(37, 99, 235, 0.20)',
              'circle-stroke-color': '#2563EB',
              'circle-stroke-width': 2.8,
            },
          });

          // 5. Crisp, high-visibility station dots with white borders (like on Render)
          map.addLayer({
            id: 'station-dots',
            type: 'circle',
            source: 'stations',
            paint: {
              'circle-radius': [
                'interpolate', ['linear'], ['zoom'],
                3.5, 4.5,
                5.0, 6.0,
                7.0, 8.0,
                10.0, 11.5,
              ],
              'circle-color': healthColour,
              'circle-stroke-color': '#FFFFFF',
              'circle-stroke-width': 1.6,
              'circle-opacity': 0.96,
            },
          });

          // Click handler on any station dot: opens station inspection drawer
          map.on('click', 'station-dots', (event: any) => {
            const stationId = event.features?.[0]?.properties?.station_id;
            const station = stationsRef.current.find(item => item.station_id === stationId);
            if (station) {
              onSelectRef.current(station);
            }
          });

          // Hover handler on station dot: displays meteorological tooltip
          map.on('mouseenter', 'station-dots', (event: any) => {
            map.getCanvas().style.cursor = 'pointer';
            const feature = event.features?.[0];
            if (!feature) return;
            const p = feature.properties;
            const isFault = ['PROBABLE_FAULT', 'CRITICAL', 'MULTI_SENSOR_ANOMALY', 'SENSOR_FAULT'].includes(p.quality_state);
            const badgeColor = isFault ? '#DC2626' : p.quality_state === 'GENUINE_WEATHER_EVENT' ? '#0284C7' : '#059669';
            const badgeBg = isFault ? '#FEF2F2' : p.quality_state === 'GENUINE_WEATHER_EVENT' ? '#F0F9FF' : '#ECFDF5';

            const scoreStr = p.anomaly_score != null ? Number(p.anomaly_score).toFixed(3) : '—';
            const rootCauseStr = p.root_cause ? `<div style="margin-top:6px;font-size:10px;color:#991B1B;background:#FEF2F2;border:1px solid #FECACA;border-radius:6px;padding:3px 6px;"><b>Diagnosis:</b> ${escapeHtml(p.root_cause)}</div>` : '';

            const html = `
              <div style="font-family:Inter,system-ui,sans-serif;padding:4px;min-width:240px;color:#102A43;">
                <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
                  <strong style="font-size:13px;font-weight:800;color:#0F172A;">${escapeHtml(p.station_name)}</strong>
                  <span style="font-size:9px;font-weight:700;padding:2px 6px;border-radius:999px;background:${badgeBg};color:${badgeColor};">${escapeHtml(p.quality_state)}</span>
                </div>
                <div style="margin:2px 0 8px;font:10px ui-monospace,monospace;color:#64748B;">
                  ${escapeHtml(p.station_id)} · ${escapeHtml(p.state)}
                </div>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:5px;">
                  <div style="padding:6px 4px;background:#FFF7ED;border-radius:7px;text-align:center;">
                    <b style="display:block;font-size:12px;font-weight:800;color:#C2410C;">${display(p.temperature, '°C')}</b>
                    <span style="font-size:9px;color:#9A3412;">Temp</span>
                  </div>
                  <div style="padding:6px 4px;background:#EFF6FF;border-radius:7px;text-align:center;">
                    <b style="display:block;font-size:12px;font-weight:800;color:#1D4ED8;">${display(p.pressure, 'hPa')}</b>
                    <span style="font-size:9px;color:#1E40AF;">Press</span>
                  </div>
                  <div style="padding:6px 4px;background:#F5F3FF;border-radius:7px;text-align:center;">
                    <b style="display:block;font-size:12px;font-weight:800;color:#6D28D9;">${display(p.relative_humidity, '%')}</b>
                    <span style="font-size:9px;color:#5B21B6;">RH</span>
                  </div>
                </div>
                <div style="margin-top:6px;display:flex;align-items:center;justify-content:space-between;font-size:9.5px;color:#64748B;">
                  <span>QC Evidence Score: <b style="color:${badgeColor}">${scoreStr}</b></span>
                  <span style="color:#0284C7;font-weight:600;">Click to inspect →</span>
                </div>
                ${rootCauseStr}
              </div>
            `;
            popupRef.current.setLngLat(feature.geometry.coordinates).setHTML(html).addTo(map);
          });

          map.on('mouseleave', 'station-dots', () => {
            map.getCanvas().style.cursor = '';
            popupRef.current?.remove();
          });

          setLoaded(true);
        });
      } catch {
        setWebglSupported(false);
      }
    }
    initialise();
    return () => {
      disposed = true;
      popupRef.current?.remove();
      mapRef.current = null;
      if (map) map.remove();
    };
  }, []);

  useEffect(() => {
    if (!loaded) return;
    mapRef.current?.getSource('stations')?.setData(geojson);
  }, [geojson, loaded]);

  useEffect(() => {
    if (!loaded) return;
    mapRef.current?.getSource('neighbour-lines')?.setData(neighbourGeojson);
  }, [loaded, neighbourGeojson]);

  useEffect(() => {
    if (!loaded) return;
    mapRef.current?.setLayoutProperty('terrain', 'visibility', showTerrain ? 'visible' : 'none');
    mapRef.current?.setLayoutProperty('voyager', 'visibility', showTerrain ? 'none' : 'visible');
  }, [loaded, showTerrain]);

  useEffect(() => {
    const map = mapRef.current;
    if (!loaded || !map?.getLayer('station-dots')) return;
    let colour: any[] = healthColour;
    if (activeLayer === 'TEMPERATURE') colour = ['case', ['==', ['get', 'has_temperature'], 1], ['interpolate', ['linear'], ['get', 'temperature'], 0, '#2563EB', 20, '#0EA5E9', 30, '#0F9D8A', 38, '#D97706', 48, '#DC4C4C'], '#94A3B8'];
    if (activeLayer === 'PRESSURE') colour = ['case', ['==', ['get', 'has_pressure'], 1], ['interpolate', ['linear'], ['get', 'pressure'], 850, '#7C3AED', 970, '#2563EB', 1010, '#0EA5E9', 1040, '#0F9D8A'], '#94A3B8'];
    if (activeLayer === 'RELATIVE_HUMIDITY') colour = ['case', ['==', ['get', 'has_humidity'], 1], ['interpolate', ['linear'], ['get', 'relative_humidity'], 10, '#D97706', 45, '#38BDF8', 75, '#2563EB', 100, '#7C3AED'], '#94A3B8'];
    if (activeLayer === 'ANOMALY_SCORE') colour = ['case', ['==', ['get', 'has_score'], 1], ['interpolate', ['linear'], ['get', 'anomaly_score'], 0, '#0F9D8A', .45, '#D97706', .75, '#DC4C4C'], '#94A3B8'];
    if (activeLayer === 'FRESHNESS') colour = ['case', ['==', ['get', 'has_observation'], 1], ['interpolate', ['linear'], ['get', 'observation_age_minutes'], 0, '#0F9D8A', 90, '#0EA5E9', 180, '#D97706', 720, '#64748B'], '#94A3B8'];
    map.setPaintProperty('station-dots', 'circle-color', colour);
  }, [activeLayer, loaded]);

  useEffect(() => {
    if (loaded && selectedStation) {
      mapRef.current?.flyTo({
        center: [selectedStation.longitude, selectedStation.latitude],
        zoom: Math.max(mapRef.current.getZoom(), 7),
        duration: 750,
      });
    }
  }, [loaded, selectedStation]);

  if (!webglSupported) {
    return (
      <div className="min-h-[580px] overflow-y-auto bg-[#EDF6FB] p-5">
        <div className="rounded-2xl border border-[#D8E6EF] bg-white p-5">
          <h3 className="font-extrabold text-[#102A43]">Map unavailable on this device</h3>
          <p className="mt-1 text-xs text-[#52667A]">WebGL could not start. Station selection remains available below; no station values are generated.</p>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {filteredStations.slice(0, 60).map(station => (
              <button key={station.station_id} onClick={() => onSelectStation(station)} className="min-h-11 rounded-xl border border-slate-200 p-3 text-left text-xs hover:bg-sky-50">
                <strong className="block text-[#102A43]">{station.station_name}</strong>
                <span className="text-slate-500">{station.quality_state} · {station.timestamp_utc ? 'observed' : 'catalog only'}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex min-h-[580px] w-full flex-col overflow-hidden bg-[#EDF6FB]">
      <div ref={containerRef} className="min-h-[580px] flex-1" aria-label="Interactive India weather-station map" />
      <div className="absolute left-3 top-3 z-20">
        <MapToolbar
          activeLayer={activeLayer}
          setActiveLayer={setActiveLayer}
          showTerrainContext={showTerrain}
          setShowTerrainContext={setShowTerrain}
          onZoomIn={() => mapRef.current?.zoomIn()}
          onZoomOut={() => mapRef.current?.zoomOut()}
          onResetView={() => mapRef.current?.fitBounds(SKYGUARD_TOKENS.map.indiaBounds, { padding: 38, duration: 650 })}
        />
      </div>
      <div className="absolute right-3 top-3 z-20 hidden max-w-xs flex-col items-end gap-2 sm:flex">
        <div className="rounded-xl border border-[#D8E6EF] bg-white/95 px-3 py-2 text-[10px] text-[#52667A] shadow-lg backdrop-blur-xl">
          <strong className="text-[#102A43]">{filteredStations.length}</strong> catalog points · <strong className="text-[#0F9D8A]">{filteredStations.filter(station => station.timestamp_utc).length}</strong> observed
        </div>
        <MapLegend activeLayer={activeLayer} />
      </div>
      <div className="absolute bottom-4 left-3 right-3 z-20 mx-auto max-w-3xl">
        <TimeScrubber timeMode={timeMode} latestObservationUtc={latestObservationUtc} reportingCount={reportingCount} />
      </div>
    </div>
  );
}
