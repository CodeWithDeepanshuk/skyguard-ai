import fs from 'fs';
import path from 'path';
import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

type EvidenceStatus = 'RECORDED_PASS' | 'RECORDED_RESULT' | 'LIMITATION' | 'EXCLUDED' | 'UNAVAILABLE';

interface EvidenceItem {
  key: string;
  name: string;
  category: string;
  status: EvidenceStatus;
  measured_value: string;
  scope: string;
  description: string;
  artifact: string | null;
}

function readJson(root: string, relativePath: string): any | null {
  const file = path.join(root, relativePath);
  if (!fs.existsSync(file)) return null;
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return null;
  }
}

function allChecksPass(value: unknown): boolean {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const checks = Object.values(value as Record<string, unknown>);
  return checks.length > 0 && checks.every(Boolean);
}

function metric(value: unknown, digits = 3): string {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : 'Not available';
}

export async function GET() {
  const root = process.cwd();
  const phase10 = readJson(root, 'reports/phase10_final.json');
  const dataValidation = readJson(root, 'reports/data_validation.json');
  const featureValidation = readJson(root, 'reports/feature_validation.json');
  const labelledValidation = readJson(root, 'reports/labelled_validation.json');
  const streamingValidation = readJson(root, 'reports/streaming_validation.json');
  const correctionValidation = readJson(root, 'reports/correction_health_validation.json');
  const safeRepairValidation = readJson(root, 'reports/safe_repair_validation.json');
  const candidatePath = path.join(root, 'reports', 'final_evaluation', 'final_result_block.json');

  const timeFault = phase10?.evaluation?.time_test?.binary_fault_detection;
  const stationFault = phase10?.evaluation?.station_test?.binary_fault_detection;
  const inputContract = phase10?.policy?.input_contract;

  const evidence: EvidenceItem[] = [
    {
      key: 'THREE_PARAMETER_CONTRACT',
      name: 'SIH three-parameter inference contract',
      category: 'Scientific contract',
      status: phase10 && Array.isArray(inputContract) ? 'RECORDED_PASS' : 'UNAVAILABLE',
      measured_value: Array.isArray(inputContract) ? inputContract.join(', ') : 'Artifact unavailable',
      scope: 'Verified Phase 10 offline artifact',
      description: 'Detector inputs are limited to temperature, pressure and relative humidity; identity and timing metadata support alignment only.',
      artifact: phase10 ? 'reports/phase10_final.json' : null,
    },
    {
      key: 'DATA_PROVENANCE',
      name: 'Source and checksum validation',
      category: 'Data integrity',
      status: allChecksPass(dataValidation?.checks) ? 'RECORDED_PASS' : dataValidation ? 'RECORDED_RESULT' : 'UNAVAILABLE',
      measured_value: dataValidation ? `${Object.values(dataValidation.checks || {}).filter(Boolean).length}/${Object.keys(dataValidation.checks || {}).length} recorded checks` : 'Artifact unavailable',
      scope: 'Historical offline dataset',
      description: 'Records the source-file, schema, checksum and station/year coverage checks made by the historical-data build.',
      artifact: dataValidation ? 'reports/data_validation.json' : null,
    },
    {
      key: 'CAUSAL_FEATURES',
      name: 'Causal feature validation',
      category: 'Leakage prevention',
      status: featureValidation?.error_count === 0 && allChecksPass(featureValidation?.checks) ? 'RECORDED_PASS' : featureValidation ? 'RECORDED_RESULT' : 'UNAVAILABLE',
      measured_value: featureValidation ? `${featureValidation.model_feature_count ?? 'Unknown'} model features; ${featureValidation.error_count ?? 'unknown'} recorded errors` : 'Artifact unavailable',
      scope: 'Historical feature-generation pipeline',
      description: 'Includes backward-only neighbour alignment, first-lag causality, finite numeric inputs and manifest hash checks.',
      artifact: featureValidation ? 'reports/feature_validation.json' : null,
    },
    {
      key: 'DISJOINT_SPLITS',
      name: 'Time and station holdout integrity',
      category: 'Generalisation',
      status: labelledValidation?.error_count === 0 && allChecksPass(labelledValidation?.checks) ? 'RECORDED_PASS' : labelledValidation ? 'RECORDED_RESULT' : 'UNAVAILABLE',
      measured_value: labelledValidation ? `${labelledValidation.episode_count ?? 'Unknown'} injected evaluation episodes` : 'Artifact unavailable',
      scope: 'Fault-injected offline benchmark',
      description: 'The recorded build checks time roles, globally unique episodes, row separation and station-only holdout membership.',
      artifact: labelledValidation ? 'reports/labelled_validation.json' : null,
    },
    {
      key: 'TIME_HOLDOUT',
      name: 'Locked time-holdout detection result',
      category: 'Detection performance',
      status: timeFault ? 'RECORDED_RESULT' : 'UNAVAILABLE',
      measured_value: timeFault ? `Precision ${metric(timeFault.precision)} · Recall ${metric(timeFault.recall)} · F1 ${metric(timeFault.f1)} · AUCPR ${metric(timeFault.aucpr)}` : 'Artifact unavailable',
      scope: 'Fault-injected 2024 time holdout; not live-field accuracy',
      description: 'A historical offline benchmark result. It does not establish performance on independently confirmed live hardware failures.',
      artifact: phase10 ? 'reports/phase10_final.json' : null,
    },
    {
      key: 'UNSEEN_STATION_HOLDOUT',
      name: 'Unseen-station detection result',
      category: 'Generalisation',
      status: stationFault ? 'RECORDED_RESULT' : 'UNAVAILABLE',
      measured_value: stationFault ? `Precision ${metric(stationFault.precision)} · Recall ${metric(stationFault.recall)} · F1 ${metric(stationFault.f1)} · AUCPR ${metric(stationFault.aucpr)}` : 'Artifact unavailable',
      scope: 'Fault-injected station-disjoint holdout; not live-field accuracy',
      description: 'Measures transfer to held-out stations in the frozen research dataset. The lower recall is visible rather than hidden.',
      artifact: phase10 ? 'reports/phase10_final.json' : null,
    },
    {
      key: 'STREAM_REPLAY',
      name: 'Streaming scenario replay',
      category: 'Operational robustness',
      status: streamingValidation?.status === 'PASS' && streamingValidation?.error_count === 0 ? 'RECORDED_PASS' : streamingValidation ? 'RECORDED_RESULT' : 'UNAVAILABLE',
      measured_value: streamingValidation ? `${streamingValidation.scenario_count ?? 'Unknown'} packaged scenarios` : 'Artifact unavailable',
      scope: 'Offline replay and API contract tests',
      description: 'Recorded tests cover duplicate, dropout and timestamp evidence. This is not a claim about current provider uptime.',
      artifact: streamingValidation ? 'reports/streaming_validation.json' : null,
    },
    {
      key: 'ADVISORY_CORRECTION',
      name: 'Correction and sensor-health policy',
      category: 'Self-healing safeguards',
      status: correctionValidation?.status === 'PASS' ? 'RECORDED_PASS' : correctionValidation ? 'RECORDED_RESULT' : 'UNAVAILABLE',
      measured_value: correctionValidation ? `Recorded status: ${correctionValidation.status}` : 'Artifact unavailable',
      scope: 'Offline validation; corrections remain advisory',
      description: 'Source values remain immutable. Estimates include uncertainty and are never silently substituted into the observation record.',
      artifact: correctionValidation ? 'reports/correction_health_validation.json' : null,
    },
    {
      key: 'SAFE_AUTO_REPAIR',
      name: 'Automatic repair safety',
      category: 'Self-healing safeguards',
      status: safeRepairValidation?.status === 'PASS' ? 'RECORDED_PASS' : safeRepairValidation ? 'RECORDED_RESULT' : 'UNAVAILABLE',
      measured_value: safeRepairValidation ? `Recorded status: ${safeRepairValidation.status}; humidity auto-repair disabled: ${Boolean(safeRepairValidation.humidity_automatic_repair_disabled)}` : 'Artifact unavailable',
      scope: 'Historical injected-fault validation',
      description: 'The production UI exposes estimates for operator review and does not claim autonomous repair of live IMD sensors.',
      artifact: safeRepairValidation ? 'reports/safe_repair_validation.json' : null,
    },
    {
      key: 'LIVE_LABELS',
      name: 'Independent live hardware-fault labels',
      category: 'Open limitation',
      status: 'LIMITATION',
      measured_value: 'Not available',
      scope: 'Live operations',
      description: 'Public WIS2/METAR observations do not include independently confirmed maintenance labels, so live precision and recall are not claimed.',
      artifact: null,
    },
    {
      key: 'LIVE_CALIBRATION',
      name: 'Calibrated live fault probability',
      category: 'Open limitation',
      status: 'LIMITATION',
      measured_value: 'Not available — operational output is an anomaly evidence score',
      scope: 'Live operations',
      description: 'Calibration from injected research labels is not transferred silently to live observations from different providers and pressure semantics.',
      artifact: null,
    },
    {
      key: 'CANDIDATE_PROMOTION',
      name: 'Later 25-gate candidate promotion claim',
      category: 'Excluded claim',
      status: fs.existsSync(candidatePath) ? 'EXCLUDED' : 'UNAVAILABLE',
      measured_value: fs.existsSync(candidatePath) ? 'Excluded from public verified results' : 'Artifact not present',
      scope: 'Candidate artifact',
      description: 'The candidate artifact remains preserved in the repository but is not presented as certified until its generation is reproducible and independently reviewed.',
      artifact: fs.existsSync(candidatePath) ? 'reports/final_evaluation/final_result_block.json' : null,
    },
  ];

  const counts = evidence.reduce<Record<string, number>>((summary, item) => {
    summary[item.status] = (summary[item.status] || 0) + 1;
    return summary;
  }, {});

  return NextResponse.json({
    title: 'Scientific evidence register',
    model_version: phase10?.model_version ?? null,
    claim_scope: 'Recorded offline evidence plus explicit live-operational limitations; not a national deployment certification.',
    summary: counts,
    evidence,
  });
}
