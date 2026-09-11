/* Local Leaflet and Natural Earth coastlines keep station navigation available offline. */
window.SkyGuardMap = (() => {
  let map, markers, tiles, bounds, fitted = false;
  const zoneColors = {
    'Central Plateau': '#20c997',
    'Coastal Plains': '#00d2d3',
    'Indo-Gangetic Plains': '#4da6ff',
    'Deccan Plateau': '#ffbe53',
    'Northeast Hills': '#a55eea',
    'Western Arid/Semi-Arid': '#fd9644',
    'Northern Himalayas': '#70a1ff',
    'Island Territories': '#2ed573',
  };

  function init() {
    if (map) return;
    map = L.map('station-map', {minZoom: 1, maxZoom: 18, scrollWheelZoom: false,
      maxBounds: [[-85, -180], [85, 180]], maxBoundsViscosity: 1}).setView([22.5, 79.5], 5);
    map.createPane('offlineLand');
    map.getPane('offlineLand').style.zIndex = '150';
    markers = L.layerGroup().addTo(map);
    L.control.scale({imperial: false}).addTo(map);
    map.attributionControl.addAttribution('<a href="https://www.naturalearthdata.com/">Natural Earth</a>');
    const status = document.getElementById('map-status');
    fetch('/assets/maps/land.geojson').then(r => {
      if (!r.ok) throw new Error('Coastline unavailable');
      return r.json();
    }).then(data => L.geoJSON(data, {interactive: false, pane: 'offlineLand',
      style: {color: '#628694', weight: 1, fillColor: '#203e49', fillOpacity: 1}}).addTo(map))
      .catch(() => { if (status) status.textContent = 'Offline coastline unavailable. Station coordinates remain visible.'; });
    tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, noWrap: true,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });
    const detail = document.getElementById('map-detail');
    function detailChanged() {
      if (detail && detail.checked) { tiles.addTo(map); if (status) status.textContent = 'Street map · drag to pan · + / − or pinch to zoom'; }
      else { map.removeLayer(tiles); if (status) status.textContent = 'Offline world coastline · coarse detail · station positions are unchanged'; }
    }
    tiles.on('tileerror', () => {
      if (detail && map.hasLayer(tiles)) { detail.checked = false; detailChanged(); }
    });
    if (detail) {
      detail.addEventListener('change', detailChanged);
      if (!navigator.onLine) detail.checked = false;
      detailChanged();
    }
    const fitBtn = document.getElementById('map-fit');
    if (fitBtn) fitBtn.onclick = () => { if (bounds?.isValid()) map.fitBounds(bounds.pad(0.08), {maxZoom: 9}); else map.setView([22.5, 79.5], 5); };
    const worldBtn = document.getElementById('map-world');
    if (worldBtn) worldBtn.onclick = () => map.setView([15, 0], 2);
    new ResizeObserver(() => map.invalidateSize({pan: false})).observe(document.getElementById('station-map'));
  }

  return {
    reset() {
      init();
      markers.clearLayers();
      bounds = L.latLngBounds([]);
      const dir = document.getElementById('station-directory');
      if (dir) dir.replaceChildren();
    },
    add(station, record, selected, onSelect, options = {}) {
      const lat = Number(station.latitude), lon = Number(station.longitude);
      if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) return;
      bounds.extend([lat, lon]);
      
      const isBenchmark = Boolean(station.is_benchmark == 1 || station.evaluation_role === 'development' || station.evaluation_role === 'station_holdout');
      const baseColor = isBenchmark ? '#37d6cf' : (zoneColors[station.climate_zone] || '#a0b4bf');
      const statusColor = {healthy: '#60d6a2', monitor: '#ffc76a', degrading: '#ff706e', critical: '#ff706e'}[record.status];
      const color = (record.status && record.status !== 'unknown') ? statusColor : baseColor;
      
      const label = `${station.station_name} (${station.icao || station.station_id})`;
      const zoneTag = station.climate_zone || 'India AWS';
      const sizeClass = isBenchmark ? 'benchmark-station-dot' : 'network-station-dot';
      
      const icon = L.divIcon({
        className: 'earth-station-icon',
        iconSize: isBenchmark ? [24, 24] : [16, 16],
        iconAnchor: isBenchmark ? [12, 12] : [8, 8],
        html: `<span class="earth-station-dot ${sizeClass}${selected ? ' active' : ''}" style="--marker-color:${color}"></span>`
      });
      
      const marker = L.marker([lat, lon], {icon, title: label, alt: label, keyboard: true}).addTo(markers);
      const coordinate = `${Math.abs(lat).toFixed(4)}°${lat >= 0 ? 'N' : 'S'}, ${Math.abs(lon).toFixed(4)}°${lon >= 0 ? 'E' : 'W'}`;
      const health = record.label || record.status || (station.is_active_2024_plus ? 'Active 2024+' : 'Historical AWS');
      const score = record.score == null ? '' : ` · Health ${Number(record.score).toFixed(1)}/100`;
      const elev = station.elevation_m ? ` · ${Math.round(station.elevation_m)}m ASL` : '';
      
      const tooltip = document.createElement('div');
      tooltip.className = 'station-map-tooltip';
      tooltip.innerHTML = `<b>${label}</b><br><small>${zoneTag}${elev} · ${coordinate}</small><br><span style="color:${color};font-weight:700;">${health}${score}</span>`;
      marker.bindTooltip(tooltip).on('click', onSelect);

      if (options.renderCard !== false) {
        const dir = document.getElementById('station-directory');
        if (dir) {
          const button = document.createElement('button');
          button.type = 'button';
          button.className = `station-directory-card${selected ? ' selected' : ''}${isBenchmark ? ' benchmark' : ''}`;
          button.style.setProperty('--marker-color', color);
          button.dataset.stationId = station.station_id;
          button.dataset.zone = zoneTag;
          
          const titleLine = document.createElement('span');
          titleLine.innerHTML = `<b>${station.station_name}</b> <small>${station.icao || station.station_id}</small>`;
          button.appendChild(titleLine);
          
          const metaLine = document.createElement('span');
          metaLine.className = 'card-meta';
          metaLine.textContent = `${zoneTag}${elev} · ${coordinate}`;
          button.appendChild(metaLine);
          
          const statusLine = document.createElement('span');
          statusLine.className = 'card-status';
          statusLine.style.color = color;
          statusLine.textContent = `${health}${score}`;
          button.appendChild(statusLine);
          
          button.onclick = () => { map.setView([lat, lon], Math.max(map.getZoom(), 8)); onSelect(); };
          dir.appendChild(button);
        }
      }
    },
    setView(lat, lon, zoom = 8) {
      if (map) map.setView([lat, lon], zoom);
    },
    finish() {
      if (!fitted && bounds.isValid()) {
        map.fitBounds(bounds.pad(0.08), {maxZoom: 9});
        fitted = true;
      }
    }
  };
})();

