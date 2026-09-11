window.renderSensorTrace = (rows) => {
  const host = document.getElementById('sensor-chart');
  const ns = 'http://www.w3.org/2000/svg';
  const element = (name, attrs, text) => {
    const node = document.createElementNS(ns, name);
    Object.entries(attrs || {}).forEach(([k,v]) => node.setAttribute(k,v));
    if (text != null) node.textContent = text;
    return node;
  };
  const signature = JSON.stringify(rows.map(r => [r.station_id,r.timestamp_utc,r.temperature,r.pressure,r.humidity]));
  const changed = host.dataset.signature !== signature;
  host.dataset.signature = signature;
  host.replaceChildren();
  const validRows = rows.filter(r => Number.isFinite(Date.parse(r.timestamp_utc)));
  if (!validRows.length) {
    const empty = document.createElement('p'); empty.className = 'empty-state';
    empty.textContent = 'No observations for the selected station in this feed. Select another station or refresh.';
    host.appendChild(empty); return;
  }
  const times = validRows.map(r => Date.parse(r.timestamp_utc));
  const start = Math.min(...times), end = Math.max(...times);
  const x = time => 85 + (end === start ? .5 : (time-start)/(end-start))*760;
  for (const [key, title, unit, color] of [['temperature','Temperature','°C','#ff8a78'],['pressure','Pressure','hPa','#81b8ff'],['humidity','Humidity','% RH','#44e0cc']]) {
    const svg = element('svg', {viewBox:'0 0 900 150', role:'img', 'aria-label':`${title} in ${unit}`, class:changed ? 'trace-series updated' : 'trace-series'});
    svg.appendChild(element('text',{x:15,y:19,fill:color},`${title} · ${unit}`));
    const numeric = value => value !== '' && value != null && Number.isFinite(Number(value));
    const values = validRows.filter(r => numeric(r[key])).map(r => Number(r[key]));
    if (!values.length) { svg.appendChild(element('text',{x:350,y:80,fill:'#b5c8d4'},'No reported values')); host.appendChild(svg); continue; }
    let low = Math.min(...values), high = Math.max(...values);
    const padding = Math.max((high-low)*.12, key === 'pressure' ? .5 : .2);
    low -= padding; high += padding;
    const y = value => 110-(value-low)/(high-low)*75;
    for(let i=0;i<3;i++) {
      const value = low+(high-low)*i/2, py=y(value);
      svg.appendChild(element('line',{x1:85,x2:845,y1:py,y2:py,stroke:'#284250','stroke-dasharray':'3 5'}));
      svg.appendChild(element('text',{x:76,y:py+4,'text-anchor':'end',fill:'#a7bdca'},value.toFixed(1)));
    }
    let path='', pen=false;
    validRows.forEach(r => {
      if (!numeric(r[key])) {pen=false;return;}
      const px=x(Date.parse(r.timestamp_utc)), py=y(Number(r[key]));
      path += `${pen ? 'L' : 'M'}${px},${py} `; pen=true;
      const dot=element('circle',{cx:px,cy:py,r:3,fill:color,tabindex:0});
      dot.appendChild(element('title',{},`${r.timestamp_utc}: ${Number(r[key]).toFixed(1)} ${unit}`));
      svg.appendChild(dot);
    });
    svg.appendChild(element('path',{d:path,fill:'none',stroke:color,'stroke-width':2,'stroke-linejoin':'round'}));
    for(const [time,anchor] of [[start,'start'],[end,'end']]) {
      svg.appendChild(element('text',{x:x(time),y:139,'text-anchor':anchor,fill:'#a7bdca'},new Date(time).toISOString().slice(5,16).replace('T',' ')+' UTC'));
    }
    host.appendChild(svg);
  }
};
