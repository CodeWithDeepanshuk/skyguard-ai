"use strict";

const state = {
  summary: null,
  stations: [],
  networkFilter: "all",
  zoneFilter: "all",
  searchQuery: "",
  health: [],
  incidents: [],
  readings: [],
  alerts: [],
  selectedStation: null,
  selectedSplit: "time_test",
  healthFilter: "all",
  lastThroughput: null,
  mode: "live",
  liveStatus: null,
  liveTimer: null,
  freshnessTimer: null,
  viewRevision: 0,
  busyDepth: 0,
  replayStatus: null,
};

const scenarioCopy = {
  pressure_drift: "A single pressure sensor slowly separates from neighbouring stations. The model should identify a probable calibration drift.",
  regional_weather: "Several nearby stations warm together. Neighbour agreement should preserve this as probable genuine weather, not a sensor fault.",
  dropout: "One station stops transmitting. The packaged simulator supplies a verified heartbeat SLA, so the resumed packet can create an automatic communication-gap alert. Unknown-cadence sources produce an advisory instead.",
  packet_errors: "Repeated transport identity and a backward timestamp demonstrate duplicate-packet and timestamp-order checks.",
};

const sensorLabel = { temperature: "Temperature", pressure: "Pressure", humidity: "Humidity" };
const sensorUnit = { temperature: "°C", pressure: "hPa", humidity: "% RH" };
const $ = (id) => document.getElementById(id);

