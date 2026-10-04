export type ClassicModelId = 'NCUM' | 'WRF' | 'GFS' | 'AI_WEATHER';
/** Classic NWP/AI slots plus the public live models (Open-Meteo): ECMWF IFS, UK Met Office UM, DWD ICON. */
export type ModelId = ClassicModelId | 'ECMWF_IFS' | 'UKMO_UM' | 'ICON';

export type WeatherRegime = 'NORMAL' | 'HEAVY_RAINFALL' | 'CONVECTIVE' | 'TRANSITION_UNCERTAIN';

export type LeadHours = 24 | 48 | 72;

export type VariableType = 'rainfall' | 'temperature' | 'wind_speed';

export type UserRole = 'FORECASTER' | 'OPERATIONS' | 'MODEL_ANALYST' | 'ADMIN' | 'AUDITOR';

export type SourceMode = 'SYNTHETIC_DEMO' | 'LIVE_PUBLIC_MODELS' | 'STORED_DATA' | 'INDIA_OPERATIONAL' | 'INDIA_OPERATIONAL_PLUS_GLOBAL';
export type DataSourcePref = 'auto' | 'live' | 'database' | 'demo';

export type DataMode = 'LIVE' | 'DEMO' | 'UNAVAILABLE';

export type EvidenceStatus = 
  | 'DATABASE_VERIFIED' 
  | 'COLD_START' 
  | 'BOOTSTRAP_PRIOR' 
  | 'SYNTHETIC_REFERENCE' 
  | 'UNAVAILABLE';

export type VerificationStatus = 
  | 'VERIFIED' 
  | 'NOT_VERIFIED' 
  | 'SYNTHETIC_BENCHMARK' 
  | 'UNAVAILABLE';

export type SourceStatus = 
  | 'ACTIVE' 
  | 'DEGRADED' 
  | 'DISABLED' 
  | 'UNAVAILABLE' 
  | 'DEMO_SIMULATED';

export type ProvenanceType = 
  | 'LIVE_CONNECTED'
  | 'PUBLIC_SOURCE'
  | 'AUTHORIZED_PROVIDER'
  | 'SYNTHETIC_STRESS_TEST'
  | 'CONTROLLED_SYNTHETIC_BENCHMARK'
  | 'BOOTSTRAP_PRIOR'
  | 'DATABASE_VERIFIED'
  | 'NOT_VERIFIED'
  | 'UNAVAILABLE'
  | 'PHYSICS_INFORMED_HEURISTIC'
  | 'ENGINEERING_FIXTURE'
  | 'AUTHORIZED_ACCESS_REQUIRED'
  | 'DERIVED_DATA';

export interface DataSourceStatus {
  backendConnected: boolean;
  provenance: string;
  lastUpdated: string;
  warning?: string;
  dataMode: DataMode;
}

export interface ModelWeight {
  model_id: ModelId;
  weight: number;
  raw_forecast: number;
  historical_mae: number;
  recent_bias?: number;
  confidence_contribution?: number;
  status: 'ACTIVE' | 'DEGRADED' | 'DISABLED' | 'UNAVAILABLE';
  evidence_status?: EvidenceStatus;
  notes?: string[];
}

export interface DisagreementInfo {
  disagreement_level: 'LOW' | 'MEDIUM' | 'HIGH';
  disagreement_score: number;
  forecast_spread: number;
  weighted_spread: number;
  range: number;
  variance: number;
}

export interface UncertaintyInfo {
  confidence: 'VERY_HIGH' | 'HIGH' | 'MEDIUM' | 'LOW';
  confidence_score: number;
  hazard_exceedance_indicator_pct?: number;
  probability?: number;
  uncertainty_margin: number;
  threshold: number;
  lower_bound?: number;
  upper_bound?: number;
  calibrated?: boolean;
}

export interface ExtremeGuidance {
  is_extreme: boolean;
  severity: 'YELLOW_WATCH' | 'ORANGE_ALERT' | 'RED_WARNING';
  action_guidance: string;
}

export interface ForecastExplanation {
  primary_driver: string;
  contributing_factors: string[];
  bias_penalties: string[];
  dominant_model: string;
  notes: string[];
}

export interface WhatChanged {
  fused_delta: number;
  probability_shift?: number;
  exceedance_indicator_shift?: number;
  confidence_change: string;
  disagreement_change: string;
  primary_driver: string;
  timeline?: Array<{
    time: string;
    event: string;
    detail: string;
    type: 'trust' | 'error' | 'disagreement' | 'fusion' | 'confidence';
  }>;
}

export interface DataHealthSummary {
  status: 'HEALTHY' | 'DEGRADED' | 'CRITICAL';
  available_sources: number;
  total_sources: number;
  missing_sources: string[];
  validation_errors: number;
  packet_flow_percent: number;
  stream_latency_ms: number;
}

export interface PipelineStage {
  name: string;
  status: 'PASS' | 'WARN' | 'FAIL' | 'NOT_RUN' | 'PENDING' | 'SKIPPED';
  details?: string;
}

/** One executed pipeline stage, as returned by the backend (`stage_trace`). */
export interface StageTraceItem {
  stage: number;
  key: string;
  name: string;
  status: 'PASS' | 'WARN' | 'FAIL' | 'PENDING' | 'SKIPPED';
  duration_ms: number;
  inputs: Record<string, any>;
  outputs: Record<string, any>;
  notes?: string;
}

export interface SourceMeta {
  source?: string;
  provenance?: string;
  dataset_id?: string;
  issue_time?: string;
  valid_time?: string;
  fetched_at?: string;
  url?: string;
  unit?: string;
  grid?: { lat?: number; lon?: number; resolution?: string };
}

