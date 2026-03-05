/**
 * TypeScript interfaces matching the Supabase onboarding schema.
 * These types represent the database row shapes for direct Supabase queries.
 */

export interface OnboardingProfile {
  id: string;

  // Step completion tracking
  step_1_complete: boolean;
  step_2_complete: boolean;
  step_3_complete: boolean;
  step_4_complete: boolean;
  step_5_complete: boolean;
  step_6_complete: boolean;
  onboarding_complete: boolean;

  // Step data as JSONB
  step_1_data: Record<string, unknown>;
  step_2_data: Record<string, unknown>;
  step_3_data: Record<string, unknown>;
  step_4_data: Record<string, unknown>;
  step_5_data: Record<string, unknown>;
  step_6_data: Record<string, unknown>;

  // Timestamps
  created_at: string;
  updated_at: string;
}

export interface LabResult {
  id: string;
  profile_id: string;
  upload_date: string;
  file_path: string;
  file_type: string;
  extraction_status: "pending" | "extracted" | "confirmed";
  extracted_values: ExtractedLabValue[];
  confirmed_values: ExtractedLabValue[];
  created_at: string;
}

export interface ExtractedLabValue {
  marker_name: string;
  value: number | null;
  unit: string;
  reference_range: string | null;
  confidence: number;
}

export interface ConsentRecord {
  id: string;
  profile_id: string;
  consent_type: "ai_disclaimer" | "data_processing" | "clinical_evaluation";
  consented: boolean;
  consented_at: string;
  consent_text: string;
}

export interface CompletenessResult {
  percentage: number;
  completedSteps: number;
  totalSteps: number;
  incompleteSteps: number[];
  suggestedNextStep: number | null;
}
