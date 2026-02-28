/**
 * TypeScript types mirroring backend Pydantic schemas.
 *
 * Every interface here matches a backend schema in schemas.py.
 * When the backend changes, update here first — TypeScript will
 * flag every place in the app that needs to adapt.
 */

// ---------------------------------------------------------------------------
// Enums (string literal unions — more idiomatic than TS enums in RN)
// ---------------------------------------------------------------------------

export type EntryType = "exercise_card" | "observation_card";
export type ProcessingStatus = "pending" | "processing" | "completed" | "failed";
export type WeightUnit = "kg" | "lbs";
export type RiskLevel = "low" | "medium" | "high";
export type MessageRole = "user" | "assistant";
export type Tier = "free" | "pro" | "trainer_pro";

// ---------------------------------------------------------------------------
// Generic API wrappers
// ---------------------------------------------------------------------------

export interface PaginationMeta {
  cursor: string | null;
  limit: number;
  has_more: boolean;
}

export interface DataResponse<T> {
  data: T;
  meta: Record<string, unknown>;
}

export interface ListResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

export interface ErrorDetail {
  code: string;
  message: string;
}

export interface ErrorResponse {
  error: ErrorDetail;
}

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

export interface Client {
  id: string;
  trainer_id: string;
  name: string;
  email: string | null;
  phone: string | null;
  birth_date: string | null;
  training_start_date: string | null;
  goals: string[] | null;
  injury_history: string | null;
  preferred_weight_unit: WeightUnit | null;
  archived: boolean;
  created_at: string;
}

export interface ClientCreate {
  name: string;
  email?: string;
  phone?: string;
  birth_date?: string;
  training_start_date?: string;
  goals?: string[];
  injury_history?: string;
  preferred_weight_unit?: WeightUnit;
}

export interface ClientUpdate {
  name?: string;
  email?: string;
  phone?: string;
  birth_date?: string;
  training_start_date?: string;
  goals?: string[];
  injury_history?: string;
  preferred_weight_unit?: WeightUnit;
  archived?: boolean;
}

// ---------------------------------------------------------------------------
// Session
// ---------------------------------------------------------------------------

