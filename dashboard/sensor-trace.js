/* ==========================================================================
   SkyGuard AI · Sensor Trace Chart (Light Meteorological SVG Renderer)
   Supports:
   1. 3-Trace Comparison: Observed In-Situ, Open-Meteo Reference, MADIS Spatial Consensus
   2. Time Window Filtering: 1h, 6h, 24h, 7d
   3. Tap-to-Inspect Value Readout for Touchscreens & Mobile Devices
   4. Anomaly Markers with Visual Highlight
   ========================================================================== */

window.currentSensorTimeWindow = '24h';
window.currentInspectedPoint = null;

window.renderSensorTrace = (rows, activeParameter = 'all', tripletTraces = null, timeWindow = null) => {
  const host = document.getElementById('sensor-chart');
  if (!host) return;

  if (timeWindow) {
    window.currentSensorTimeWindow = timeWindow;
  }
  const activeWindow = window.currentSensorTimeWindow || '24h';

  const ns = 'http://www.w3.org/2000/svg';
  const element = (name, attrs, text) => {
    const node = document.createElementNS(ns, name);
    Object.entries(attrs || {}).forEach(([k, v]) => node.setAttribute(k, v));
    if (text != null) node.textContent = text;
    return node;
  };

  const rawValidRows = (rows || []).filter(r => Number.isFinite(Date.parse(r.timestamp_utc)));

  // Time window filter
  const windowMillis = {
    '1h': 3600000,
    '6h': 6 * 3600000,
    '24h': 24 * 3600000,
    '7d': 7 * 24 * 3600000,
  }[activeWindow] || (24 * 3600000);

  let maxTime = rawValidRows.length ? Math.max(...rawValidRows.map(r => Date.parse(r.timestamp_utc))) : Date.now();
  const minTimeCutoff = maxTime - windowMillis;

  const validRows = rawValidRows.filter(r => Date.parse(r.timestamp_utc) >= minTimeCutoff);

  const signature = JSON.stringify([
    (validRows || []).map(r => [r.station_id, r.timestamp_utc, r.temperature, r.pressure, r.humidity]),
    activeWindow,
    tripletTraces ? 'triplet' : 'standard'
  ]);
  const changed = host.dataset.signature !== signature;
  host.dataset.signature = signature;
  host.replaceChildren();

  // Create Window Selector & Inspection Tooltip Bar
  const controlsBar = document.createElement('div');
  controlsBar.className = 'sensor-chart-controls-bar';
  controlsBar.innerHTML = `
    <div class="chart-window-pills" role="radiogroup" aria-label="Select Telemetry Time Span">
      <button class="window-pill ${activeWindow === '1h' ? 'active' : ''}" data-window="1h" type="button">1 Hour</button>
      <button class="window-pill ${activeWindow === '6h' ? 'active' : ''}" data-window="6h" type="button">6 Hours</button>
      <button class="window-pill ${activeWindow === '24h' ? 'active' : ''}" data-window="24h" type="button">24 Hours</button>
      <button class="window-pill ${activeWindow === '7d' ? 'active' : ''}" data-window="7d" type="button">7 Days</button>
    </div>
    <div class="chart-inspect-banner" id="chart-inspect-banner">
      <span class="inspect-icon">👆</span>
      <span class="inspect-text">Tap or click any data point to inspect exact observation, reference model, and residual.</span>
    </div>
  `;
  host.appendChild(controlsBar);

  // Bind window pill events with backend history fetch trigger
  controlsBar.querySelectorAll('.window-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      const w = btn.dataset.window;
      window.currentSensorTimeWindow = w;
      if (typeof window.onSensorWindowChange === 'function') {
        window.onSensorWindowChange(w);
      } else {
        window.renderSensorTrace(rows, activeParameter, tripletTraces, w);
      }
    });
  });

  // Metadata Banner: Observation count, oldest and newest times, source provenance, and freshness
  const oldestTime = validRows.length ? Math.min(...validRows.map(r => Date.parse(r.timestamp_utc))) : null;
  const newestTime = validRows.length ? Math.max(...validRows.map(r => Date.parse(r.timestamp_utc))) : null;
  const oldestStr = oldestTime ? new Date(oldestTime).toISOString().replace('T', ' ').slice(0, 16) + ' UTC' : '—';
  const newestStr = newestTime ? new Date(newestTime).toISOString().replace('T', ' ').slice(0, 16) + ' UTC' : '—';
  const obsCount = validRows.length;
  const nowMs = Date.now();
  const feedAgeMin = newestTime ? Math.round((nowMs - newestTime) / 60000) : null;
  const freshnessStr = feedAgeMin !== null ? (feedAgeMin <= 20 ? `${feedAgeMin}m ago (Fresh)` : `${feedAgeMin}m ago (Stale Feed)`) : '—';

  const metaBar = document.createElement('div');
  metaBar.className = 'sensor-chart-metadata-bar';
  metaBar.style.cssText = 'display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; font-size:11px; color:#475569; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:6px 12px; margin-bottom:12px;';
  metaBar.innerHTML = `
    <span><strong>Observations in ${activeWindow}:</strong> <span style="color:#0F172A; font-weight:700;">${obsCount}</span> ${obsCount === 1 ? '<span style="color:#D97706; font-weight:600;">(Single observation · Insufficient history for trend line)</span>' : ''}</span>
    <span><strong>Window Extent:</strong> ${oldestStr} → ${newestStr}</span>
    <span><strong>Provenance:</strong> IMD AWS Surface Network</span>
    <span><strong>Freshness:</strong> ${freshnessStr}</span>
  `;
  host.appendChild(metaBar);

  if (!validRows.length && !tripletTraces) {
    const empty = document.createElement('div');
    empty.className = 'chart-empty-state';
    empty.style.cssText = 'padding: 30px 20px; text-align: center; color: #64748B; font-size: 13px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; margin-top: 10px;';
    empty.textContent = `No observations available for the selected ${activeWindow} time span. Telemetry will appear as observations arrive.`;
    host.appendChild(empty);
    return;
  }

  // Determine time extent
  let allTimes = validRows.map(r => Date.parse(r.timestamp_utc));
  if (tripletTraces && tripletTraces.reference_model) {
    tripletTraces.reference_model.forEach(r => {
      const t = Date.parse(r.timestamp_utc);
      if (Number.isFinite(t) && t >= minTimeCutoff) allTimes.push(t);
    });
  }
  if (!allTimes.length) allTimes = [Date.now() - windowMillis, Date.now()];

  const start = Math.min(...allTimes), end = Math.max(...allTimes);
  const leftMargin = 85;
  const rightMargin = 890;
  const plotWidth = rightMargin - leftMargin;
  const x = time => leftMargin + (end === start ? 0.5 : (time - start) / (end - start)) * plotWidth;

  const seriesDefs = [
    ['temperature', 'Temperature', '°C', '#0D9488', '#CCFBF1', 'temperature_c', '🌡️'],
    ['pressure', 'Atmospheric Pressure', 'hPa', '#2563EB', '#DBEAFE', 'pressure_hpa', '🧭'],
    ['humidity', 'Relative Humidity', '% RH', '#D97706', '#FEF3C7', 'relative_humidity_pct', '💧']
  ];

  const seriesToRender = activeParameter === 'all' 
    ? seriesDefs 
    : seriesDefs.filter(([key]) => key === activeParameter);

  for (const [key, title, unit, color, lightColor, paramKey, icon] of seriesToRender) {
    const numeric = value => value !== '' && value != null && Number.isFinite(Number(value));
    const values = validRows.filter(r => numeric(r[key])).map(r => Number(r[key]));

    // Include triplet values in scaling if available
    if (tripletTraces) {
      ['observed', 'reference_model', 'neighbor_consensus'].forEach(tKey => {
        (tripletTraces[tKey] || []).forEach(r => {
          const t = Date.parse(r.timestamp_utc);
          if (t >= minTimeCutoff) {
            const v = r[paramKey] != null ? r[paramKey] : r[key];
            if (numeric(v)) values.push(Number(v));
          }
        });
      });
    }

    const latestVal = values.length ? values[values.length - 1] : null;
    const minVal = values.length ? Math.min(...values) : null;
    const maxVal = values.length ? Math.max(...values) : null;
    const meanVal = values.length ? (values.reduce((a, b) => a + b, 0) / values.length) : null;
    const isSinglePoint = values.length === 1;

    // Outer Box Container for this parameter term
    const box = document.createElement('div');
    box.className = 'parameter-graph-box';
    box.id = `graph-box-${key}`;

    // Box Header with 1-point trend warning pill
    const header = document.createElement('div');
    header.className = 'parameter-graph-header';
    header.innerHTML = `
      <div class="parameter-graph-title">
        <span style="font-size:16px;">${icon}</span>
        <span>${title}</span>
        <span class="stat-pill live">Latest: <strong>${latestVal != null ? latestVal.toFixed(1) : '—'} ${unit}</strong></span>
        ${isSinglePoint ? '<span class="stat-pill warning" style="background:#FEF3C7; color:#92400E; border:1px solid #FCD34D;">1 reading · Insufficient history for trend line</span>' : ''}
      </div>
      <div class="parameter-graph-stats">
        <span class="stat-pill">Min: <strong>${minVal != null ? minVal.toFixed(1) : '—'} ${unit}</strong></span>
        <span class="stat-pill">Max: <strong>${maxVal != null ? maxVal.toFixed(1) : '—'} ${unit}</strong></span>
        <span class="stat-pill">Mean: <strong>${meanVal != null ? meanVal.toFixed(1) : '—'} ${unit}</strong></span>
      </div>
    `;
    box.appendChild(header);

    if (!values.length) {
      const emptyNote = document.createElement('div');
      emptyNote.style.cssText = 'padding: 24px; text-align: center; color: #94A3B8; font-size: 12px;';
      emptyNote.textContent = `No ${title} telemetry reported for this station within ${activeWindow}.`;
      box.appendChild(emptyNote);
      host.appendChild(box);
      continue;
    }

    let low = Math.min(...values), high = Math.max(...values);
    const padding = Math.max((high - low) * 0.18, key === 'pressure' ? 1.2 : 0.6);
    low -= padding;
    high += padding;

    const yTop = 22;
    const yBottom = 125;
    const plotHeight = yBottom - yTop;
    const y = value => yBottom - (value - low) / (high - low) * plotHeight;

    const svg = element('svg', {
      viewBox: '0 0 920 160',
      role: 'img',
      'aria-label': `${title} in ${unit}`,
      class: changed ? 'trace-series updated' : 'trace-series'
    });

    // 1. Grid Lines & Broad Y-axis Ticks
    const numYSteps = 3;
    for (let i = 0; i <= numYSteps; i++) {
      const value = low + (high - low) * (i / numYSteps);
      const py = y(value);

      svg.appendChild(element('line', {
        x1: leftMargin + 1,
        x2: rightMargin,
        y1: py,
        y2: py,
        stroke: '#E2E8F0',
        'stroke-dasharray': '4 4',
        'stroke-width': 1
      }));

      svg.appendChild(element('line', {
        x1: leftMargin - 7,
        y1: py,
        x2: leftMargin,
        y2: py,
        stroke: '#475569',
        'stroke-width': 2
      }));

      svg.appendChild(element('text', {
        x: leftMargin - 11,
        y: py + 4,
        'text-anchor': 'end',
        fill: '#0F172A',
        'font-size': '11px',
        'font-weight': '700'
      }, value.toFixed(1)));
    }

    // 2. Broad Solid Y and X Axis Lines
    svg.appendChild(element('line', {
      x1: leftMargin,
      y1: yTop - 4,
      x2: leftMargin,
      y2: yBottom,
      stroke: '#475569',
      'stroke-width': 2.5
    }));

    svg.appendChild(element('line', {
      x1: leftMargin,
      y1: yBottom,
      x2: rightMargin,
      y2: yBottom,
      stroke: '#475569',
      'stroke-width': 2.5
    }));

    svg.appendChild(element('text', {
      x: leftMargin,
      y: yTop - 10,
      'text-anchor': 'start',
      fill: '#475569',
      'font-weight': '800',
      'font-size': '11px'
    }, `▲ ${unit}`));

    svg.appendChild(element('text', {
      x: rightMargin,
      y: yBottom + 30,
      'text-anchor': 'end',
      fill: '#64748B',
      'font-weight': '700',
      'font-size': '10px'
    }, 'Time (UTC) ▶'));

    // 3. Time labels & Broad X-axis Ticks
    const numXSteps = 4;
    for (let i = 0; i <= numXSteps; i++) {
      const tVal = start + (end - start) * (i / numXSteps);
      const px = x(tVal);

      svg.appendChild(element('line', {
        x1: px,
        y1: yBottom,
        x2: px,
        y2: yBottom + 6,
        stroke: '#475569',
        'stroke-width': 2
      }));

      if (i > 0 && i < numXSteps) {
        svg.appendChild(element('line', {
          x1: px,
          y1: yTop,
          x2: px,
          y2: yBottom - 1,
          stroke: '#F1F5F9',
          'stroke-dasharray': '3 3',
          'stroke-width': 1
        }));
      }

      const dateObj = new Date(tVal);
      const timeStr = activeWindow === '7d'
        ? `${dateObj.getDate()} ${dateObj.toLocaleString('en-IN', { month: 'short' })}`
        : dateObj.toISOString().slice(11, 16) + ' UTC';

      svg.appendChild(element('text', {
        x: px,
        y: yBottom + 18,
        'text-anchor': i === 0 ? 'start' : (i === numXSteps ? 'end' : 'middle'),
        fill: '#1E293B',
        'font-size': '11px',
        'font-weight': '700'
      }, timeStr));
    }

    // Draw reference traces (only if explicitly computed with genuine values)
    const drawTracePath = (traceData, strokeColor, strokeWidth, dashArray, valueGetter) => {
      let d = '', pen = false;
      let lastT = null;
      const sorted = [...traceData]
        .filter(r => Date.parse(r.timestamp_utc) >= minTimeCutoff)
        .sort((a, b) => Date.parse(a.timestamp_utc) - Date.parse(b.timestamp_utc));

      sorted.forEach(r => {
        const val = valueGetter(r);
        const t = Date.parse(r.timestamp_utc);
        if (!numeric(val) || !Number.isFinite(t)) { pen = false; return; }
        // Break line across missing telemetry gaps (> 45 minutes)
        if (lastT !== null && (t - lastT) > 45 * 60 * 1000) {
          pen = false;
        }
        lastT = t;
        const px = x(t), py = y(Number(val));
        d += `${pen ? 'L' : 'M'}${px.toFixed(1)},${py.toFixed(1)} `;
        pen = true;
      });
      // Only draw path line if multiple distinct observations exist
      if (d && sorted.filter(r => numeric(valueGetter(r))).length > 1) {
        const pathAttrs = {
          d,
          fill: 'none',
          stroke: strokeColor,
          'stroke-width': strokeWidth,
          'stroke-linejoin': 'round'
        };
        if (dashArray) pathAttrs['stroke-dasharray'] = dashArray;
        svg.appendChild(element('path', pathAttrs));
      }
    };

    if (tripletTraces && Array.isArray(tripletTraces.reference_model) && tripletTraces.reference_model.length > 0) {
      const hasComputedRef = tripletTraces.reference_model.some(r => numeric(r[paramKey] != null ? r[paramKey] : r[key]));
      if (hasComputedRef) {
        drawTracePath(tripletTraces.reference_model, '#6366F1', 2.0, '5 3', r => (r[paramKey] != null ? r[paramKey] : r[key]));
      }
    }

    if (tripletTraces && Array.isArray(tripletTraces.neighbor_consensus) && tripletTraces.neighbor_consensus.length > 0) {
      const hasComputedNeighbor = tripletTraces.neighbor_consensus.some(r => numeric(r[paramKey] != null ? r[paramKey] : r[key]));
      if (hasComputedNeighbor) {
        drawTracePath(tripletTraces.neighbor_consensus, '#F59E0B', 2.2, '2 3', r => (r[paramKey] != null ? r[paramKey] : r[key]));
      }
    }

    // Draw Observed In-Situ Primary Path
    let obsData = validRows;
    let obsGetter = r => r[key];
    if (tripletTraces && tripletTraces.observed && tripletTraces.observed.length) {
      obsData = tripletTraces.observed.filter(r => Date.parse(r.timestamp_utc) >= minTimeCutoff);
      obsGetter = r => (r[paramKey] != null ? r[paramKey] : r[key]);
    }

    let path = '', pen = false;
    let lastObsTime = null;
    const sortedObs = [...obsData].sort((a, b) => Date.parse(a.timestamp_utc) - Date.parse(b.timestamp_utc));
    
    // Tap-to-Inspect handler function
    const onPointInspect = (pointData, pointVal, pointTime, isFault, circleNode) => {
      const banner = document.getElementById('chart-inspect-banner');
      if (banner) {
        const timeUtcStr = new Date(pointTime).toISOString().replace('T', ' ').slice(0, 16) + ' UTC';
        const istStr = new Date(pointTime).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' }) + ' IST';
        
        banner.className = `chart-inspect-banner ${isFault ? 'anomaly-active' : 'inspected'}`;
        banner.innerHTML = `
          <div class="inspect-detail-row">
            <span class="inspect-pill-time">🕒 ${timeUtcStr} (${istStr})</span>
            <span class="inspect-pill-metric"><strong>${title}:</strong> ${Number(pointVal).toFixed(1)} ${unit}</span>
            <span class="inspect-pill-status ${isFault ? 'critical' : 'nominal'}">
              ${isFault ? '⚠️ SUSPECTED SENSOR ANOMALY' : '✓ Nominal Telemetry'}
            </span>
          </div>
        `;
      }

      // Highlight tapped circle
      svg.querySelectorAll('circle.tapped-highlight').forEach(c => c.classList.remove('tapped-highlight'));
      if (circleNode) {
        circleNode.classList.add('tapped-highlight');
      }
    };

    sortedObs.forEach(r => {
      const val = obsGetter(r);
      const t = Date.parse(r.timestamp_utc);
      if (!numeric(val) || !Number.isFinite(t)) { pen = false; return; }

      // Gap detection: break path line across gaps (> 45 min for a 15-min feed)
      if (lastObsTime !== null && (t - lastObsTime) > 45 * 60 * 1000) {
        pen = false;
      }
      lastObsTime = t;

      const px = x(t), py = y(Number(val));
      path += `${pen ? 'L' : 'M'}${px.toFixed(1)},${py.toFixed(1)} `;
      pen = true;

      // Anomaly marker vs standard dot
      const isFault = r.event_decision === 'sensor_fault' || (r.fault_probability && Number(r.fault_probability) > 0.8);
      const dot = element('circle', {
        cx: px.toFixed(1),
        cy: py.toFixed(1),
        r: isFault ? 6.5 : 4.5,
        fill: isFault ? '#DC2626' : color,
        stroke: '#FFFFFF',
        'stroke-width': isFault ? 2.5 : 1.5,
        class: isFault ? 'chart-anomaly-dot' : 'chart-obs-dot',
        style: 'cursor: pointer; -webkit-tap-highlight-color: transparent;',
        tabindex: 0
      });

      // Interactive Touch & Click Tap-to-Inspect
      const handleTrigger = (e) => {
        e.stopPropagation();
        onPointInspect(r, val, t, isFault, dot);
      };

      dot.addEventListener('click', handleTrigger);
      dot.addEventListener('touchstart', handleTrigger, { passive: true });

      const tooltipTime = new Date(t).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' });
      dot.appendChild(element('title', {}, `${tooltipTime} UTC: ${Number(val).toFixed(1)} ${unit}${isFault ? ' (ANOMALY DETECTED)' : ''}`));
      svg.appendChild(dot);
    });

    // Only draw continuous trend line if 2 or more distinct observations exist
    const validObsCount = sortedObs.filter(r => numeric(obsGetter(r))).length;
    if (path && validObsCount > 1) {
      svg.appendChild(element('path', {
        d: path,
        fill: 'none',
        stroke: color,
        'stroke-width': 2.8,
        'stroke-linejoin': 'round'
      }));
    }

    box.appendChild(svg);
    host.appendChild(box);
  }
};
