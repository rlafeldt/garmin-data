import { z } from "zod";

/**
 * Step 5: Baseline Biometric Metrics
 *
 * 30-day averages from Garmin Connect establishing personal normal --
 * the reference frame for daily deviation assessment.
 *
 * All fields optional. AI establishes baseline from first 7 days if blank.
 */
export const step5Schema = z.object({
  hrv_rmssd: z
    .number()
    .min(0, "HRV must be at least 0 ms")
    .max(300, "HRV must be at most 300 ms")
    .optional(),

  resting_hr: z
    .number()
    .min(30, "Resting HR must be at least 30 bpm")
    .max(120, "Resting HR must be at most 120 bpm")
    .optional(),

  vo2_max: z
    .number()
    .min(15, "VO2 Max must be at least 15 ml/kg/min")
    .max(90, "VO2 Max must be at most 90 ml/kg/min")
    .optional(),

  spo2_avg: z
    .number()
    .min(80, "SpO2 must be at least 80%")
    .max(100, "SpO2 must be at most 100%")
    .optional(),

  respiration_rate_sleep: z
    .number()
    .min(5, "Respiration rate must be at least 5 brpm")
    .max(30, "Respiration rate must be at most 30 brpm")
    .optional(),

  body_battery_morning: z
    .number()
    .int()
    .min(0, "Body Battery must be at least 0")
    .max(100, "Body Battery must be at most 100")
    .optional(),

  average_daily_steps: z
    .number()
    .int()
    .min(0, "Steps must be at least 0")
    .max(50000, "Steps must be at most 50,000")
    .optional(),

  sleep_score_avg: z
    .number()
    .int()
    .min(0, "Sleep score must be at least 0")
    .max(100, "Sleep score must be at most 100")
    .optional(),

  garmin_training_status: z
    .enum([
      "unproductive",
      "maintaining",
      "productive",
      "peaking",
      "overreaching",
      "recovery",
      "detraining",
      "no_status",
      "not_sure",
    ])
    .optional(),
});

export type Step5Data = z.infer<typeof step5Schema>;
