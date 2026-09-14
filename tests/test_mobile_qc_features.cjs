const assert = require('node:assert/strict');
const SkyGuardQC = require('../dashboard/mobile-qc.js');

console.log('Testing SkyGuardQC Baseline Meteorological Quality Control...');

// 1. Physical Bounds Checks
{
  const normalRow = { temperature: 28.5, pressure: 1012.3, humidity: 65.0 };
  const violationsNormal = SkyGuardQC.BaselineQC.checkPhysicalBounds(normalRow);
  assert.equal(violationsNormal.length, 0, 'Normal reading should produce 0 violations');

  const hotRow = { temperature: 65.0, pressure: 1012.3, humidity: 65.0 };
  const violationsHot = SkyGuardQC.BaselineQC.checkPhysicalBounds(hotRow);
  assert.equal(violationsHot.length, 1, 'Temperature 65°C should violate physical max');
  assert.equal(violationsHot[0].sensor, 'temperature');
  assert.equal(violationsHot[0].type, 'range_violation');

  const lowPressureRow = { temperature: 25.0, pressure: 450.0, humidity: 50.0 };
  const violationsPress = SkyGuardQC.BaselineQC.checkPhysicalBounds(lowPressureRow);
  assert.equal(violationsPress.length, 1, 'Pressure 450 hPa should violate physical min');

  const overHumidRow = { temperature: 25.0, pressure: 1000.0, humidity: 105.0 };
  const violationsHumid = SkyGuardQC.BaselineQC.checkPhysicalBounds(overHumidRow);
  assert.equal(violationsHumid.length, 1, 'Humidity 105% should violate physical max 100%');
  console.log('✔ Physical bounds validation passed');
}

// 2. Step Change Rate-of-Change Checks
{
  const prev = { timestamp_utc: '2026-09-14T10:00:00Z', temperature: 25.0, pressure: 1010.0 };
  const currNormal = { timestamp_utc: '2026-09-14T10:15:00Z', temperature: 25.8, pressure: 1009.8 };
  const stepNormal = SkyGuardQC.BaselineQC.checkStep(prev, currNormal);
  assert.equal(stepNormal.length, 0, 'Normal 0.8°C / 15min step should pass');

  // +4°C in 15min = 16°C/hr rate (> 5.0°C/hr threshold)
  const currSpike = { timestamp_utc: '2026-09-14T10:15:00Z', temperature: 29.0, pressure: 1010.0 };
  const stepSpike = SkyGuardQC.BaselineQC.checkStep(prev, currSpike);
  assert.equal(stepSpike.length, 1, '4°C in 15 min should exceed 5°C/hr threshold');
  assert.equal(stepSpike[0].sensor, 'temperature');
  assert.equal(stepSpike[0].type, 'step_change');
  console.log('✔ Step-change validation passed');
}

// 3. Persistence Flatline Freeze Check
{
  const flatlineRows = [
    { temperature: 31.2 },
    { temperature: 31.2 },
    { temperature: 31.2 },
    { temperature: 31.2 },
    { temperature: 31.2 },
  ];
  const freezeIssue = SkyGuardQC.BaselineQC.checkPersistence(flatlineRows, 'temperature', 5);
  assert.notEqual(freezeIssue, null, '5 identical temperature values should trigger persistence_freeze');
  assert.equal(freezeIssue.type, 'persistence_freeze');
  assert.equal(freezeIssue.value, 31.2);

  const varyingRows = [
    { temperature: 31.2 },
    { temperature: 31.3 },
    { temperature: 31.2 },
    { temperature: 31.1 },
    { temperature: 31.2 },
  ];
  const noFreeze = SkyGuardQC.BaselineQC.checkPersistence(varyingRows, 'temperature', 5);
  assert.equal(noFreeze, null, 'Natural small variations should not trigger freeze');
  console.log('✔ Persistence flatline check passed');
}

