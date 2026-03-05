import { z } from "zod";

/**
 * Step 2: Health, Medications & Supplementation
 *
 * Contextualises biometric data, flags relevant interactions,
 * applies condition-specific evidence.
 *
 * All fields optional.
 */

const supplementCategorySchema = z.array(z.string()).default([]);

export const step2Schema = z.object({
  health_conditions: z
    .array(
      z.enum([
        "type_2_diabetes",
        "hypertension",
        "hypothyroidism",
        "hyperthyroidism",
        "insulin_resistance",
        "pcos",
        "sleep_apnea",
        "cardiovascular_disease",
        "autoimmune_condition",
        "anxiety_depression",
        "gut_digestive_issues",
        "none",
      ])
    )
    .optional(),

  injury_history_text: z.string().optional(),

  current_medications: z.string().optional(),

  smoking_status: z
    .enum([
      "non_smoker",
      "former_smoker",
      "current_smoker",
      "vaping_e_cigarettes",
    ])
    .optional(),

  recovery_modalities: z
    .array(
      z.enum([
        "cold_exposure_ice_bath",
        "sauna",
        "contrast_therapy",
        "massage_soft_tissue",
        "red_light_therapy",
        "none",
        "other",
      ])
    )
    .optional(),

  // Categorised supplement selection across 8 groups
  supplements: z
    .object({
      foundational: supplementCategorySchema,
      performance_recovery: supplementCategorySchema,
      hormonal_metabolic: supplementCategorySchema,
      longevity_cellular: supplementCategorySchema,
      cognitive_neurological: supplementCategorySchema,
      gut_immune: supplementCategorySchema,
      sleep_stress: supplementCategorySchema,
      ketogenic_metabolic: supplementCategorySchema,
    })
    .optional(),

  other_supplements_text: z.string().optional(),

  no_supplements: z.boolean().optional(),
});

export type Step2Data = z.infer<typeof step2Schema>;
