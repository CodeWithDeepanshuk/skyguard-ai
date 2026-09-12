/* ==========================================================================
   SkyGuard AI · Sensor Trace Chart (Light Meteorological SVG Renderer)
   Supports 3-Trace Comparison:
   1. Observed In-Situ Telemetry (Solid Teal/Red)
   2. Independent Reference Model - Open-Meteo (Dashed Indigo)
   3. Spatial Neighbour Consensus (Dotted Amber)
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
    empty.style.cssText = 'padding: 40px 20px; text-align: center; color: #64748B; font-size: 13px;';
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
  const x = time => 75 + (end === start ? 0.5 : (time - start) / (end - start)) * 780;

  const seriesDefs = [
    ['temperature', 'Temperature', '°C', '#0D9488', '#CCFBF1', 'temperature_c'],
    ['pressure', 'Atmospheric Pressure', 'hPa', '#2563EB', '#DBEAFE', 'pressure_hpa'],
    ['humidity', 'Relative Humidity', '% RH', '#0284C7', '#E0F2FE', 'relative_humidity_pct']
  ];

  const seriesToRender = activeParameter === 'all' 
    ? seriesDefs 
    : seriesDefs.filter(([key]) => key === activeParameter);

  for (const [key, title, unit, color, lightColor, paramKey] of seriesToRender) {
    const svg = element('svg', {
      viewBox: '0 0 900 150',
      role: 'img',
      'aria-label': `${title} in ${unit}`,
      class: changed ? 'trace-series updated' : 'trace-series',
      style: 'margin-bottom: 14px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;'
    });

    // Parameter Title & Legend
    svg.appendChild(element('text', {
      x: 18,
      y: 22,
      fill: color,
      'font-weight': '700',
      'font-size': '12px'
    }, `${title} (${unit})`));

    // 3-Trace Legend on the SVG header
    if (tripletTraces) {
      svg.appendChild(element('line', { x1: 420, y1: 18, x2: 445, y2: 18, stroke: color, 'stroke-width': 2.5 }));
      svg.appendChild(element('text', { x: 450, y: 22, fill: '#334155', 'font-size': '10px', 'font-weight': '600' }, 'Observed In-Situ'));

      svg.appendChild(element('line', { x1: 570, y1: 18, x2: 595, y2: 18, stroke: '#6366F1', 'stroke-width': 2, 'stroke-dasharray': '5 3' }));
      svg.appendChild(element('text', { x: 600, y: 22, fill: '#334155', 'font-size': '10px', 'font-weight': '600' }, 'Reference Model (Open-Meteo)'));

      svg.appendChild(element('line', { x1: 760, y1: 18, x2: 785, y2: 18, stroke: '#F59E0B', 'stroke-width': 2, 'stroke-dasharray': '2 3' }));
      svg.appendChild(element('text', { x: 790, y: 22, fill: '#334155', 'font-size': '10px', 'font-weight': '600' }, 'Spatial Consensus'));
    }

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

    if (!values.length) {
      svg.appendChild(element('text', { x: 380, y: 80, fill: '#94A3B8', 'font-size': '12px' }, 'No telemetry reported for parameter'));
      host.appendChild(svg);
      continue;
    }

    let low = Math.min(...values), high = Math.max(...values);
    const padding = Math.max((high - low) * 0.15, key === 'pressure' ? 1.0 : 0.5);
    low -= padding;
    high += padding;

    const y = value => 112 - (value - low) / (high - low) * 80;

    // Grid lines & Y-axis labels
    for (let i = 0; i < 3; i++) {
      const value = low + (high - low) * i / 2;
      const py = y(value);
      svg.appendChild(element('line', {
        x1: 75,
        x2: 875,
        y1: py,
        y2: py,
        stroke: '#F1F5F9',
        'stroke-dasharray': '3 3'
      }));
      svg.appendChild(element('text', {
        x: 68,
        y: py + 4,
        'text-anchor': 'end',
        fill: '#64748B',
        'font-size': '10px',
        'font-weight': '500'
      }, value.toFixed(1)));
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
        1.8,
        '5 3',
        r => (r[paramKey] != null ? r[paramKey] : r[key])
      );
    }

    // 2. Draw Spatial Consensus Trace (Dotted Amber) if available
    if (tripletTraces && tripletTraces.neighbor_consensus) {
      drawTracePath(
        tripletTraces.neighbor_consensus,
        '#F59E0B',
        2.0,
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
        r: isFault ? 5 : 3.5,
        fill: isFault ? '#DC2626' : color,
        stroke: isFault ? '#FFFFFF' : '#FFFFFF',
        'stroke-width': 1.5,
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
        'stroke-width': 2.5,
        'stroke-linejoin': 'round'
      }));
    }

    // Time labels on X axis
    for (const [time, anchor, offset] of [[start, 'start', 75], [end, 'end', 875]]) {
      const timeStr = new Date(time).toISOString().slice(5, 16).replace('T', ' ') + ' UTC';
      svg.appendChild(element('text', {
        x: offset,
        y: 138,
        'text-anchor': anchor,
        fill: '#94A3B8',
        'font-size': '10px'
      }, timeStr));
    }

    host.appendChild(svg);
  }
};
