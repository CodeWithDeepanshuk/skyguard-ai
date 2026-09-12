import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

export interface GateItem {
  key: string;
  name: string;
  category: 'Integrity & Data Safety' | 'Incident & Detection Performance' | 'Weather & Coherence' | 'Drift & Specialized Recall' | 'Root Cause & Calibration';
  threshold: string;
  actual_status: boolean;
  status_label: 'PASS' | 'FAIL';
  description: string;
}

export async function GET() {
  const root = process.cwd();
  const file11 = path.join(root, 'iteration 11 result', 'iteration11_result_block.json');
  const file10 = path.join(root, 'iteration 10 result', 'iteration10_result_block (1).json');

  let rawData = null;
  if (fs.existsSync(file11)) {
    try {
      rawData = JSON.parse(fs.readFileSync(file11, 'utf-8'));
    } catch {
      // Fallback
    }
  }
  if (!rawData && fs.existsSync(file10)) {
    try {
      rawData = JSON.parse(fs.readFileSync(file10, 'utf-8'));
    } catch {
      // Fallback
    }
  }

  const rawGates: Record<string, boolean> = rawData?.promotion_gates || {};

  const gateDefinitions: Array<Omit<GateItem, 'actual_status' | 'status_label'>> = [
    {
      key: 'calibration_development_safety_pass',
      name: 'Calibration Safety Audit',
      category: 'Integrity & Data Safety',
      threshold: 'Zero post-event leakage & monotonic temperature reliability',
      description: 'Ensures probability calibrators are strictly fit on pre-event development data.'
    },
    {
      key: 'eligible_policy_found',
      name: 'Eligible Operational Policy',
      category: 'Integrity & Data Safety',
      threshold: 'Operating threshold candidates >= 1',
      description: 'Requires at least one operating policy meeting all strict precision thresholds.'
    },
    {
      key: 'india_and_dwd_holdout_rows_nonzero',
      name: 'Independent Holdout Integrity',
      category: 'Integrity & Data Safety',
      threshold: 'Validation rows > 0 across all geographic holdouts',
      description: 'Verifies holdout sets represent genuine independent test partitions.'
    },
    {
      key: 'holdouts_absent_from_training',
      name: 'Station Holdout Exclusion Check',
      category: 'Integrity & Data Safety',
      threshold: 'Zero training contamination from holdout stations',
      description: 'Guarantees that unseen stations were never seen during gradient boosting fitting.'
    },
    {
      key: 'locked_2024_2025_unopened',
      name: 'Evaluation Vault Sealed Receipt',
      category: 'Integrity & Data Safety',
      threshold: 'Cryptographic hash lock active',
      description: 'Confirms that locked test years remain untouched during iterative development.'
    },
    {
      key: 'three_fresh_seed_runs_present',
      name: 'Multi-Seed Repeatability',
      category: 'Integrity & Data Safety',
      threshold: '3 seeds completed (111, 222, 333)',
      description: 'Verifies algorithmic stability across different random seeds.'
    },
    {
      key: 'incident_fault_precision_gte_0_80_every_domain_and_holdout',
      name: 'Incident Fault Precision',
      category: 'Incident & Detection Performance',
      threshold: 'Precision >= 80% across all domains',
      description: 'Guarantees that confirmed operational fault alerts are at least 80% genuine.'
    },
    {
      key: 'incident_fault_f1_gte_0_70',
      name: 'Incident-Level Macro F1',
      category: 'Incident & Detection Performance',
      threshold: 'Incident F1 >= 70%',
      description: 'Harmonic mean of incident detection precision and episode recall.'
    },
    {
      key: 'false_alerts_per_station_day_lte_0_02_every_domain_and_holdout',
      name: 'False Alert Budget',
      category: 'Incident & Detection Performance',
      threshold: '<= 0.02 false alerts / station-day (max 1 per 50 days)',
      description: 'Operational noise budget to prevent field engineer alert fatigue.'
    },
    {
      key: 'no_primary_incident_f1_regression_vs_best_retained',
      name: 'Non-Regression in Incident F1',
      category: 'Incident & Detection Performance',
      threshold: 'Delta F1 >= 0.0% vs Phase 10 baseline',
      description: 'Prevents promoting candidates that regress on incident-level detection.'
    },
    {
      key: 'no_primary_point_f1_regression_vs_best_retained',
      name: 'Non-Regression in Point F1',
      category: 'Incident & Detection Performance',
      threshold: 'Delta Point F1 >= 0.0% vs Phase 10 baseline',
      description: 'Guarantees point-wise observation accuracy is preserved.'
    },
    {
      key: 'fault_episode_recall_gte_0_70',
      name: 'General Fault Episode Recall',
      category: 'Drift & Specialized Recall',
      threshold: 'Recall >= 70% across all 18 fault types',
      description: 'Proportion of persistent physical sensor failures successfully flagged.'
    },
    {
      key: 'drift_episode_recall_gte_0_50',
      name: 'Slow Calibration Drift Recall',
      category: 'Drift & Specialized Recall',
      threshold: 'CUSUM drift recall >= 50%',
      description: 'Flags slow transducer wear before complete sensor failure.'
    },
    {
      key: 'frozen_episode_recall_gte_0_80',
      name: 'Integer-Aware Freeze Recall',
      category: 'Drift & Specialized Recall',
      threshold: 'Flatline freeze recall >= 80%',
      description: 'Detects stuck values while accounting for quantization resolutions.'
    },
    {
      key: 'communication_mean_recall_gte_0_80',
      name: 'Data Corruption & Transport Recall',
      category: 'Drift & Specialized Recall',
      threshold: 'Communication error recall >= 80%',
      description: 'Identifies malformed telemetry packets and CRC failures.'
    },
    {
      key: 'weak_fault_mean_recall_gte_0_60',
      name: 'Low-Magnitude Fault Recall',
      category: 'Drift & Specialized Recall',
      threshold: 'Weak fault recall >= 60%',
      description: 'Detects subtle deviations within 1.5-2.5 standard deviations.'
    },
    {
      key: 'india_and_dwd_weather_incident_f1_gte_0_75',
      name: 'Weather Incident Preservation F1',
      category: 'Weather & Coherence',
      threshold: 'Weather Event F1 >= 75%',
      description: 'Preserves extreme frontal passages without raising false hardware alarms.'
    },
    {
      key: 'worst_supported_cluster_weather_f1_gte_0_65',
      name: 'Regional Cluster Robustness',
      category: 'Weather & Coherence',
      threshold: 'Lowest climate-zone weather F1 >= 65%',
      description: 'Ensures spatial veto performs across all 8 Indian climate zones.'
    },
    {
      key: 'fault_to_weather_rate_lte_0_01_every_domain_and_holdout',
      name: 'Fault Misclassified as Weather',
      category: 'Weather & Coherence',
      threshold: 'Confusion Rate <= 1.0%',
      description: 'Prevents broken sensors from being mistakenly excused as weather.'
    },
    {
      key: 'root_cause_accuracy_gte_0_80',
      name: 'Root-Cause Diagnosis Accuracy',
      category: 'Root Cause & Calibration',
      threshold: 'Classification Accuracy >= 80%',
      description: 'Accurately attributes fault to Spike, Drift, Freeze, or Bias.'
    },
    {
      key: 'root_cause_macro_f1_gte_0_70',
      name: 'Root-Cause Macro F1',
      category: 'Root Cause & Calibration',
      threshold: 'Macro F1 >= 70% across 12 fault classes',
      description: 'Balanced diagnosis across frequent and rare failure modes.'
    },
    {
      key: 'fault_ece_lte_0_08',
      name: 'Fault Probability Calibration ECE',
      category: 'Root Cause & Calibration',
      threshold: 'Expected Calibration Error <= 0.08',
      description: 'Ensures predicted fault probability reflects real-world empirical frequency.'
    },
    {
      key: 'weather_ece_lte_0_08',
      name: 'Weather Probability Calibration ECE',
      category: 'Root Cause & Calibration',
      threshold: 'Expected Calibration Error <= 0.08',
      description: 'Ensures genuine weather confidence values are mathematically trustworthy.'
    },
    {
      key: 'median_fault_detection_latency_lte_180_minutes',
      name: 'Operational Detection Latency',
      category: 'Incident & Detection Performance',
      threshold: 'Median Detection Latency <= 180 min (6 observations)',
      description: 'Time from physical transducer degradation to engineer alert dispatch.'
    },
    {
      key: 'every_seed_precision_and_false_alarm_pass',
      name: 'Global Multi-Seed Constraint Pass',
      category: 'Integrity & Data Safety',
      threshold: 'Zero constraint violations across all seeds',
      description: 'Confirms stability under random model re-initialization.'
    }
  ];

  const gates: GateItem[] = gateDefinitions.map(def => {
    const passed = rawGates[def.key] === true;
    return {
      ...def,
      actual_status: passed,
      status_label: passed ? 'PASS' : 'FAIL'
    };
  });

  const passedCount = gates.filter(g => g.actual_status).length;
  const totalCount = gates.length;

  return NextResponse.json({
    iteration: rawData?.iteration || '11_all_india_incident_engine',
    summary: {
      passed_gates: passedCount,
      total_gates: totalCount,
      passed_percentage: +((passedCount / totalCount) * 100).toFixed(1),
      status: rawData?.status || 'shadow_deployment_active',
      device: rawData?.device || 'Tesla T4 / AMD64',
    },
    gates
  });
}
