/* ==========================================================================
   SkyGuard AI · Sensor Trace Chart (Light Meteorological SVG Renderer)
   Supports 3-Trace Comparison:
   1. Observed In-Situ Telemetry (Solid Teal/Indigo/Amber)
   2. Independent Reference Model - Open-Meteo (Dashed Indigo)
   3. Spatial Neighbour Consensus - NOAA MADIS (Dotted Amber)
   Box Format for Each Term: Temperature, Pressure, Relative Humidity
   ========================================================================== */

window.renderSensorTrace = (rows, activeParameter = 'all', tripletTraces = null) => {
  const host = document.getElementById('sensor-chart');
  if (!host) return;

  const ns = 'http://www.w3.org/2000/svg';
  const element = (name, attrs, text) => {
    const node = document.createElementNS(ns, name);
    Object.entries(attrs || {}).forEach(([k, v]) => node.setAttribute(k, v));
    if (text != null) node.textContent = text;
    return node;
  };

  const signature = JSON.stringify([
    (rows || []).map(r => [r.station_id, r.timestamp_utc, r.temperature, r.pressure, r.humidity]),
    tripletTraces ? 'triplet' : 'standard'
  ]);
  const changed = host.dataset.signature !== signature;
  host.dataset.signature = signature;
  host.replaceChildren();

  const validRows = (rows || []).filter(r => Number.isFinite(Date.parse(r.timestamp_utc)));
  if (!validRows.length && !tripletTraces) {
    const empty = document.createElement('div');
    empty.style.cssText = 'padding: 40px 20px; text-align: center; color: #64748B; font-size: 13px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;';
    empty.textContent = 'No observations available for the selected station. Telemetry will appear as observations arrive.';
    host.appendChild(empty);
    return;
  }

  // Determine time extent
  let allTimes = validRows.map(r => Date.parse(r.timestamp_utc));
  if (tripletTraces && tripletTraces.reference_model) {
    tripletTraces.reference_model.forEach(r => {
      const t = Date.parse(r.timestamp_utc);
      if (Number.isFinite(t)) allTimes.push(t);
    });
  }
  if (!allTimes.length) allTimes = [Date.now() - 86400000, Date.now()];

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
          const v = r[paramKey] != null ? r[paramKey] : r[key];
          if (numeric(v)) values.push(Number(v));
        });
      });
    }

    const latestVal = values.length ? values[values.length - 1] : null;
    const minVal = values.length ? Math.min(...values) : null;
    const maxVal = values.length ? Math.max(...values) : null;
    const meanVal = values.length ? (values.reduce((a, b) => a + b, 0) / values.length) : null;

    // Outer Box Container for this parameter term
    const box = document.createElement('div');
    box.className = 'parameter-graph-box';
    box.id = `graph-box-${key}`;

    // Box Header
    const header = document.createElement('div');
    header.className = 'parameter-graph-header';
    header.innerHTML = `
      <div class="parameter-graph-title">
        <span style="font-size:16px;">${icon}</span>
        <span>${title}</span>
        <span class="stat-pill live">Latest: <strong>${latestVal != null ? latestVal.toFixed(1) : '—'} ${unit}</strong></span>
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
      emptyNote.textContent = `No ${title} telemetry reported for this station.`;
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

      // Horizontal faint gridline
      svg.appendChild(element('line', {
        x1: leftMargin + 1,
        x2: rightMargin,
        y1: py,
        y2: py,
        stroke: '#E2E8F0',
        'stroke-dasharray': '4 4',
        'stroke-width': 1
      }));

      // Broad Y-axis Tick mark
      svg.appendChild(element('line', {
        x1: leftMargin - 7,
        y1: py,
        x2: leftMargin,
        y2: py,
        stroke: '#475569',
        'stroke-width': 2
      }));

      // Bold Y-axis Tick label
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

    // Y-Axis Unit Title at top-left
    svg.appendChild(element('text', {
      x: leftMargin,
      y: yTop - 10,
      'text-anchor': 'start',
      fill: '#475569',
      'font-weight': '800',
      'font-size': '11px'
    }, `▲ ${unit}`));

    // X-Axis Title at bottom-right
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

      // X-axis Tick Mark
      svg.appendChild(element('line', {
        x1: px,
        y1: yBottom,
        x2: px,
        y2: yBottom + 6,
        stroke: '#475569',
        'stroke-width': 2
      }));

      // Vertical faint grid line
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

      // Time Text Label
      const timeStr = new Date(tVal).toISOString().slice(11, 16) + ' UTC';
      svg.appendChild(element('text', {
        x: px,
        y: yBottom + 18,
        'text-anchor': i === 0 ? 'start' : (i === numXSteps ? 'end' : 'middle'),
        fill: '#1E293B',
        'font-size': '11px',
        'font-weight': '700'
      }, timeStr));
    }

    // Helper to draw a polyline path
    const drawTracePath = (traceData, strokeColor, strokeWidth, dashArray, valueGetter) => {
      let d = '', pen = false;
      const sorted = [...traceData].sort((a, b) => Date.parse(a.timestamp_utc) - Date.parse(b.timestamp_utc));
      sorted.forEach(r => {
        const val = valueGetter(r);
        const t = Date.parse(r.timestamp_utc);
        if (!numeric(val) || !Number.isFinite(t)) { pen = false; return; }
        const px = x(t), py = y(Number(val));
        d += `${pen ? 'L' : 'M'}${px.toFixed(1)},${py.toFixed(1)} `;
        pen = true;
      });
      if (d) {
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

    // 1. Draw Reference Model Trace (Dashed Indigo) if available
    if (tripletTraces && tripletTraces.reference_model) {
      drawTracePath(
        tripletTraces.reference_model,
        '#6366F1',
        2.0,
        '5 3',
        r => (r[paramKey] != null ? r[paramKey] : r[key])
      );
    }

    // 2. Draw Spatial Consensus Trace (Dotted Amber) if available
    if (tripletTraces && tripletTraces.neighbor_consensus) {
      drawTracePath(
        tripletTraces.neighbor_consensus,
        '#F59E0B',
        2.2,
        '2 3',
        r => (r[paramKey] != null ? r[paramKey] : r[key])
      );
    }

    // 3. Draw Observed In-Situ Primary Path (Solid Line with Points)
    let obsData = validRows;
    let obsGetter = r => r[key];
    if (tripletTraces && tripletTraces.observed && tripletTraces.observed.length) {
      obsData = tripletTraces.observed;
      obsGetter = r => (r[paramKey] != null ? r[paramKey] : r[key]);
    }

    let path = '', pen = false;
    const sortedObs = [...obsData].sort((a, b) => Date.parse(a.timestamp_utc) - Date.parse(b.timestamp_utc));
    sortedObs.forEach(r => {
      const val = obsGetter(r);
      const t = Date.parse(r.timestamp_utc);
      if (!numeric(val) || !Number.isFinite(t)) { pen = false; return; }
      const px = x(t), py = y(Number(val));
      path += `${pen ? 'L' : 'M'}${px.toFixed(1)},${py.toFixed(1)} `;
      pen = true;

      // Point highlight & anomaly detection marker
      const isFault = r.event_decision === 'sensor_fault' || (r.fault_probability && Number(r.fault_probability) > 0.8);
      const dot = element('circle', {
        cx: px.toFixed(1),
        cy: py.toFixed(1),
        r: isFault ? 6 : 4,
        fill: isFault ? '#DC2626' : color,
        stroke: '#FFFFFF',
        'stroke-width': isFault ? 2.5 : 1.5,
        tabindex: 0
      });

      const tooltipTime = new Date(t).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' });
      dot.appendChild(element('title', {}, `${tooltipTime} UTC: ${Number(val).toFixed(1)} ${unit}${isFault ? ' (ANOMALY DETECTED)' : ''}`));
      svg.appendChild(dot);
    });

    if (path) {
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
