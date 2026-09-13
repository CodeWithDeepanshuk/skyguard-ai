import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

function readJson(file: string): any | null {
  if (!fs.existsSync(file)) return null;
  try {
    return JSON.parse(fs.readFileSync(file, 'utf-8'));
  } catch {
    return null;
  }
}

export async function GET() {
  const root = process.cwd();
  const phase10Path = path.join(root, 'reports', 'phase10_final.json');
  const qcPath = path.join(root, 'reports', 'qc_baseline.json');
  const candidatePath = path.join(root, 'reports', 'final_evaluation', 'final_result_block.json');
  const phase10 = readJson(phase10Path);
  const qc = readJson(qcPath);

  if (!phase10) {
    return NextResponse.json({
      status: 'unavailable',
      benchmark: null,
      message: 'The verified offline benchmark artifact is not available in this deployment.',
    }, { status: 503 });
  }

  const timeTest = phase10?.evaluation?.time_test ?? null;
  const stationTest = phase10?.evaluation?.station_test ?? null;
  return NextResponse.json({
    status: 'success',
    generated_at_utc: new Date().toISOString(),
    benchmark: {
      model_version: phase10.model_version ?? null,
      phase: phase10.phase ?? null,
      feature_count: phase10.feature_count ?? null,
      input_parameters: phase10?.policy?.input_contract ?? null,
      dew_point_used_by_detector: phase10?.policy?.dew_point_used_by_detector ?? null,
      deployment_role: 'verified_offline_research_baseline',
      claim_scope: 'Fault-injected offline benchmark; these metrics are not live-field accuracy.',
      live_fault_labels_available: false,
      promoted_to_live_certified_model: false,
      tcn_role: phase10?.policy?.tcn_role ?? null,
      evaluation: {
        time_test: {
          rows: timeTest?.rows ?? null,
          binary_fault_detection: timeTest?.binary_fault_detection ?? null,
          event_decision: timeTest?.event_decision ?? null,
          oracle_root_cause: timeTest?.oracle_root_cause ?? null,
        },
        station_test: {
          rows: stationTest?.rows ?? null,
          binary_fault_detection: stationTest?.binary_fault_detection ?? null,
          event_decision: stationTest?.event_decision ?? null,
          oracle_root_cause: stationTest?.oracle_root_cause ?? null,
        },
      },
      quality_control: qc ? {
        report_type: qc.report_type ?? null,
        total_observations: qc.observations ?? null,
        total_alerts: qc.alerts ?? null,
        alerts_per_1000: qc.alerts_per_1000_observations ?? null,
        observations_per_second: qc.observations_per_second ?? null,
        alerts_by_rule: qc.alerts_by_rule ?? null,
        alerts_by_sensor: qc.alerts_by_sensor ?? null,
        warning: qc.warning ?? null,
      } : null,
      evidence_artifacts: [
        'reports/phase10_final.json',
        ...(qc ? ['reports/qc_baseline.json'] : []),
      ],
      excluded_candidate_artifact: fs.existsSync(candidatePath) ? {
        path: 'reports/final_evaluation/final_result_block.json',
        reason: 'Candidate promotion artifact is excluded from public metrics until its generation is reproducible and independently verified.',
      } : null,
    },
  });
}