// 4. Humidity Boundary Run Check
{
  const stuck100 = [
    { humidity: 100.0 }, { humidity: 100.0 }, { humidity: 100.0 },
    { humidity: 100.0 }, { humidity: 100.0 }, { humidity: 100.0 }
  ];
  const bound100 = SkyGuardQC.BaselineQC.checkHumidityBoundary(stuck100, 6);
  assert.notEqual(bound100, null);
  assert.equal(bound100.boundary, '100%');

  const stuck0 = [
    { humidity: 0.0 }, { humidity: 0.0 }, { humidity: 0.0 },
    { humidity: 0.0 }, { humidity: 0.0 }, { humidity: 0.0 }
  ];
  const bound0 = SkyGuardQC.BaselineQC.checkHumidityBoundary(stuck0, 6);
  assert.notEqual(bound0, null);
  assert.equal(bound0.boundary, '0%');
  console.log('✔ Humidity boundary run check passed');
}

// 5. Time Integrity & Timestamp Order Checks
{
  const invertedRows = [
    { station_id: 'TEST1', timestamp_utc: '2026-09-14T10:00:00Z' },
    { station_id: 'TEST1', timestamp_utc: '2026-09-14T09:45:00Z' }, // Inversion
  ];
  const timeIssues = SkyGuardQC.BaselineQC.checkTimeIntegrity(invertedRows);
  assert.equal(timeIssues.length, 1);
  assert.equal(timeIssues[0].type, 'time_order_error');

  const dupeRows = [
    { station_id: 'TEST1', timestamp_utc: '2026-09-14T10:00:00Z' },
    { station_id: 'TEST1', timestamp_utc: '2026-09-14T10:00:00Z' }, // Duplicate
  ];
  const dupeIssues = SkyGuardQC.BaselineQC.checkTimeIntegrity(dupeRows);
  assert.equal(dupeIssues.length, 1);
  assert.equal(dupeIssues[0].type, 'duplicate_timestamp');
  console.log('✔ Time integrity check passed');
}

// 6. Leave-one-out Spatial Buddy Check with Elevation Lapse-Rate
{
  const targetStation = { station_id: 'STN_TGT', station_name: 'Target Station', latitude: 28.5, longitude: 77.1, elevation_m: 200 };
  const targetReading = { station_id: 'STN_TGT', timestamp_utc: '2026-09-14T12:00:00Z', temperature: 38.0 }; // Spike!

  const neighbours = [
    { station_id: 'STN_N1', station_name: 'Neighbour 1', latitude: 28.6, longitude: 77.2, elevation_m: 200 },
    { station_id: 'STN_N2', station_name: 'Neighbour 2', latitude: 28.4, longitude: 77.0, elevation_m: 500 }, // +300m elevation
    { station_id: 'STN_N3', station_name: 'Neighbour 3', latitude: 28.55, longitude: 77.15, elevation_m: 210 },
  ];

  const neighbourReadings = [
    { station_id: 'STN_N1', timestamp_utc: '2026-09-14T12:00:00Z', temperature: 31.0 },
    // N2 is at 500m vs target 200m (300m higher). With -6.5°C/km lapse rate, N2 raw 29.05°C adjusts to ~31.0°C at 200m
    { station_id: 'STN_N2', timestamp_utc: '2026-09-14T12:00:00Z', temperature: 29.05 },
    { station_id: 'STN_N3', timestamp_utc: '2026-09-14T12:00:00Z', temperature: 30.8 },
  ];

  const buddyResult = SkyGuardQC.BaselineQC.checkSpatialBuddy(
    targetStation,
    targetReading,
    [targetStation, ...neighbours],
    [targetReading, ...neighbourReadings],
    'temperature'
  );

  assert.notEqual(buddyResult, null);
  assert.equal(buddyResult.is_discrepant, true, 'Target 38.0°C vs neighbour median ~31.0°C should be DISCREPANT');
  assert.equal(buddyResult.status, 'DISCREPANT');
  assert.ok(buddyResult.z_spatial >= 3.5, `Z-spatial should exceed 3.5σ, got ${buddyResult.z_spatial}`);
  assert.equal(buddyResult.neighbours.length, 3);
  console.log('✔ Spatial buddy check with lapse-rate passed');
}