function number(value, digits = 0) {
  if (value === null || value === undefined || String(value).trim() === "" || !Number.isFinite(Number(value))) return "—";
  return Number(value).toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function percent(value, digits = 1) {
  if (value === null || value === undefined || String(value).trim() === "" || !Number.isFinite(Number(value))) return "—";
  return `${number(Number(value) * 100, digits)}%`;
}

function esc(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}

function pretty(value) {
  return String(value || "unknown").replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatTime(value) {
  if (!value) return "—";
  return String(value).replace("T", " ").replace("Z", "").slice(0, 16);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

function toast(message, error = false) {
  const element = $("toast");
  element.textContent = message;
  element.className = `toast show${error ? " error" : ""}`;
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => { element.className = "toast"; }, 3000);
}

function setBusy(busy) {
  state.busyDepth = Math.max(0, state.busyDepth + (busy ? 1 : -1));
  const processing = state.busyDepth > 0;
  ["load-scenario", "step-scenario", "run-scenario", "reset-scenario", "refresh-live", "trace-refresh", "inject-live-fault", "clear-live-faults"].forEach((id) => { $(id).disabled = processing; });
  document.querySelectorAll("#mode-selector button").forEach(button => { button.disabled = processing; });
  if (processing) {
    $("replay-state").textContent = "Processing";
    $("replay-state").className = "status-pill";
  } else if (state.mode === "live") renderLiveStatus(state.liveStatus || {});
  else renderReplay(state.replayStatus || {});
}

function stationName(id) {
  return state.stations.find((station) => station.station_id === id)?.station_name || id;
}

function parseReading(row) {
  try { return { ...row, ...JSON.parse(row.payload_json || "{}") }; }
  catch { return row; }
}

async function replayAction(action) {
  setBusy(true);
  try {
    const result = await action();
    if (result?.throughput_rows_per_second) state.lastThroughput = result.throughput_rows_per_second;
    await refreshLiveData();
  } catch (error) {
    toast(`Replay action failed: ${error.message}`, true);
  } finally {
    setBusy(false);
  }
}

async function loadScenario(preview = true) {
  const name = $("scenario-select").value;
  await replayAction(async () => {
    await api(`/api/replay/load/${encodeURIComponent(name)}`, { method: "POST" });
    const result = preview ? await api("/api/replay/step?count=220", { method: "POST" }) : null;
    toast(`${pretty(name)} loaded${preview ? " with visible preview data" : ""}.`);
    return result;
  });
}

async function refreshLiveData() {
  const revision = state.viewRevision;
  const [status, readings, alerts] = await Promise.all([
    api("/api/replay/status"),
    api("/api/readings?limit=5000"),
    api("/api/alerts?limit=500"),
  ]);
  if (state.mode !== "replay" || revision !== state.viewRevision) return;
  state.replayStatus = status;
  state.readings = readings.map(parseReading);
  state.alerts = alerts;
  if (!state.selectedStation) {
    state.selectedStation = state.readings[0]?.station_id || state.stations[0]?.station_id || null;
  }
  renderReplay(status);
  renderNetwork();
  renderReadings();
  renderAlertQueue();
  renderKpis();
}

async function refreshOfficialLive(force = true) {
  if (state.liveFetching || state.mode !== "live") return;
  const revision = state.viewRevision;
  state.liveFetching = true;
  setBusy(true);
  try {
    const status = force ? await api("/api/live/refresh?hours=24", { method: "POST" }) : await api("/api/live/status");
    const [readings, alerts, liveIncidents] = await Promise.all([
      api("/api/live/readings?limit=5000"),
      api("/api/live/alerts?limit=500"),
      api("/api/live/incidents"),
    ]);
    if (state.mode !== "live" || revision !== state.viewRevision) return;
    state.liveStatus = status;
    state.readings = readings.map(parseReading);
    state.alerts = alerts;
    state.incidents = liveIncidents || [];
    if (!state.selectedStation) {
      state.selectedStation = state.readings[0]?.station_id || null;
    }
    renderLiveStatus(status);
    renderNetwork(); renderReadings(); renderAlertQueue(); renderKpis();
    toast(status.simulation_active ? "Simulation view updated; these modified values are not genuine live observations." : status.is_cached ? "Showing a cached snapshot; check observation age." : "Observation snapshot updated; check each station's timestamp.", Boolean(status.error));
  } catch (error) {
    if (state.mode !== "live" || revision !== state.viewRevision) return;
    state.liveStatus = { ...state.liveStatus, is_cached: true, error: error.message };
    renderLiveStatus(state.liveStatus);
    renderNetwork();
    toast(`Live refresh failed: ${error.message}. Offline replay remains available.`, true);
  } finally {
    state.liveFetching = false;
    setBusy(false);
  }
}

function observationAgeMinutes(value, now = Date.now()) {
  if (!value || !/(Z|[+-]\d{2}:\d{2})$/i.test(String(value))) return null;
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? (now - timestamp) / 60000 : null;
}

function ageLabel(value) {
  const age = observationAgeMinutes(value);
  if (age === null) return "Age unavailable";
  return age < 0 ? "Future timestamp · check clock" : `${number(Math.floor(age))} min old`;
}

function renderLiveStatus(status) {
  $('hero-live-count').textContent = number(status.observation_count);
  $('hero-live-stations').textContent = number(status.reporting_stations);
  $('hero-live-time').textContent = `${status.is_cached ? 'Cached' : 'Fetched'} ${formatTime(status.fetched_at_utc)} UTC`;
  $("live-stations").textContent = `${number(status.reporting_stations)}/${number(status.configured_icao_stations)}`;
  $("live-observations").textContent = number(status.observation_count);
  $("live-age").textContent = ageLabel(status.latest_observation_utc);
  $("live-age").title = "Age of the newest network report only. Other stations may be older.";
  $("live-interpretation").textContent = status.interpretation || "Official observations with cached offline fallback.";
  $("progress-bar").style.width = status.observation_count ? "100%" : "0%";
  $("replay-position").textContent = `${number(status.observation_count)} ${status.simulation_active ? 'simulation' : 'source'} observations`;
  $("replay-throughput").textContent = `${status.is_cached ? "Cached" : "Fetched"} ${formatTime(status.fetched_at_utc)} UTC · ${ageLabel(status.fetched_at_utc)}`;
  const label = status.simulation_active ? "Simulation" : status.error ? "Source unavailable" : status.is_cached ? "Cached" : status.observation_count ? "Fetched" : "No reports";
  $("replay-state").textContent = state.busyDepth ? "Processing" : label;
  $("replay-state").className = "status-pill";
  const badge = $("injection-status-badge");
  badge.textContent = status.simulation_active === true ? "SIMULATION: modified observations; not real sensor faults. Model detection is not guaranteed."
    : status.simulation_active === false ? "No simulation overlay. Sensor health is not certified by absence of an alert."
    : "Snapshot simulation provenance unverified; fetch fresh source reports before presenting as live evidence.";
  badge.className = `injection-status-badge${status.simulation_active ? ' alert-active' : ''}`;
}

async function switchMode(mode) {
  if (mode === state.mode) return;
  state.mode = mode;
  state.viewRevision += 1;
  const revision = state.viewRevision;
  state.readings = []; state.alerts = []; state.incidents = [];
  renderNetwork(); renderReadings(); renderAlertQueue();
  document.body.dataset.mode = mode;
  document.querySelectorAll("#mode-selector button").forEach((button) => button.classList.toggle("active", button.dataset.mode === mode));
  $("replay-controls").classList.toggle("hidden", mode === "live");
  $("live-controls").classList.toggle("hidden", mode !== "live");
  $("replay-title").textContent = mode === "live" ? "Live observation feed" : "Scenario replay";
  $("kpi-readings-note").textContent = mode === "live" ? "Official observation cache" : "Replay database";
  $("kpi-faults-note").textContent = mode === "live" ? "Current live window" : "Current replay window";
  $("observations-subtitle").textContent = mode === "live"
    ? "Genuine METAR values scored by the compliant three-parameter model"
    : "Reported values and model decision from the active scenario";
  window.clearInterval(state.liveTimer);
  state.liveTimer = null;
  if (mode === "live") { await refreshOfficialLive(true); scheduleLiveRefresh(); }
  else {
    const incidents = await api('/api/incidents?limit=500');
    if (revision !== state.viewRevision) return;
    state.incidents = incidents;
    await loadScenario(true);
  }
}

function renderReplay(status) {
  const progress = status.total_rows ? status.position / status.total_rows : 0;
  $("progress-bar").style.width = `${Math.min(100, progress * 100)}%`;
  $("replay-position").textContent = `${number(status.position)} / ${number(status.total_rows)} source packets`;
  $("replay-throughput").textContent = state.lastThroughput ? `${number(state.lastThroughput)} rows/sec` : (status.finished ? "Replay complete" : "Preview ready");
  $("replay-state").textContent = status.finished ? "Complete" : "Ready";
}

function healthByStation() {
  const result = {};
  if (state.mode === 'live') {
    for (const station of state.stations) {
      const latest = state.readings.filter(row => row.station_id === station.station_id)
        .sort((a, b) => String(b.timestamp_utc).localeCompare(String(a.timestamp_utc)))[0];
      const review = latest && (latest.event_decision === 'sensor_fault' || state.alerts.some(a => a.station_id === station.station_id && a.timestamp_utc === latest.timestamp_utc));
      result[station.station_id] = {score: null, status: review ? 'monitor' : 'unknown',
        label: review ? 'Review signal' : 'Health unverified', timestamp: latest?.timestamp_utc,
        detail: stationSupport(station, state.stations, state.readings).text};
    }
    return result;
  }
  for (const row of state.health) {
    const score = Number(row.health_score);
    if (!result[row.station_id] || score < result[row.station_id].score) result[row.station_id] = { score, status: row.status, sensor: row.sensor };
  }
  return result;
}

function renderNetwork() {
  const health = healthByStation();
  SkyGuardMap.reset();

  const netFilter = state.networkFilter || "all";
  const zFilter = state.zoneFilter || "all";
  const query = (state.searchQuery || "").trim().toLowerCase();

  const filteredStations = (state.stations || []).filter((st) => {
    if (netFilter === "benchmark") {
      const isBench = st.is_benchmark == 1 || st.evaluation_role === "development" || st.evaluation_role === "station_holdout";
      if (!isBench) return false;
    } else if (netFilter === "active") {
      if (String(st.is_active_2024_plus) !== "1") return false;
    }
    if (zFilter !== "all" && (st.climate_zone || "").toLowerCase() !== zFilter.toLowerCase()) {
      return false;
    }
    if (query) {
      const match = (st.station_name || "").toLowerCase().includes(query) ||
                    (st.station_id || "").toLowerCase().includes(query) ||
                    (st.icao || "").toLowerCase().includes(query) ||
                    (st.climate_zone || "").toLowerCase().includes(query);
      if (!match) return false;
    }
    return true;
  });

  const badge = $("station-count-badge");
  if (badge) {
    badge.textContent = `${filteredStations.length} of ${state.stations.length} Indian stations`;
  }

  const maxCards = 100;
  let cardCount = 0;
  for (const station of filteredStations) {
    const record = health[station.station_id] || { score: null, status: "unknown" };
    const shouldRenderCard = cardCount < maxCards || station.station_id === state.selectedStation;
    if (shouldRenderCard) cardCount++;
    SkyGuardMap.add(station, record, station.station_id === state.selectedStation, () => {
      state.selectedStation = station.station_id;
      renderNetwork();
      renderReadings();
    }, { renderCard: shouldRenderCard });
  }
  SkyGuardMap.finish();

  const station = state.stations.find((item) => item.station_id === state.selectedStation);
  const stationHealth = health[state.selectedStation];
  if (station) {
    const zoneInfo = station.climate_zone ? ` · ${esc(station.climate_zone)}` : '';
    const elevInfo = station.elevation_m ? ` · ${Math.round(station.elevation_m)}m ASL` : '';
    $("selected-station").innerHTML = `<b>${esc(station.station_name)}</b> · ${esc(station.icao || station.station_id)}${zoneInfo}${elevInfo} · ${number(station.latitude, 4)}°N, ${number(station.longitude, 4)}°E · ${esc(stationHealth?.label || pretty(stationHealth?.status))}${stationHealth?.score != null ? ` · Historical health ${number(stationHealth.score, 1)}/100` : ' · Score unavailable'}`;
  }
  const selectedRows = state.readings.filter((row) => row.station_id === state.selectedStation)
    .sort((a,b) => Date.parse(a.timestamp_utc) - Date.parse(b.timestamp_utc)).slice(-80);
  renderCurrentValues(selectedRows.at(-1));
  drawSensorChart(selectedRows);
  $("chart-city").value = state.selectedStation || '';
  $("chart-subtitle").textContent = station ? `${station.station_name} · ${selectedRows.length} observations · ${state.mode === 'live' ? 'METAR' : 'Offline replay'}` : 'Select a station';
  renderTraceFreshness();
  renderSelectedIncident();
}

function renderTraceFreshness() {
  const latest = state.readings.filter(row => row.station_id === state.selectedStation)
    .sort((a, b) => Date.parse(b.timestamp_utc) - Date.parse(a.timestamp_utc))[0];
  $("trace-status").textContent = state.mode !== 'live' ? 'OFFLINE REPLAY' : !latest ? 'NO STATION REPORT' : state.liveStatus?.simulation_active ? 'SIMULATION · MODIFIED DATA' : state.liveStatus?.is_cached ? 'CACHED SNAPSHOT' : 'PERIODIC REPORTS · CHECK AGE';
  $("trace-time").textContent = latest ? `Observed ${formatTime(latest.timestamp_utc)} UTC${state.mode === 'live' ? ` · ${ageLabel(latest.timestamp_utc)} · Fetched ${formatTime(state.liveStatus?.fetched_at_utc)} UTC` : ' · Historical scenario time'}` : 'No observations for this selected station. Another city will not be substituted.';
}

function renderSelectedIncident() {
  // Every entry point (map, selector, alert, refresh) uses the same station-only lookup.
  const match = state.incidents.filter(inc => inc.station_id === state.selectedStation && inc.incident_id !== 'SYS-LIVE-CLEAN')
    .sort((a, b) => String(b.timestamp_utc || b.last_timestamp_utc || '').localeCompare(String(a.timestamp_utc || a.last_timestamp_utc || '')))[0];
  if (match) { renderIncident(match); return; }
  renderIncident({
    station_id: state.selectedStation, severity: 'unknown', root_cause: 'no_evidence_record',
    fault_probability: null, root_cause_confidence: null,
    explanation: `${stationName(state.selectedStation) || 'Selected station'}: no ${state.mode === 'live' ? 'live advisory' : 'historical benchmark'} incident record is available. This does not establish sensor health.`,
    recommended_action: 'Check station timestamps, missing reports and available evidence. No automatic repair is claimed.',
  });
}

function renderCurrentValues(row) {
  $("current-temp").textContent = row ? number(row.temperature, 1) : "—";
  $("current-pressure").textContent = row ? number(row.pressure, 1) : "—";
  $("current-humidity").textContent = row ? number(row.humidity, 1) : "—";
  $("current-probability").textContent = row ? percent(row.fault_probability, 1) : "—";
  $("current-decision").textContent = row ? pretty(row.event_decision) : "No reading";
}

function drawSensorChart(rows) {
  window.renderSensorTrace(rows);
}

function renderReadings() {
  let rows = state.readings;
  if (state.mode === "live") {
    const seen = new Set();
    const latestRows = [];
    const olderRows = [];
    for (const r of rows) {
      if (!seen.has(r.station_id)) {
        seen.add(r.station_id);
        latestRows.push(r);
      } else {
        olderRows.push(r);
      }
    }
    latestRows.sort((a, b) => {
      if (a.event_decision === "sensor_fault" && b.event_decision !== "sensor_fault") return -1;
      if (b.event_decision === "sensor_fault" && a.event_decision !== "sensor_fault") return 1;
      return (stationName(a.station_id)).localeCompare(stationName(b.station_id));
    });
    rows = [...latestRows, ...olderRows];
  }
  const displayRows = rows.slice(0, 18);
  $("reading-count").textContent = `${number(state.readings.length)} ${state.mode === "live" ? (state.liveStatus?.simulation_active ? "simulation rows" : "source snapshot rows") : "replay rows"}`;
  $("readings-body").innerHTML = displayRows.length ? displayRows.map((row) => `<tr>
    <td>${esc(formatTime(row.timestamp_utc))}</td><td>${esc(stationName(row.station_id))}</td>
    <td>${number(row.temperature, 1)} °C</td><td>${number(row.pressure, 1)} hPa</td><td>${number(row.humidity, 1)}%</td>
    <td>${percent(row.fault_probability, 1)}</td><td><span class="decision ${esc(row.event_decision)}">${esc(pretty(row.event_decision))}</span></td>
    <td>${esc(pretty(row.root_cause || row.root_cause_prediction || "not_a_fault"))}</td></tr>`).join("") : `<tr><td colspan="8" class="empty-state">${state.mode === 'live' ? 'No source observations available. Check the feed status or use offline replay.' : 'No replay readings yet. Load a scenario preview.'}</td></tr>`;
}

function renderAlertQueue() {
  let combined = [];
  if (state.mode === "live") {
    combined = (state.alerts || []).map((row) => ({
      ...row,
      kind: row.source?.includes("quality") ? "transport" : "model",
    }));
  } else {
    const modelAlerts = state.readings.filter((row) => row.event_decision === "sensor_fault").map((row) => ({
      kind: "model", station_id: row.station_id, timestamp_utc: row.timestamp_utc,
      alert_type: row.root_cause || row.root_cause_prediction || "sensor_fault", explanation: `${percent(row.fault_probability, 1)} fault probability`,
    }));
    combined = [...state.alerts.map((row) => ({ ...row, kind: row.source?.includes("quality") ? "transport" : "model" })), ...modelAlerts].slice(0, 30);
  }
  $("queue-count").textContent = `${combined.length} in snapshot`;
  $("alert-list").innerHTML = combined.length ? combined.map((alert, index) => `<button class="alert-item ${alert.kind === "transport" ? "transport" : ""}" data-alert-index="${index}">
    <i class="alert-mark"></i><span><b>${esc(pretty(alert.alert_type))}</b><span>${esc(stationName(alert.station_id))}</span><small>${esc(formatTime(alert.timestamp_utc))}</small></span><em>${esc(alert.explanation || "Inspect")}</em></button>`).join("") : `<div class="empty-state">No alerts in this ${state.mode === "live" ? "source snapshot" : "replay window"}. Sensor health remains unverified; check report freshness and coverage.</div>`;
  document.querySelectorAll("[data-alert-index]").forEach((button) => button.addEventListener("click", () => {
    const alert = combined[Number(button.dataset.alertIndex)];
    if (alert.station_id) {
      state.selectedStation = alert.station_id;
      renderNetwork();
      renderReadings();
    }
  }));
}

function renderIncident(incident) {
  $("incident-title").textContent = `${pretty(incident.root_cause)} · ${stationName(incident.station_id)}`;
  $("incident-severity").textContent = incident.severity;
  $("incident-severity").className = `severity ${incident.severity}`;
  $("incident-explanation").textContent = incident.explanation;
  $("incident-record-time").textContent = `${state.mode === 'live' ? (incident.simulation ? 'Simulation advisory' : 'Live-source advisory') : 'Historical benchmark evidence'} · Record ${formatTime(incident.timestamp_utc || incident.last_timestamp_utc || incident.start_utc)} UTC`;
  $("fault-confidence").textContent = percent(incident.fault_probability, 1);
  $("root-confidence").textContent = percent(incident.root_cause_confidence, 1);
  $("affected-sensor").textContent = (incident.affected_sensors || []).map(pretty).join(", ") || "Unknown";
  $("evidence-list").innerHTML = (incident.evidence || []).map((item) => `<div class="bar-row"><span>${esc(pretty(`${item.sensor} ${item.signal}`))}</span><b>${number(item.score, 3)}</b><div class="bar"><i style="width:${Math.min(100, Math.abs(Number(item.score)) * 100)}%"></i></div></div>`).join("") || `<div class="empty-state">No rule evidence recorded.</div>`;
  const contributions = incident.model_feature_contributions || [];
  const maxContribution = Math.max(1, ...contributions.map((item) => Math.abs(Number(item.contribution))));
  $("contribution-list").innerHTML = contributions.map((item) => `<div class="bar-row"><span>${esc(pretty(item.feature))}</span><b>${number(item.contribution, 3)}</b><div class="bar"><i class="${Number(item.contribution) < 0 ? "negative" : ""}" style="width:${Math.abs(Number(item.contribution)) / maxContribution * 100}%"></i></div></div>`).join("") || `<div class="empty-state">No local contributions recorded.</div>`;
  const corrections = incident.corrections || [];
  $("correction-box").innerHTML = corrections.length ? corrections.map((item) => `<div class="correction-cell"><span>${esc(sensorLabel[item.sensor] || pretty(item.sensor))}</span><b>${number(item.reported_value, 2)} → ${number(item.estimate, 2)} ${esc(sensorUnit[item.sensor] || "")}</b><small>90% interval ${number(item.interval_lower, 2)}–${number(item.interval_upper, 2)} · ${esc(pretty(item.method))}</small></div>`).join("") : `<div class="correction-cell"><span>Correction</span><b>No safe estimate</b><small>Observation remains unchanged and requires review.</small></div>`;
  $("maintenance-action").textContent = incident.recommended_action;
}

function renderKpis() {
  const modelFaults = state.readings.filter((row) => row.event_decision === "sensor_fault").length;
  const healthy = state.health.filter((row) => row.status === "healthy").length;
  $("kpi-readings").textContent = number(state.readings.length);
  $("kpi-faults").textContent = number(modelFaults);
  $("kpi-alerts").textContent = number(state.alerts.length);
  $("kpi-healthy").textContent = `${healthy}/${state.health.length}`;
  const f1 = state.summary?.classification?.station_test?.binary_fault_detection?.f1;
  $("kpi-f1").textContent = percent(f1, 1);
}

function healthClass(row) { return ["healthy", "monitor", "degrading", "critical"].includes(row.status) ? row.status : "monitor"; }

function renderHealth() {
  const rows = state.health.filter((row) => state.healthFilter === "all" || row.status === state.healthFilter);
  $("health-body").innerHTML = rows.map((row) => `<tr><td>${esc(stationName(row.station_id))}</td><td>${esc(pretty(row.sensor))}</td>
    <td><div class="health-meter"><b>${number(row.health_score, 1)}</b><span><i class="${healthClass(row)}" style="width:${Math.max(0, Math.min(100, Number(row.health_score)))}%"></i></span></div></td>
    <td><span class="health-status ${healthClass(row)}">${esc(pretty(row.status))}</span></td>
    <td>${esc(pretty(row.health_trend || "insufficient_history"))}</td>
    <td>${row.projected_health_7d === "" || row.projected_health_7d == null ? "—" : `${number(row.projected_health_7d, 1)}/100`}</td>
    <td>${row.maintenance_horizon_days === "" || row.maintenance_horizon_days == null ? "Not forecast" : `${number(row.maintenance_horizon_days, 1)} days`}</td>
    <td>${number(row.incident_count)}</td><td>${esc(formatTime(row.last_incident_utc))}</td><td>${esc(row.recommended_action)}</td></tr>`).join("") || `<tr><td colspan="10" class="empty-state">No sensors match this filter.</td></tr>`;
}

function metricRows(items) {
  return items.map(([label, value]) => `<div class="metric-row"><span>${esc(label)}</span><b>${esc(value)}</b></div>`).join("");
}

function renderValidation() {
  const split = state.selectedSplit;
  const classification = state.summary.classification[split];
  const detection = classification.binary_fault_detection;
  const event = classification.event_decision;
  const eventAbstention = event.abstention || null;
  const eventCalibration = event.calibration || null;
  const weather = event.per_class.genuine_weather;
  const root = classification.oracle_root_cause;
  const endRoot = classification.end_to_end_root_cause;
  const correction = state.summary.correction[split].operational;
  const safe = state.summary.safe_repair[split];

  const cards = [
    ["Fault precision", percent(detection.precision, 1), `${number(detection.tp)} true positives`],
    ["Fault recall", percent(detection.recall, 1), `${number(detection.fn)} missed rows`],
    ["Fault F1", percent(detection.f1, 1), "Precision–recall balance"],
    ["AUCPR", percent(detection.aucpr, 1), "Imbalanced-data metric"],
    ["Episode recall", percent(detection.episode_detection.recall, 1), `${number(detection.episode_detection.detected_episodes)}/${number(detection.episode_detection.episodes)} episodes`],
    ["Event accuracy", percent(event.accuracy, 2), eventAbstention ? `${number(eventAbstention.unknown_rows)} confidence abstentions` : "Three-class decision accuracy"],
  ];
  $("accuracy-strip").innerHTML = cards.map(([label, value, note]) => `<div class="accuracy-stat"><span>${esc(label)}</span><b>${esc(value)}</b><small>${esc(note)}</small></div>`).join("");
  $("detection-metrics").innerHTML = metricRows([
    ["Evaluated rows", number(detection.rows)], ["Fault-positive rows", number(detection.positives)],
    ["Precision", percent(detection.precision, 2)], ["Recall", percent(detection.recall, 2)], ["F1-score", percent(detection.f1, 2)],
    ["AUCPR", percent(detection.aucpr, 2)], ["False alarms / station-day", number(detection.false_alarms_per_station_day, 4)],
    ["Median episode latency", `${number(detection.episode_detection.median_detection_latency_minutes, 1)} min`],
  ]);
  const noWeather = Number(weather.support) === 0;
  $("weather-metrics").innerHTML = metricRows([
    ["Regional weather rows", number(weather.support)], ["Weather precision", noWeather ? "N/A in this holdout" : percent(weather.precision, 2)],
    ["Weather recall", noWeather ? "N/A in this holdout" : percent(weather.recall, 2)], ["Weather F1", noWeather ? "N/A in this holdout" : percent(weather.f1, 2)],
    ["Weather → fault false positives", number(detection.weather_false_positives)], ["Weather false-positive rate", percent(detection.weather_false_positive_rate, 3)],
    ["Model calibration error", eventCalibration ? percent(eventCalibration.expected_calibration_error, 3) : "Not reported for Phase 10"],
    ["Accepted event accuracy", eventAbstention ? percent(eventAbstention.accepted_accuracy, 2) : percent(event.accuracy, 2)],
  ]);
  $("root-metrics").innerHTML = metricRows([
    ["Oracle root-cause accuracy", percent(root.accuracy, 2)], ["Oracle macro F1", percent(root.macro_f1, 2)],
    ["End-to-end exact accuracy", percent(endRoot.exact_accuracy, 2)], ["Diagnostic coverage", percent(endRoot.diagnostic_coverage, 2)],
    ["Accepted diagnosis accuracy", percent(endRoot.accepted_root_accuracy, 2)], ["Missed detection rows", number(endRoot.missed_detection_rows)],
    ["Unknown / abstained fault rows", number(endRoot.unknown_fault_rows)], ["Root classes", number(root.classes.length)],
  ]);

  $("correction-body").innerHTML = ["temperature", "pressure", "humidity"].map((sensor) => {
    const row = correction[sensor];
    return `<tr><td>${sensorLabel[sensor]}</td><td>${number(row.changed_affected_points)}</td><td>${number(row.corrected_points)}</td><td>${percent(row.coverage, 2)}</td><td>${number(row.reported_value_mae, 2)} ${sensorUnit[sensor]}</td><td>${number(row.corrected_value_mae, 2)} ${sensorUnit[sensor]}</td><td>${number(row.corrected_value_rmse, 2)} ${sensorUnit[sensor]}</td><td>${number(row.mae_reduction_percent, 2)}%</td><td>${percent(row.interval_90_coverage, 2)}</td></tr>`;
  }).join("");

  $("safe-repair-body").innerHTML = ["temperature", "pressure", "humidity"].map((sensor) => {
    const review = safe[sensor].review, auto = safe[sensor].auto;
    const enabled = sensor !== "humidity";
    return `<tr><td>${sensorLabel[sensor]}</td><td>${number(review.proposed_corrections)}</td><td>${percent(review.precision, 2)}</td><td>${percent(review.coverage_recall, 2)}</td><td>${number(auto.proposed_corrections)}</td><td>${auto.proposed_corrections ? percent(auto.precision, 2) : "N/A"}</td><td>${percent(auto.coverage_recall, 2)}</td><td><span class="decision ${enabled ? "genuine_weather" : "sensor_fault"}">${enabled ? "High-precision gate" : "Review only"}</span></td></tr>`;
  }).join("");

  const episodeTypes = detection.episode_detection.per_fault_type;
  $("fault-grid").innerHTML = Object.entries(episodeTypes).map(([name, item]) => `<div class="fault-score"><span>${esc(pretty(name))}</span><b>${percent(item.recall, 0)}</b><small>${number(item.detected)}/${number(item.episodes)} episodes</small><div class="mini-track"><i style="width:${Number(item.recall) * 100}%"></i></div></div>`).join("");
}

function renderProfiles() {
  const profiles = state.summary.streaming.profiles;
  const full = state.summary.competition?.benchmark;
  const modelProfile = full ? `<div class="profile-item"><span>Complete Phase 10 inference</span><b>${number(full.throughput_rows_per_second)} rows/sec</b><small>${number(full.mean_wall_latency_ms_per_row, 3)} ms/row · temporal + neighbour + trend + event + root cause</small></div>` : "";
  $("profile-list").innerHTML = modelProfile + Object.entries(profiles).map(([name, row]) => `<div class="profile-item"><span>${esc(pretty(name))}</span><b>${number(row.throughput_rows_per_second)} rows/sec</b><small>${number(row.mean_processing_latency_ms, 3)} ms mean latency · ${number(row.source_rows)} rows</small></div>`).join("");
}

function renderDataset() {
  const data = state.summary.dataset;
  const summary = data.summary;
  const checks = Object.values(data.checks);
  $("data-rows").textContent = number(summary.processed_rows);
  $("data-files").textContent = number(data.provenance.manifest_entries);
  $("data-clean").textContent = `${number(summary.clean_candidate_percent, 2)}%`;
  $("data-checks").textContent = `${checks.filter(Boolean).length}/${checks.length} pass`;
  $("range-list").innerHTML = metricRows(Object.entries(data.ranges).map(([sensor, row]) => [pretty(sensor), `${number(row.min, 2)} – ${number(row.max, 2)}`]));
  $("missing-list").innerHTML = metricRows(Object.entries(data.missing).map(([sensor, row]) => [pretty(sensor), `${number(row.rows)} rows · ${number(row.percent, 4)}%`]));
  $("data-limitation").textContent = data.limitation;
  $("policy-statement").textContent = state.summary.policy.statement;
}

function scheduleLiveRefresh() {
  window.clearInterval(state.liveTimer);
  state.liveTimer = null;
  if ($('auto-refresh').checked && state.mode === 'live') {
    state.liveTimer = window.setInterval(() => refreshOfficialLive(true), 300000);
  }
}

function bindControls() {
  $("chart-city").addEventListener('change', event => { state.selectedStation = event.target.value; renderNetwork(); renderReadings(); });
  $("trace-refresh").addEventListener('click', () => { if (state.mode === 'live') refreshOfficialLive(true); });
  document.querySelectorAll("#mode-selector button").forEach((button) => button.addEventListener("click", () => switchMode(button.dataset.mode)));
  $("scenario-select").addEventListener("change", () => { $("scenario-description").textContent = scenarioCopy[$("scenario-select").value] || "Controlled offline replay scenario."; });
  $("load-scenario").addEventListener("click", () => loadScenario(true));
  $("step-scenario").addEventListener("click", () => replayAction(() => api("/api/replay/step?count=25", { method: "POST" })));
  $("run-scenario").addEventListener("click", () => replayAction(() => api("/api/replay/step?count=10000", { method: "POST" })));
  $("reset-scenario").addEventListener("click", () => replayAction(() => api("/api/replay/reset", { method: "POST" })));
  $("refresh-live").addEventListener("click", () => refreshOfficialLive(true));
  $("auto-refresh").addEventListener("change", (event) => {
    scheduleLiveRefresh();
  });
  document.querySelectorAll("#split-selector button").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll("#split-selector button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active"); state.selectedSplit = button.dataset.split; renderValidation();
  }));
  document.querySelectorAll("#health-filter button").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll("#health-filter button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active"); state.healthFilter = button.dataset.filter; renderHealth();
  }));
  const injectBtn = $("inject-live-fault");
  if (injectBtn) {
    injectBtn.addEventListener("click", async () => {
      const stationId = $("inject-station-select").value;
      const faultType = $("inject-fault-select").value;
      let sensor = "temperature";
      let mag = 0.0;
      if (faultType === "temp_spike") { sensor = "temperature"; mag = 24.0; }
      else if (faultType === "press_drop") { sensor = "pressure"; mag = 38.0; }
      else if (faultType === "humidity_spike") { sensor = "humidity"; mag = 45.0; }
      else if (faultType === "temp_bounds") { sensor = "temperature"; mag = 0.0; }
      else if (faultType === "sensor_drift") { sensor = "temperature"; mag = 14.0; }
      else if (faultType === "frozen_sensor") { sensor = "temperature"; mag = 0.0; }

      setBusy(true);
      try {
        await api(`/api/live/inject-fault?station_id=${encodeURIComponent(stationId)}&sensor=${sensor}&fault_type=${faultType}&magnitude=${mag}`, { method: "POST" });
        const badge = $("injection-status-badge");
        if (badge) {
          badge.textContent = `Simulation added for ${stationName(stationId)}. Checking model output; this is not a real sensor fault.`;
          badge.className = "injection-status-badge alert-active";
        }
        state.selectedStation = stationId;
        await refreshOfficialLive(false);
        toast(`Simulation added for ${stationName(stationId)}. Inspect actual model output; detection is not assumed.`);
      } catch (err) {
        toast(`Fault injection failed: ${err.message}`, true);
      } finally {
        setBusy(false);
      }
    });
  }

  const clearBtn = $("clear-live-faults");
  if (clearBtn) {
    clearBtn.addEventListener("click", async () => {
      setBusy(true);
      try {
        await api("/api/live/clear-faults", { method: "POST" });
        const badge = $("injection-status-badge");
        if (badge) {
          badge.textContent = "Simulation removed. Source observations are not a sensor-health certification.";
          badge.className = "injection-status-badge";
        }
        await refreshOfficialLive(false);
        toast("Simulation overlay removed. Check source timestamps and model evidence.");
      } catch (err) {
        toast(`Reset failed: ${err.message}`, true);
      } finally {
        setBusy(false);
      }
    });
  }

  const allBtn = $("filter-all-stations");
  const actBtn = $("filter-active-stations");
  const benBtn = $("filter-benchmark-stations");
  if (allBtn && actBtn && benBtn) {
    const setNetFilter = (filter, activeBtn) => {
      [allBtn, actBtn, benBtn].forEach((b) => { b.className = "toolbar-pill"; });
      activeBtn.className = "toolbar-pill active";
      state.networkFilter = filter;
      renderNetwork();
    };
    allBtn.addEventListener("click", () => setNetFilter("all", allBtn));
    actBtn.addEventListener("click", () => setNetFilter("active", actBtn));
    benBtn.addEventListener("click", () => setNetFilter("benchmark", benBtn));
  }

  const zoneFilter = $("climate-zone-filter");
  if (zoneFilter) {
    zoneFilter.addEventListener("change", (e) => {
      state.zoneFilter = e.target.value;
      renderNetwork();
    });
  }

  const searchInput = $("station-search-input");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      state.searchQuery = e.target.value;
      renderNetwork();
    });
  }

  window.addEventListener("resize", () => renderNetwork());
}