/** Explainability record for every headline number (see backend build_lineage). */
export interface Lineage {
  computed_at?: string;
  model_forecasts?: Record<string, SourceMeta & { model: string; value: number | null }>;
  fused_value?: { value: number | null; unit?: string; formula: string; bias_correction?: Record<string, number>;
                  terms: Array<{ model: string; weight: number; value: number | null; product: number | null }> };
  simple_average?: { value: number | null; formula: string };
  static_blend?: { value: number | null; formula: string };
  weights?: Record<string, { value: number; strategy: string; formula: string; historical_mae?: number;
                             skill_provenance?: string; recent_error?: number; recent_error_provenance?: string;
                             predicted_error?: number; bias_correction?: number }>;
  disagreement?: Record<string, any>;
  confidence?: Record<string, any>;
  probability?: Record<string, any>;
  uncertainty_margin?: Record<string, any>;
  extreme_signal?: Record<string, any>;
}

export interface ForecastIntelligencePackage {
  cycle: {
    run_id: string;
    issue_time: string;
    valid_time: string;
    lead_hours: LeadHours;
    region_id: string;
    variable: VariableType;
    season: string;
    weather_regime: WeatherRegime;
  };
  provenance: {
    overall_status: string;
    source_type: string;
    dataset_ids: string[];
    model_sources: string[];
    observation_status: string;
    evidence_status: EvidenceStatus;
  };
  forecasts: Array<{
    model_id: ModelId;
    value: number | null;
    unit: string;
    status: SourceStatus;
    provenance: string;
  }>;
  trust: Array<{
    model_id: ModelId;
    weight: number;
    skill_evidence: number;
    recent_error_evidence: number;
    lead_time_evidence: number;
    regime_evidence: number;
    disagreement_penalty: number;
    availability: number;
    evidence_status: EvidenceStatus;
  }>;
  fusion: {
    fused_value: number;
    unit: string;
    strategy: string;
    baseline_comparisons: {
      simple_average: number;
      static_blend: number;
    };
  };
  disagreement: DisagreementInfo;
  uncertainty: UncertaintyInfo;
  extreme_signal: ExtremeGuidance;
  explanation: ForecastExplanation;
  verification: {
    status: VerificationStatus;
    observation_available: boolean;
    metrics?: Record<string, any>;
    sample_count: number;
    evaluation_window?: string;
    provenance: string;
  };
  data_health: DataHealthSummary;
  audit: {
    pipeline_stages: PipelineStage[];
    warnings: string[];
    failed_checks: string[];
  };
}

export interface DashboardSummary {
  active_cycle: string;
  region_id: string;
  variable: VariableType;
  lead_hours: LeadHours;
  weather_regime: WeatherRegime;
  season: string;
  fused_forecast: number;
  unit: string;
  baselines: {
    simple_average: number;
    static_blend: number;
  };
  model_forecasts: Partial<Record<ModelId, number | null>>;
  weights: ModelWeight[];
  disagreement: DisagreementInfo;
  uncertainty: UncertaintyInfo;
  extreme_guidance: ExtremeGuidance;
  explanation: ForecastExplanation;
  what_changed: WhatChanged;
  data_health: DataHealthSummary;
  provenance: string;
  data_mode?: DataMode;
  forecast_package?: ForecastIntelligencePackage;
  // Round-3 traceability fields
  source_mode?: SourceMode;
  source_note?: string;
  source_meta?: Record<string, SourceMeta>;
  dataset_ids?: string[];
  issue_time?: string | null;
  computed_at?: string;
  run_id?: string;
  models?: ModelId[];
  strategy?: string;
  strategy_note?: string;
  skill_provenance?: Record<string, string>;
  stage_trace?: StageTraceItem[];
  lineage?: Lineage;
  notification_id?: string | null;
  qc_state?: Record<string, 'ACCEPTED' | 'WARNING' | 'REJECTED' | 'QUARANTINED' | 'MISSING'>;
  qc_flags?: Record<string, string[]>;
  fused_value?: number;
  confidence_score?: number;
}

export interface IndianSubdivision {
  id: string;
  name: string;
  state: string;
  terrain: string;
  climatic_zone: string;
  risk_profile: string;
  centroid: { lat: number; lon: number };
  bbox: [number, number, number, number];
  polygon?: number[][];
  dominant_model?: ModelId;
  trust_percentage?: number;
  weights?: Record<string, number>;
  disagreement_level?: 'LOW' | 'MEDIUM' | 'HIGH';
  rainfall_mm?: number;
  confidence?: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface FusionTrace {
  model_id: ModelId;
  assigned_weight: number;
  percentage: number;
  delta_from_previous: number;
  contributors: {
    regional_skill: number;
    recent_error: number;
    lead_reliability: number;
    weather_regime: number;
    disagreement_penalty: number;
    availability: number;
  };
  rationale: string;
  evidence_status?: EvidenceStatus;
}

export interface ExtremeEventItem {
  id: string;
  region: string;
  region_name: string;
  event: string;
  risk_signal: 'ELEVATED' | 'HIGH' | 'CRITICAL' | 'NORMAL';
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  forecast_window: string;
  model_consensus: string;
  model_disagreement: 'LOW' | 'MEDIUM' | 'HIGH';
  supporting_models: string[];
  contradicting_signal: string;
  varuna_interpretation: string;
}

export interface FailureMemoryRecord {
  model_id: ModelId;
  region_name: string;
  lead_hours: number;
  regime: WeatherRegime;
  signal: string;
  observed_pattern: string;
  trust_response: string;
  verification_history: string;
}

