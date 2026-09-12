/* ==========================================================================
   SkyGuard AI · Sensor Trace Chart (Light Meteorological SVG Renderer)
   ========================================================================== */

window.renderSensorTrace = (rows, activeParameter = 'all') => {
  const host = document.getElementById('sensor-chart');
  if (!host) return;

  const ns = 'http://www.w3.org/2000/svg';
  const element = (name, attrs, text) => {
    const node = document.createElementNS(ns, name);
    Object.entries(attrs || {}).forEach(([k, v]) => node.setAttribute(k, v));
    if (text != null) node.textContent = text;
    return node;
  };

  const signature = JSON.stringify(rows.map(r => [r.station_id, r.timestamp_utc, r.temperature, r.pressure, r.humidity]));
  const changed = host.dataset.signature !== signature;
  host.dataset.signature = signature;
  host.replaceChildren();

  const validRows = (rows || []).filter(r => Number.isFinite(Date.parse(r.timestamp_utc)));
  if (!validRows.length) {
    const empty = document.createElement('div');
    empty.style.cssText = 'padding: 40px 20px; text-align: center; color: #64748B; font-size: 13px;';
    empty.textContent = 'No observations available for the selected station. Telemetry will appear as observations arrive.';
    host.appendChild(empty);
    return;
  }

  const times = validRows.map(r => Date.parse(r.timestamp_utc));
  const start = Math.min(...times), end = Math.max(...times);
  const x = time => 75 + (end === start ? 0.5 : (time - start) / (end - start)) * 780;

  const seriesDefs = [
    ['temperature', 'Temperature', '°C', '#DC2626', '#FEE2E2'],
    ['pressure', 'Pressure', 'hPa', '#2563EB', '#DBEAFE'],
    ['humidity', 'Relative Humidity', '% RH', '#0EA5E9', '#E0F2FE']
  ];

  const seriesToRender = activeParameter === 'all' 
    ? seriesDefs 
    : seriesDefs.filter(([key]) => key === activeParameter);

  for (const [key, title, unit, color, lightColor] of seriesToRender) {
    const svg = element('svg', {
      viewBox: '0 0 900 140',
      role: 'img',
      'aria-label': `${title} in ${unit}`,
      class: changed ? 'trace-series updated' : 'trace-series',
      style: 'margin-bottom: 12px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;'
    });

    // Parameter Title & Unit
    svg.appendChild(element('text', {
      x: 18,
      y: 22,
      fill: color,
      'font-weight': '700',
      'font-size': '12px'
    }, `${title} (${unit})`));

    const numeric = value => value !== '' && value != null && Number.isFinite(Number(value));
    const values = validRows.filter(r => numeric(r[key])).map(r => Number(r[key]));

    if (!values.length) {
      svg.appendChild(element('text', { x: 380, y: 75, fill: '#94A3B8', 'font-size': '12px' }, 'No reported values'));
      host.appendChild(svg);
      continue;
    }

    let low = Math.min(...values), high = Math.max(...values);
    const padding = Math.max((high - low) * 0.15, key === 'pressure' ? 0.8 : 0.4);
    low -= padding;
    high += padding;

    const y = value => 105 - (value - low) / (high - low) * 75;

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

    // Path points
    let path = '', pen = false;
    validRows.forEach(r => {
      if (!numeric(r[key])) { pen = false; return; }
      const px = x(Date.parse(r.timestamp_utc)), py = y(Number(r[key]));
      path += `${pen ? 'L' : 'M'}${px.toFixed(1)},${py.toFixed(1)} `;
      pen = true;

      // Anomaly detection marker highlight
      const isFault = r.event_decision === 'sensor_fault' || (r.fault_probability && Number(r.fault_probability) > 0.8);
      const dot = element('circle', {
        cx: px.toFixed(1),
        cy: py.toFixed(1),
        r: isFault ? 5 : 3,
        fill: isFault ? '#DC2626' : color,
        stroke: isFault ? '#FFFFFF' : 'none',
        'stroke-width': isFault ? 2 : 0,
        tabindex: 0
      });

      const tooltipTime = new Date(r.timestamp_utc).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' });
      dot.appendChild(element('title', {}, `${tooltipTime} UTC: ${Number(r[key]).toFixed(1)} ${unit}${isFault ? ' (ANOMALY DETECTED)' : ''}`));
      svg.appendChild(dot);
    });

    svg.appendChild(element('path', {
      d: path,
      fill: 'none',
      stroke: color,
      'stroke-width': 2,
      'stroke-linejoin': 'round'
    }));

    // Time labels on X axis
    for (const [time, anchor, offset] of [[start, 'start', 75], [end, 'end', 875]]) {
      const timeStr = new Date(time).toISOString().slice(5, 16).replace('T', ' ') + ' UTC';
      svg.appendChild(element('text', {
        x: offset,
        y: 130,
        'text-anchor': anchor,
        fill: '#94A3B8',
        'font-size': '10px'
      }, timeStr));
    }

    host.appendChild(svg);
  }
};