async function initialize() {
  bindControls();
  try {
    const [healthCheck, scenarios, summary, stations, health] = await Promise.all([
      api("/health"), api("/api/scenarios"), api("/api/dashboard-summary"), api("/api/stations"),
      api("/api/sensor-health"),
    ]);
    state.summary = summary; state.stations = stations; state.health = health;

    const benchStations = stations.filter(st => st.is_benchmark == 1 || st.evaluation_role === 'development' || st.evaluation_role === 'station_holdout');
    const benchOptions = benchStations.map(st => `<option value="${esc(st.station_id)}">⭐ ${esc(st.station_name)} (${esc(st.icao || st.station_id)})</option>`).join('');

    const zones = [...new Set(stations.map(st => st.climate_zone || 'Other'))].sort();
    const zoneOptgroups = zones.map(z => {
      const zStations = stations.filter(st => (st.climate_zone || 'Other') === z && !(st.is_benchmark == 1 || st.evaluation_role === 'development' || st.evaluation_role === 'station_holdout'));
      if (!zStations.length) return '';
      return `<optgroup label="${esc(z)} (${zStations.length})">${zStations.map(st => `<option value="${esc(st.station_id)}">${esc(st.station_name)} (${esc(st.icao || st.station_id)})</option>`).join('')}</optgroup>`;
    }).join('');

    $("chart-city").innerHTML = `<optgroup label="⭐ Core Benchmark & METAR Stations (${benchStations.length})">${benchOptions}</optgroup>${zoneOptgroups}`;
    $("connection-text").textContent = healthCheck.offline ? "System online" : "Connected";
    document.querySelector(".pulse").classList.add("online");

    const liveTargetSelect = $("inject-station-select");
    if (liveTargetSelect) {
      const icaoStations = stations.filter(st => st.icao && st.icao.trim());
      liveTargetSelect.innerHTML = (icaoStations.length ? icaoStations : benchStations).map((st) => `<option value="${esc(st.station_id)}">${esc(st.station_name)} (${esc(st.icao || st.cluster)})</option>`).join("");
    }

    $("scenario-select").innerHTML = scenarios.map((scenario) => `<option value="${esc(scenario.name)}">${esc(pretty(scenario.name))} · ${number(scenario.source_rows || scenario.rows)} rows</option>`).join("");
    const preferred = scenarios.find((scenario) => scenario.name === "pressure_drift");
    if (preferred) $("scenario-select").value = preferred.name;
    $("scenario-description").textContent = scenarioCopy[$("scenario-select").value] || "Controlled offline replay scenario.";
    renderHealth(); renderValidation(); renderProfiles(); renderDataset(); renderKpis();
    $("raw-metrics").textContent = JSON.stringify({ classification: summary.classification, correction: summary.correction, safe_repair: summary.safe_repair, full_inference: summary.competition, streaming: summary.streaming, dataset: summary.dataset }, null, 2);

    // Boot directly into LIVE observations
    await refreshOfficialLive(true);
    scheduleLiveRefresh();
    window.clearInterval(state.freshnessTimer);
    state.freshnessTimer = window.setInterval(() => {
      if (state.mode === 'live') { renderLiveStatus(state.liveStatus || {}); renderTraceFreshness(); }
    }, 30000);
  } catch (error) {
    $("connection-text").textContent = "Data unavailable";
    toast(`Dashboard could not load: ${error.message}. Restart the SkyGuard server.`, true);
  }
}

document.addEventListener("DOMContentLoaded", initialize);