// 7. IncidentStore Grouping, Acknowledgment, Notes & Resolution
{
  const readingsWithFaults = [
    { station_id: 'VIAR', timestamp_utc: '2026-09-14T08:00:00Z', temperature: 36.5, event_decision: 'sensor_fault', alert_type: 'temp_spike', fault_probability: 0.92, residual: 4.2 },
    { station_id: 'VIAR', timestamp_utc: '2026-09-14T08:15:00Z', temperature: 36.6, event_decision: 'sensor_fault', alert_type: 'temp_spike', fault_probability: 0.94, residual: 4.3 },
    { station_id: 'VIAR', timestamp_utc: '2026-09-14T08:30:00Z', temperature: 36.8, event_decision: 'sensor_fault', alert_type: 'temp_spike', fault_probability: 0.95, residual: 4.5 },
  ];

  const stations = [{ station_id: 'VIAR', station_name: 'Amritsar Airport' }];

  const incidents = SkyGuardQC.IncidentStore.groupReadingsIntoIncidents(readingsWithFaults, stations);
  assert.equal(incidents.length, 1, '3 consecutive temperature fault readings on VIAR must group into exactly 1 incident');
  const inc = incidents[0];
  assert.equal(inc.station_id, 'VIAR');
  assert.equal(inc.sensor, 'temperature');
  assert.equal(inc.readings_count, 3);
  assert.equal(inc.status, 'new');

  // Test Acknowledge
  const ackSuccess = SkyGuardQC.IncidentStore.acknowledge(inc.incident_id, 'Technician Rahul');
  assert.equal(ackSuccess, true);
  assert.equal(inc.status, 'acknowledged');

  // Test Operator Notes
  const note = SkyGuardQC.IncidentStore.addNote(inc.incident_id, 'Checked RTD junction box; wiring loose.', 'Technician Rahul');
  assert.equal(note.note, 'Checked RTD junction box; wiring loose.');
  const allNotes = SkyGuardQC.IncidentStore.getNotes(inc.incident_id);
  assert.ok(allNotes.length >= 2, 'Should have ack note + custom note');

  // Test Resolve
  const resSuccess = SkyGuardQC.IncidentStore.resolve(inc.incident_id, 'Tightened terminal screws; reading normalized.', 'Technician Rahul');
  assert.equal(resSuccess, true);
  assert.equal(inc.status, 'resolved');

  // Test CSV & JSON exports
  const csv = SkyGuardQC.IncidentStore.exportAsCSV(incidents);
  assert.match(csv, /Incident ID,Station ID,Station Name/);
  assert.match(csv, /VIAR/);

  const json = SkyGuardQC.IncidentStore.exportAsJSON(incidents);
  const parsedJson = JSON.parse(json);
  assert.equal(parsedJson.total_incidents, 1);
  assert.equal(parsedJson.incidents[0].station_id, 'VIAR');
  console.log('✔ IncidentStore grouping, lifecycle, and exports passed');
}

// 8. WorkbookParser CSV Parsing & Synthetic Dataset
{
  const rawCsv = `Station ID,Timestamp,Temperature_C,Pressure_hPa,Relative_Humidity
STN_01,2026-09-14T00:00:00Z,28.4,1012.0,65
STN_01,2026-09-14T01:00:00Z,28.2,1011.8,66
STN_01,BAD_TIMESTAMP,28.1,1011.6,67
`;
  const parseResult = SkyGuardQC.WorkbookParser.parseCSV(rawCsv);
  assert.equal(parseResult.success, true);
  assert.equal(parseResult.total_rows, 3);
  assert.equal(parseResult.valid_rows, 2);
  assert.equal(parseResult.error_rows.length, 1);
  assert.equal(parseResult.data[0].temperature, 28.4);

  // Synthetic sample data generator
  const sample = SkyGuardQC.WorkbookParser.generateSampleData();
  assert.equal(sample.success, true);
  assert.ok(sample.valid_rows >= 90, `Sample data should generate ~96 rows, got ${sample.valid_rows}`);
  console.log('✔ WorkbookParser and synthetic generator passed');
}

console.log('\nALL 8 METEOROLOGICAL QC & MOBILE TEST SUITES PASSED CLEANLY! 🎉');
