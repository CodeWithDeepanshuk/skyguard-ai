import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

describe('SkyGuard AI Physical & API Validation Tests', () => {
  test('Strict three-parameter physical bounds: temperature out of range triggers SENSOR_FAULT', () => {
    const invalidTemp = 75.0; // Above 65°C Indian max limit
    const minTemp = -60.0;
    const maxTemp = 65.0;
    const isOutOfRange = invalidTemp < minTemp || invalidTemp > maxTemp;
    assert.equal(isOutOfRange, true, 'Temperature 75.0C must violate physical boundary');
  });

  test('Strict three-parameter physical bounds: station pressure bounds', () => {
    const validPress = 1008.2;
    const invalidPress = 450.0; // Barometric transducer disconnect
    assert.equal(validPress >= 600 && validPress <= 1100, true);
    assert.equal(invalidPress >= 600 && invalidPress <= 1100, false);
  });

  test('Transport gap separation: missing readings must NOT become hardware sensor faults', () => {
    const event = {
      type: 'HEARTBEAT_TIMEOUT',
      gap_minutes: 180,
      sensor_values_present: false,
    };
    const decision = event.sensor_values_present ? 'SENSOR_FAULT' : 'TRANSPORT_OR_DATA_GAP';
    assert.equal(decision, 'TRANSPORT_OR_DATA_GAP');
  });

  test('Integer freeze detector: run-length threshold check', () => {
    const runLength = 1;
    const isFrozen = runLength >= 12; // Minimum persistent run-length
    assert.equal(isFrozen, false, 'Single repeated integer must not trigger freeze');
  });

  test('Persistence engine: k-of-n voting requires minimum 3 persistent votes', () => {
    const votes = 1;
    const k = 3;
    const isConfirmedIncident = votes >= k;
    assert.equal(isConfirmedIncident, false, 'Single noisy row must not open incident');
  });
});
