import { z } from "zod";

/**
 * Step 3: Metabolic & Nutrition Profile
 *
 * Assesses metabolic flexibility -- capacity to switch between fat and
 * glucose oxidation. Covers dietary pattern, meal timing, hydration,
 * stimulants, and food sensitivities.
 *
 * Required: dietary_pattern, pre_training_nutrition
 * All other fields optional.
 */
export const step3Schema = z.object({
  // Required fields
  dietary_pattern: z.enum([
    "omnivore",
    "ketogenic",
    "low_carb_lchf",
    "mediterranean",
    "paleo_ancestral",
    "carnivore_animal_based",
    "plant_based_vegan",
    "cyclic",
  ]),

  pre_training_nutrition: z.enum([
    "fully_fasted",
    "coffee_only",
    "light_carbs",
    "full_meal_with_carbs",
    "protein_only",
    "mixed_meal",
    "varies_by_session",
  ]),

  // Optional fields
  primary_carb_sources: z
    .array(
      z.enum([
        "fruit",
        "root_vegetables",
        "legumes_lentils",
        "white_rice_potato",
        "whole_grains",
        "refined_grains",
        "ultra_processed_food",
        "sugar_sweetened_drinks",
        "avoids_most_carbs",
      ])
    )
    .optional(),

  metabolic_flexibility_signals: z
    .object({
      energy_crash: z
        .enum(["never", "occasionally", "often", "always"])
        .optional(),
      hunger_irritability: z
        .enum(["never", "occasionally", "often", "always"])
        .optional(),
      fasted_training: z
        .enum(["never_tried", "cannot", "with_difficulty", "easily"])
        .optional(),
      carb_cravings: z
        .enum(["never", "occasionally", "often", "always"])
        .optional(),
      energy_consistency: z
        .enum([
          "always_consistent",
          "mostly",
          "variable",
          "significant_crashes",
        ])
        .optional(),
    })
    .optional(),

  eating_window: z
    .enum([
      "no_fasting",
      "twelve_twelve",
      "sixteen_eight",
      "eighteen_six",
      "twenty_four",
      "omad",
      "multi_day",
      "variable",
    ])
    .optional(),

  estimated_daily_calories: z
    .enum([
      "under_1500",
      "1500_2000",
      "2000_2500",
      "2500_3000",
      "3000_3500",
      "over_3500",
      "dont_track",
    ])
    .optional(),

  protein_intake_emphasis: z
    .enum([
      "very_low",
      "low",
      "moderate",
      "high",
      "very_high",
    ])
    .optional(),

  time_meal_to_training: z
    .enum([
      "fasted_8h_plus",
      "under_30min",
      "30_60min",
      "1_2h",
      "2_3h",
      "3h_plus",
      "varies",
    ])
    .optional(),

  intra_training_fuelling: z
    .enum([
      "water_only",
      "electrolytes",
      "gels_sports_drink",
      "whole_food",
      "nothing_under_60min",
    ])
    .optional(),

  post_workout_nutrition_window: z
    .enum([
      "within_30min",
      "30_60min",
      "1_2h",
      "2h_plus",
      "extend_fast",
    ])
    .optional(),

  daily_water_intake: z
    .enum([
      "under_1_5l",
      "1_5_2_5l",
      "2_5_3_5l",
      "over_3_5l",
    ])
    .optional(),

  pre_training_stimulants: z
    .array(
      z.enum([
        "black_coffee",
        "espresso",
        "caffeine_pill",
        "pre_workout",
        "energy_drink",
        "yerba_mate_green_tea",
        "beta_alanine",
        "citrulline_arginine",
        "none",
      ])
    )
    .optional(),

  daily_caffeine_intake: z
    .enum([
      "none",
      "low",
      "moderate",
      "high",
      "very_high",
    ])
    .optional(),

  caffeine_cutoff_time: z
    .enum([
      "no_caffeine",
      "before_10am",
      "before_noon",
      "before_2pm",
      "afternoon",
      "evening",
    ])
    .optional(),

  alcohol_consumption: z
    .enum([
      "none",
      "occasional",
      "moderate",
      "regular",
    ])
    .optional(),

  food_sensitivities: z
    .array(
      z.enum([
        "none",
        "gluten_wheat",
        "lactose_dairy",
        "fructose",
        "fodmap",
        "histamine_intolerance",
        "multiple",
      ])
    )
    .optional(),
});

export type Step3Data = z.infer<typeof step3Schema>;
