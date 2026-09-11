const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const nodes = new Map();
const get = id => { if(!nodes.has(id)) nodes.set(id,{textContent:'',innerHTML:'',value:'',style:{},dataset:{},classList:{toggle(){}},addEventListener(){}}); return nodes.get(id); };
let alertButtons = [];
let mapSelect = {};
let clockTime = Date.parse('2026-09-10T18:00:00Z');
class TestDate extends Date { static now() { return clockTime; } }
const context = {console, Date:TestDate, JSON, Number, String, Math, Set,
  stationSupport:require('../dashboard/live-qc.js').stationSupport,
  document:{getElementById:get, addEventListener(){},querySelectorAll(selector){ return selector==='[data-alert-index]' ? alertButtons : []; },body:{dataset:{}}},
  window:{renderSensorTrace(rows){context.chartRows = rows;},clearTimeout(){},setTimeout(){},clearInterval(){},setInterval(){}},
  SkyGuardMap:{reset(){},add(station,health,selected,onSelect){mapSelect[station.station_id]=onSelect;},finish(){}}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('dashboard/app.js','utf8'),context);
vm.runInContext(`
state.stations=[{station_id:'JAIPUR',station_name:'Jaipur',latitude:26,longitude:75},{station_id:'DELHI',station_name:'Delhi',latitude:28,longitude:77}];
state.readings=[{station_id:'JAIPUR',timestamp_utc:'2026-09-10T17:00:00Z',temperature:31},{station_id:'DELHI',timestamp_utc:'2026-09-10T17:30:00Z',temperature:28},{station_id:'DELHI',timestamp_utc:'2026-09-10T16:30:00Z',temperature:27}];
state.selectedStation='DELHI'; renderNetwork();
`,context);
assert.match(get('chart-subtitle').textContent,/Delhi/);
assert.equal(get('current-temp').textContent,'28.0');
assert.equal(context.chartRows.length,2);
assert.equal(context.chartRows[0].temperature,27);
vm.runInContext("state.readings=state.readings.filter(r=>r.station_id==='JAIPUR');renderNetwork();",context);
assert.match(get('chart-subtitle').textContent,/Delhi/);
assert.equal(context.chartRows.length,0);
assert.equal(get('current-temp').textContent,'—');
console.log('PASS: selected city, timestamp ordering, latest value and missing-station isolation.');

vm.runInContext(`
state.incidents=[{station_id:'JAIPUR',root_cause:'pressure_drift',severity:'high',explanation:'Jaipur only',fault_probability:0.8}];
renderNetwork();
`,context);
assert.match(get('incident-title').textContent,/Delhi/);
assert.equal(get('fault-confidence').textContent,'—');
mapSelect.JAIPUR();
assert.match(get('incident-title').textContent,/Jaipur/);
assert.equal(get('fault-confidence').textContent,'80.0%');
mapSelect.DELHI();
assert.equal(get('fault-confidence').textContent,'—');

const alertButton={dataset:{alertIndex:'0'},addEventListener(event,callback){this.click=callback;}};
alertButtons=[alertButton];
vm.runInContext("state.alerts=[{station_id:'DELHI',alert_type:'pressure_drift'}];renderAlertQueue();",context);
alertButton.click();
assert.match(get('incident-title').textContent,/Delhi/);
assert.equal(get('fault-confidence').textContent,'—');
vm.runInContext("state.alerts=[];renderAlertQueue();",context);
assert.match(get('alert-list').innerHTML,/health remains unverified/);
assert.doesNotMatch(get('alert-list').innerHTML,/All stations normal/);

vm.runInContext(`state.liveStatus={status:'cached',is_cached:true,source_age_minutes:0,observation_count:3,latest_observation_utc:'2026-09-10T17:30:00Z',fetched_at_utc:'2026-09-10T17:35:00Z'};setBusy(true);setBusy(false);`,context);
assert.equal(get('replay-state').textContent,'Cached');
assert.equal(get('live-age').textContent,'30 min old');
clockTime += 30*60000;
vm.runInContext('renderLiveStatus(state.liveStatus)',context);
assert.equal(get('live-age').textContent,'60 min old');
assert.equal(vm.runInContext("ageLabel('bad timestamp')",context),'Age unavailable');
assert.equal(vm.runInContext("ageLabel('2026-09-11T00:00:00Z')",context),'Future timestamp · check clock');
assert.equal(vm.runInContext("number('')",context),'—');
vm.runInContext("state.mode='replay';renderNetwork();",context);
assert.equal(get('trace-status').textContent,'OFFLINE REPLAY');
assert.doesNotMatch(get('trace-time').textContent,/Fetched/);
console.log('PASS: station-only incidents, map/alert selection, honest empty states, cached status and ticking ages.');

(async () => {
  vm.runInContext("state.mode='live';state.selectedStation='DELHI';",context);
  context.fetch=async path=>({ok:true,json:async()=> path.includes('status') ? {observation_count:1,is_cached:true} : path.includes('readings') ? [{station_id:'DELHI',temperature:26,timestamp_utc:'2026-09-10T17:30:00Z'}] : path.includes('incidents') ? [{station_id:'JAIPUR',root_cause:'pressure_drift',fault_probability:0.99}] : []});
  await vm.runInContext('refreshOfficialLive(false)',context);
  assert.match(get('incident-title').textContent,/Delhi/);
  assert.equal(get('fault-confidence').textContent,'—');
  assert.equal(get('replay-state').textContent,'Cached');
  context.fetch=async()=>{throw new Error('network unavailable');};
  await vm.runInContext('refreshOfficialLive(true)',context);
  assert.equal(get('replay-state').textContent,'Source unavailable');
  assert.match(get('trace-status').textContent,/CACHED/);
  assert.equal(get('current-temp').textContent,'26.0');

  let release;
  context.fetch=()=>new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>({observation_count:2})});});
  const pending=vm.runInContext('refreshOfficialLive(false)',context);
  vm.runInContext("state.mode='replay';state.viewRevision+=1;state.readings=[{station_id:'DELHI',temperature:19}];state.incidents=[];",context);
  context.fetch=async()=>({ok:true,json:async()=>[]});
  release();
  await pending;
  assert.equal(vm.runInContext('state.readings[0].temperature',context),19);
  assert.equal(vm.runInContext('state.incidents.length',context),0);
  assert.equal(vm.runInContext('state.busyDepth',context),0);
  console.log('PASS: asynchronous refresh isolation, failure recovery and late live response cannot overwrite replay.');
})().catch(error=>{console.error(error);process.exitCode=1;});
