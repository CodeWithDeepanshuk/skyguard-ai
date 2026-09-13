const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const nodes = new Map();
const get = id => {
  if (!nodes.has(id)) {
    nodes.set(id, {
      id,
      textContent: '',
      innerHTML: '',
      value: '',
      className: '',
      style: {},
      dataset: {},
      classList: {
        classes: new Set(),
        add(c) { this.classes.add(c); },
        remove(c) { this.classes.delete(c); },
        toggle(c, v) { if (v) this.classes.add(c); else this.classes.delete(c); },
        contains(c) { return this.classes.has(c); }
      },
      listeners: {},
      addEventListener(event, fn) {
        if (!this.listeners[event]) this.listeners[event] = [];
        this.listeners[event].push(fn);
      },
      click() {
        if (this.listeners['click']) {
          this.listeners['click'].forEach(fn => fn());
        }
      }
    });
  }
  return nodes.get(id);
};

let clockTime = Date.parse('2026-09-10T18:00:00Z');
class TestDate extends Date { static now() { return clockTime; } }

const context = {
  console,
  Date: TestDate,
  JSON,
  Number,
  String,
  Math,
  Set,
  stationSupport: require('../dashboard/live-qc.js').stationSupport,
  document: {
    getElementById: get,
    addEventListener() {},
    querySelectorAll(sel) { return []; },
    body: { dataset: {} }
  },
  window: {
    renderSensorTrace(rows) {},
    clearTimeout() {},
    setTimeout() {},
    clearInterval() {},
    setInterval() {},
    addEventListener() {}
  },
  SkyGuardMap: { reset() {}, add() {}, finish() {} },
  fetch: async () => ({ ok: true, json: async () => ({}) })
};

vm.createContext(context);
vm.runInContext(fs.readFileSync('dashboard/app.js', 'utf8'), context);
vm.runInContext(`bindControls();`, context);

vm.runInContext(`
  state.stations = [
    { station_id: 'VOMM', station_name: 'Chennai Intl', latitude: 12.99, longitude: 80.17 },
    { station_id: 'VIAR', station_name: 'Amritsar', latitude: 31.71, longitude: 74.80 }
  ];
  state.readings = [
    { station_id: 'VOMM', timestamp_utc: '2026-09-10T17:00:00Z', temperature: 29.5, pressure: 1010.0, humidity: 70.0 }
  ];
  state.selectedStation = 'VOMM';
`, context);

// Test injection
const injectBtn = get('inject-live-fault');
get('inject-station-select').value = 'VOMM';
get('inject-fault-select').value = 'temp_spike';

(async () => {
  console.log("Triggering click on inject-live-fault...");
  await injectBtn.listeners['click'][0]();

  console.log("sim-val-shock:", get('sim-val-shock').textContent);
  console.log("sim-val-detect:", get('sim-val-detect').textContent);
  console.log("sim-val-repair:", get('sim-val-repair').textContent);
  console.log("injection-status-badge:", get('injection-status-badge').textContent);
  console.log("current-temp:", get('current-temp').textContent);

  assert.match(get('sim-val-shock').textContent, /53\.5/);
  assert.equal(get('sim-val-detect').textContent, '8.42σ Flagged');
  assert.match(get('sim-val-repair').textContent, /29\.5/);
  assert.equal(get('current-temp').textContent, '53.5');

  console.log("Testing clear-live-faults...");
  const clearBtn = get('clear-live-faults');
  await clearBtn.listeners['click'][0]();

  console.log("Restored sim-val-shock:", get('sim-val-shock').textContent);
  console.log("Restored current-temp:", get('current-temp').textContent);
  assert.equal(get('sim-val-shock').textContent, 'Nominal');
  assert.equal(get('current-temp').textContent, '29.5');

  console.log("ALL INJECTION TESTS PASSED SUCCESFULLY!");
})().catch(err => {
  console.error("TEST FAILED:", err);
  process.exit(1);
});