export interface Session {
  id: string;
  trainer_id: string;
  client_id: string;
  started_at: string;
  ended_at: string | null;
  scheduled_for: string | null;
  duration_minutes: number | null;
  audio_url: string | null;
  audio_duration_seconds: number | null;
  raw_transcript: string | null;
  processing_status: ProcessingStatus;
  trainer_edited: boolean;
  plan_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface SessionCreate {
  client_id: string;
  started_at: string;
  scheduled_for?: string;
  plan_id?: string;
}

export interface SessionUpdate {
  ended_at?: string;
  scheduled_for?: string;
  duration_minutes?: number;
  raw_transcript?: string;
  processing_status?: ProcessingStatus;
  trainer_edited?: boolean;
  plan_id?: string;
}

// ---------------------------------------------------------------------------
// Session Entry
// ---------------------------------------------------------------------------

/**
 * Set data stored as JSONB — no enforced schema at DB level.
 *
 * Two producers write this data with slightly different keys:
 *   Seed data:      { set: 1, weight_kg: 80, reps: 8, rpe: 7 }
 *   Voice pipeline:  { reps: 8, weight: 80, weight_unit: "kg", rpe: 7 }
 *
 * Frontend must handle both formats gracefully.
 */
export interface SetData {
  set?: number;
  reps: number | null;
  weight_kg?: number | null;
  weight?: number | null;
  weight_unit?: string | null;
  rpe: number | null;
  rir?: number | null;
  notes?: string | null;
  duration_seconds?: number | null;
  equipment_note?: string | null;
  [key: string]: unknown;
}

export interface SessionEntry {
  id: string;
  session_id: string;
  client_id: string;
  entry_type: EntryType;
  sequence_order: number;
  exercise_name: string | null;
  exercise_canonical: string | null;
  sets: SetData[] | null;
  total_volume_kg: number | null;
  form_notes: string[] | null;
  cues_given: string[] | null;
  cue_effectiveness: Record<string, unknown> | null;
  observation_text: string | null;
  attached_to_set: number | null;
  flag_color: string | null;
  flag_reason: string | null;
  performed_at: string | null;
  created_at: string;
}

export interface SessionEntryCreate {
  entry_type: EntryType;
  sequence_order?: number;
  exercise_name?: string;
  exercise_canonical?: string;
  sets?: SetData[];
  total_volume_kg?: number;
  form_notes?: string[];
  cues_given?: string[];
  cue_effectiveness?: Record<string, unknown>;
  observation_text?: string;
  attached_to_set?: number;
  flag_color?: string;
  flag_reason?: string;
  performed_at?: string;
}

export interface SessionEntryUpdate {
  entry_type?: EntryType;
  sequence_order?: number;
  exercise_name?: string;
  exercise_canonical?: string;
  sets?: SetData[];
  total_volume_kg?: number;
  form_notes?: string[];
  cues_given?: string[];
  cue_effectiveness?: Record<string, unknown>;
  observation_text?: string | null;
  attached_to_set?: number;
  flag_color?: string | null;
  flag_reason?: string | null;
  performed_at?: string;
}

// ---------------------------------------------------------------------------
// Session Plan
// ---------------------------------------------------------------------------

export interface SessionPlan {
  id: string;
  client_id: string;
  trainer_id: string;
  plan_text: string;
  planned_for_date: string | null;
  created_at: string;
}

export interface SessionPlanCreate {
  client_id: string;
  plan_text: string;
  planned_for_date?: string;
}

export interface SessionPlanUpdate {
  plan_text?: string;
  planned_for_date?: string;
}

// ---------------------------------------------------------------------------
// Injury Flag
// ---------------------------------------------------------------------------

export interface InjuryFlag {
  id: string;
  client_id: string;
  session_id: string;
  session_entry_id: string | null;
  body_part: string;
  pain_level: number;
  description: string | null;
  first_occurrence: string | null;
  last_occurrence: string | null;
  occurrence_count: number;
  resolved: boolean;
  resolved_at: string | null;
  flagged_at: string;
}

// ---------------------------------------------------------------------------
// Workout Classification
// ---------------------------------------------------------------------------

export interface WorkoutClassification {
  workout_type: string;
}

// ---------------------------------------------------------------------------
// Voice Processing
// ---------------------------------------------------------------------------

export interface TimingBreakdown {
  transcription_ms: number;
  parsing_ms: number;
  validation_ms: number;
  persistence_ms: number;
  total_ms: number;
}

export interface ClarificationItem {
  observation_text: string;
  flag_reason: string | null;
}

export interface ValidationWarning {
  field: string;
  code: string;
  message: string;
}

export interface TranscribeResponse {
  transcript: string;
  confidence: number;
}

export interface VoiceClipResponse {
  entries_created: SessionEntry[];
  entries_modified: SessionEntry[];
  clarifications_needed: ClarificationItem[];
  warnings: ValidationWarning[];
  transcript: string;
  confidence: number;
  timing: TimingBreakdown;
}

// ---------------------------------------------------------------------------
// Exercise
// ---------------------------------------------------------------------------

export interface Exercise {
  id: string;
  canonical_name: string;
  aliases: string[] | null;
  category: string | null;
  primary_muscles: string[] | null;
  equipment: string[] | null;
  difficulty: string | null;
  common_errors: Record<string, unknown> | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Client Analysis (Phase 3+)
// ---------------------------------------------------------------------------

export interface ClientAnalysis {
  id: string;
  client_id: string;
  total_sessions: number;
  last_session_date: string | null;
  avg_weight_increase_pct_per_week: number | null;
  current_volume_trend: string | null;
  injury_risk_score: number | null;
  injury_risk_level: RiskLevel | null;
  risk_factors: string[] | null;
  form_degradation_detected: boolean;
  overtraining_indicators: boolean;
  pain_pattern_detected: boolean;
  client_score: number | null;
  client_score_breakdown: Record<string, unknown> | null;
  last_computed_at: string | null;
}

// ---------------------------------------------------------------------------
// Brain (Phase 3+)
// ---------------------------------------------------------------------------

export interface BrainConversation {
  id: string;
  trainer_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface BrainMessage {
  id: string;
  conversation_id: string;
  trainer_id: string;
  role: MessageRole;
  content: string;
  created_at: string;
}
