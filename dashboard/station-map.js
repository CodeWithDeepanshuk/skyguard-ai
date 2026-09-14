/* ==========================================================================
   SkyGuard AI · Interactive Leaflet Station Map (Light Meteorological Theme)
   ========================================================================== */

window.SkyGuardMap = (() => {
  let map, markers, tiles, bounds, fitted = false;
  let fullMap, fullMarkers;

  const zoneColors = {
    'Central Plateau': '#0D9488',
    'Coastal Plains': '#0284C7',
    'Indo-Gangetic Plains': '#2563EB',
    'Deccan Plateau': '#D97706',
    'Northeast Hills': '#7C3AED',
    'Western Arid/Semi-Arid': '#EA580C',
    'Northern Himalayas': '#4F46E5',
    'Island Territories': '#059669',
  };

  function init() {
    if (map) return;
    map = L.map('station-map', {
      minZoom: 4,
      maxZoom: 12,
      scrollWheelZoom: true,
      maxBounds: [[5.0, 65.0], [38.5, 100.0]],
      maxBoundsViscosity: 1.0
    }).setView([22.8, 79.5], 5);

    map.createPane('offlineLand');
    map.getPane('offlineLand').style.zIndex = '150';
    markers = L.layerGroup().addTo(map);
    L.control.scale({ imperial: false, position: 'bottomleft' }).addTo(map);

    const fullEl = document.getElementById('fullscreen-map');
    if (fullEl && !fullMap) {
      fullMap = L.map('fullscreen-map', {
        minZoom: 4,
        maxZoom: 12,
        scrollWheelZoom: true,
        maxBounds: [[5.0, 65.0], [38.5, 100.0]],
        maxBoundsViscosity: 1.0
      }).setView([22.8, 79.5], 5);
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        noWrap: true,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      }).addTo(fullMap);
      fullMarkers = L.layerGroup().addTo(fullMap);
      new ResizeObserver(() => fullMap.invalidateSize({ pan: false })).observe(fullEl);
    }

    const status = document.getElementById('map-status');

    // Offline coastline fallback
    fetch('/assets/maps/land.geojson')
      .then(r => {
        if (!r.ok) throw new Error('Coastline unavailable');
        return r.json();
      })
      .then(data => {
        L.geoJSON(data, {
          interactive: false,
          pane: 'offlineLand',
          style: {
            color: '#CBD5E1',
            weight: 1,
            fillColor: '#F1F5F9',
            fillOpacity: 1
          }
        }).addTo(map);
      })
      .catch(() => {
        if (status) status.textContent = 'Station coordinates active across Indian subcontinent.';
      });

    // Clean OpenStreetMap Tiles - No API Key Required, No Watermark
    tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      noWrap: true,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });
    tiles.addTo(map);

    const fitBtn = document.getElementById('map-fit');
    if (fitBtn) {
      fitBtn.onclick = () => {
        map.fitBounds([[7.0, 67.0], [37.0, 98.0]], { padding: [15, 15] });
        if (fullMap) fullMap.fitBounds([[7.0, 67.0], [37.0, 98.0]], { padding: [15, 15] });
      };
    }

    const worldBtn = document.getElementById('map-world');
    if (worldBtn) {
      worldBtn.onclick = () => {
        map.fitBounds([[7.0, 67.0], [37.0, 98.0]]);
        if (fullMap) fullMap.fitBounds([[7.0, 67.0], [37.0, 98.0]]);
      };
    }

    const mapElement = document.getElementById('station-map');
    if (mapElement) {
      new ResizeObserver(() => map.invalidateSize({ pan: false })).observe(mapElement);
    }
  }

  return {
    reset() {
      init();
      markers.clearLayers();
      if (fullMarkers) fullMarkers.clearLayers();
      bounds = L.latLngBounds([]);
      const dir = document.getElementById('station-directory');
      if (dir) dir.replaceChildren();
    },

    add(station, record, selected, onSelect, options = {}) {
      const lat = Number(station.latitude), lon = Number(station.longitude);
      if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) return;
      bounds.extend([lat, lon]);

      const isBenchmark = Boolean(
        station.is_benchmark == 1 ||
        station.evaluation_role === 'development' ||
        station.evaluation_role === 'station_holdout'
      );

      const statusMap = {
        healthy: '#16A34A',
        monitor: '#F59E0B',
        watch: '#F59E0B',
        degrading: '#EA580C',
        critical: '#DC2626',
        sensor_fault: '#DC2626'
      };

      const isReferenceOnly = Boolean(
        station.is_reference_only ||
        record.is_reference_only ||
        record.source_type === 'REFERENCE_MODEL'
      );

      const isCritical = record.status === 'critical' || record.status === 'sensor_fault' || record.has_active_fault;
      const markerColor = isReferenceOnly 
        ? '#0284C7' 
        : (statusMap[record.status] || (isBenchmark ? '#2563EB' : (zoneColors[station.climate_zone] || '#64748B')));
      const label = `${station.station_name} (${station.icao || station.station_id})${isReferenceOnly ? ' [REFERENCE MODEL]' : ''}`;
      const zoneTag = station.climate_zone || 'India AWS';
      const coordinate = `${Math.abs(lat).toFixed(4)}°${lat >= 0 ? 'N' : 'S'}, ${Math.abs(lon).toFixed(4)}°${lon >= 0 ? 'E' : 'W'}`;

      const pulseClass = isCritical ? ' anomaly-pulsing' : '';
      const iconSize = isBenchmark || isCritical ? [18, 18] : [13, 13];
      const anchorSize = isBenchmark || isCritical ? [9, 9] : [6.5, 6.5];

      const icon = L.divIcon({
        className: 'station-div-icon',
        iconSize,
        iconAnchor: anchorSize,
        html: `<div class="station-marker-pin${pulseClass}${selected ? ' active' : ''}" style="--marker-color:${markerColor}; width:${iconSize[0]}px; height:${iconSize[1]}px; border-radius:${isReferenceOnly ? '2px' : '50%'};"></div>`
      });

      const marker = L.marker([lat, lon], { icon, title: label, keyboard: true }).addTo(markers);

      const health = isReferenceOnly 
        ? 'Independent Reference Model' 
        : (record.label || record.status || (station.is_active_2024_plus ? 'Active 2024+' : 'AWS Station'));
      const score = isReferenceOnly ? ' (Open-Meteo)' : (record.score == null ? '' : ` · Health: ${Number(record.score).toFixed(1)}/100`);
      const tempRead = record.temperature != null ? ` · Temp: <b>${record.temperature}°C</b>` : '';

      const tooltipContent = `
        <div style="font-size:12px; line-height:1.4; padding:2px;">
          <strong style="color:#0F172A; font-size:13px;">${station.station_name}</strong>
          <small style="color:#64748B; display:block;">${station.state ? station.state + ' · ' : ''}${zoneTag}</small>
          <div style="margin-top:4px; display:flex; align-items:center; gap:6px;">
            <span style="display:inline-block; width:8px; height:8px; border-radius:${isReferenceOnly ? '2px' : '50%'}; background-color:${markerColor};"></span>
            <span style="font-weight:600; color:${markerColor};">${health}${score}</span>
          </div>
          ${tempRead ? `<div style="margin-top:2px; font-size:11px; color:#475569;">${tempRead}</div>` : ''}
          ${isReferenceOnly ? `<div style="margin-top:4px; font-size:10px; color:#0369A1; font-weight:600; background:#F0F9FF; padding:2px 4px; border-radius:4px;">Independent NWP Reference · Not physical IMD AWS</div>` : ''}
        </div>
      `;

      marker.bindTooltip(tooltipContent, { className: 'light-map-tooltip', direction: 'top', offset: [0, -8] })
            .on('click', () => {
              onSelect();
            });

      if (fullMarkers) {
        const fullM = L.marker([lat, lon], { icon, title: label, keyboard: true }).addTo(fullMarkers);
        fullM.bindTooltip(tooltipContent, { className: 'light-map-tooltip', direction: 'top', offset: [0, -8] })
             .on('click', () => onSelect());
      }

      // Render into station directory table if requested
      if (options.renderCard !== false) {
        const dir = document.getElementById('station-directory');
        if (dir) {
          const item = document.createElement('div');
          item.className = `station-list-card${selected ? ' selected' : ''}`;
          item.dataset.stationId = station.station_id;
          item.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <strong>${station.station_name}</strong>
              <span style="font-size:11px; font-weight:600; color:${markerColor};">${health}</span>
            </div>
            <small style="color:#64748B;">${zoneTag} · ${coordinate}</small>
          `;
          item.onclick = () => {
            map.setView([lat, lon], Math.max(map.getZoom(), 8));
            onSelect();
          };
          dir.appendChild(item);
        }
      }
    },

    setView(lat, lon, zoom = 8) {
      if (map) map.setView([lat, lon], zoom);
    },

    invalidateFull() {
      if (fullMap) {
        fullMap.invalidateSize({ pan: false });
        fullMap.fitBounds([[7.0, 67.0], [37.0, 98.0]], { padding: [15, 15] });
      }
      if (map) {
        map.invalidateSize({ pan: false });
      }
    },

    finish() {
      if (!fitted) {
        map.fitBounds([[7.0, 67.0], [37.0, 98.0]], { padding: [15, 15] });
        fitted = true;
      }
    }
  };
})();
