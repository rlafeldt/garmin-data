import { z } from "zod";

/**
 * Step 4: Training Context & Sleep
 *
 * Periodisation context, circadian alignment, and sleep data for
 * interpreting daily HRV, VO2, and training load.
 *
 * Required: current_training_phase, chronotype
 * All other fields optional.
 */
export const step4Schema = z.object({
  // Required fields
  current_training_phase: z.enum([
    "off_season",
    "base_aerobic",
    "build_race_specific",
    "peak_competition",
    "taper",
    "recovery_deload",
    "rehabilitation",
    "no_structured_training",
  ]),

  chronotype: z.enum([
    "definite_morning",
    "moderate_morning",
    "intermediate",
    "moderate_evening",
    "definite_evening",
  ]),

  // Optional fields
  next_race_event: z
    .string()
    .max(200, "Maximum 200 characters")
    .optional(),

  typical_training_time: z
    .enum([
      "early_morning",
      "mid_morning",
      "midday",
      "afternoon",
      "evening",
      "night",
      "varies",
    ])
    .optional(),

  sleep_schedule_consistency: z
    .enum([
      "very_consistent",
      "mostly",
      "social_jetlag_1_2h",
      "significant_jetlag_2h_plus",
      "highly_irregular",
    ])
    .optional(),

  average_sleep_duration: z
    .enum([
      "under_5h",
      "5_6h",
      "6_7h",
      "7_8h",
      "8_9h",
      "over_9h",
    ])
    .optional(),

  screen_blue_light: z
    .enum([
      "no_screens_after_8pm",
      "screens_stop_1h_before",
      "30min_before",
      "in_bed_until_sleep",
      "blue_light_glasses",
    ])
    .optional(),

  subjective_recovery_waking: z
    .number()
    .int()
    .min(1)
    .max(5)
    .optional(),

  perceived_cognitive_fatigue: z
    .enum([
      "rarely",
      "occasional_afternoon_dip",
      "regular_brain_fog",
      "chronic",
    ])
    .optional(),

  preferred_insight_delivery_time: z
    .enum([
      "morning",
      "post_workout",
      "evening",
      "flexible",
    ])
    .optional(),
});

export type Step4Data = z.infer<typeof step4Schema>;
