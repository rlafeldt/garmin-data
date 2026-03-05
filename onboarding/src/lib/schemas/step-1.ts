import { z } from "zod";

/**
 * Step 1: Biological Profile
 *
 * Core biometric data used to calibrate all AI interpretations and establish
 * individual physiological baseline.
 *
 * Required: age, biological_sex, height_cm, weight_kg, primary_sport
 * Optional: occupational_activity_level, hormonal_status (ONBD-08),
 *           cycle_phase (ONBD-08), weekly_training_volume_hours,
 *           primary_goals, perceived_stress_level
 */
export const step1Schema = z.object({
  // Required fields
  age: z
    .number()
    .int()
    .min(16, "Must be at least 16 years old")
    .max(120, "Must be at most 120 years old"),

  biological_sex: z.enum(["male", "female", "prefer_not_to_say"]),

  height_cm: z
    .number()
    .int()
    .min(100, "Height must be at least 100 cm")
    .max(250, "Height must be at most 250 cm"),

  weight_kg: z
    .number()
    .min(30, "Weight must be at least 30 kg")
    .max(300, "Weight must be at most 300 kg"),

  primary_sport: z.enum([
    "running",
    "cycling",
    "triathlon",
    "swimming",
    "strength_training",
    "crossfit_hiit",
    "team_sports",
    "hiking_trail",
    "mixed_general_fitness",
    "other",
  ]),

  // Optional fields
  occupational_activity_level: z
    .enum(["sedentary", "light", "moderate", "active", "very_active"])
    .optional(),

  // Female athletes -- Hormonal context (ONBD-08)
  hormonal_status: z
    .enum([
      "regular_tracking",
      "regular_not_tracking",
      "irregular",
      "perimenopause",
      "post_menopause",
      "hormonal_contraception",
      "hrt",
      "prefer_not_to_say",
    ])
    .optional(),

  cycle_phase: z
    .enum([
      "menstrual",
      "follicular",
      "ovulatory",
      "luteal",
      "not_applicable",
    ])
    .optional(),

  weekly_training_volume_hours: z
    .number()
    .min(0)
    .max(25)
    .optional(),

  primary_goals: z
    .array(
      z.enum([
        "performance",
        "recovery",
        "metabolic_flexibility",
        "body_composition",
        "longevity",
        "sleep_quality",
        "stress_resilience",
        "injury_prevention",
        "cognitive_performance",
      ])
    )
    .optional(),

  perceived_stress_level: z
    .number()
    .int()
    .min(1)
    .max(5)
    .optional(),
});

export type Step1Data = z.infer<typeof step1Schema>;
