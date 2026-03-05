"use client";

import { useStepForm } from "@/hooks/use-step-form";
import { step5Schema } from "@/lib/schemas/step-5";
import { FieldGroup } from "@/components/onboarding/field-group";
import { StepNavigation } from "@/components/onboarding/step-navigation";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const TRAINING_STATUS_OPTIONS = [
  { value: "unproductive", label: "Unproductive" },
  { value: "maintaining", label: "Maintaining" },
  { value: "productive", label: "Productive" },
  { value: "peaking", label: "Peaking" },
  { value: "overreaching", label: "Overreaching" },
  { value: "recovery", label: "Recovery" },
  { value: "detraining", label: "Detraining" },
  { value: "not_sure", label: "Not sure" },
] as const;

/**
 * Step 5: Baseline Biometric Metrics
 *
 * 30-day averages from Garmin Connect establishing personal normal.
 * All fields optional -- AI establishes baseline from first 7 days if blank.
 */
export default function Step5Page() {
  const { form, onSubmit, isLoading, isSubmitting } = useStepForm({
    schema: step5Schema,
    stepNumber: 5,
  });

  const {
    register,
    formState: { errors },
    setValue,
    watch,
  } = form;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Baseline Biometric Metrics</CardTitle>
          <CardDescription>
            30-day averages from Garmin Connect establishing your personal
            normal -- the reference frame for daily deviation assessment.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-3 text-sm text-blue-800 dark:border-blue-900/50 dark:bg-blue-950/20 dark:text-blue-300 mb-6">
            These are all optional. If left blank, the AI will establish your
            personal baseline from the first 7 days of Garmin data.
          </div>

          <div className="grid gap-6 sm:grid-cols-2">
            <FieldGroup
              label="HRV (ms, RMSSD)"
              description="30-day average from Garmin Connect"
            >
              <Input
                type="number"
                placeholder="e.g. 45"
                {...register("hrv_rmssd", { valueAsNumber: true })}
              />
              {errors.hrv_rmssd && (
                <p className="text-xs text-destructive">
                  {errors.hrv_rmssd.message}
                </p>
              )}
            </FieldGroup>

            <FieldGroup
              label="Resting Heart Rate (bpm)"
              description="Resting Heart Rate average"
            >
              <Input
                type="number"
                placeholder="e.g. 55"
                {...register("resting_hr", { valueAsNumber: true })}
              />
              {errors.resting_hr && (
                <p className="text-xs text-destructive">
                  {errors.resting_hr.message}
                </p>
              )}
            </FieldGroup>

            <FieldGroup
              label="VO2 Max (ml/kg/min)"
              description="Garmin estimate"
            >
              <Input
                type="number"
                placeholder="e.g. 48"
                {...register("vo2_max", { valueAsNumber: true })}
              />
              {errors.vo2_max && (
                <p className="text-xs text-destructive">
                  {errors.vo2_max.message}
                </p>
              )}
            </FieldGroup>

            <FieldGroup
              label="SpO2 (%)"
              description="Blood Oxygen Saturation"
            >
              <Input
                type="number"
                placeholder="e.g. 97"
                {...register("spo2_avg", { valueAsNumber: true })}
              />
              {errors.spo2_avg && (
                <p className="text-xs text-destructive">
                  {errors.spo2_avg.message}
                </p>
              )}
            </FieldGroup>

            <FieldGroup
              label="Respiration Rate during Sleep (brpm)"
              description="Breaths per minute during sleep"
            >
              <Input
                type="number"
                placeholder="e.g. 14"
                {...register("respiration_rate_sleep", {
                  valueAsNumber: true,
                })}
              />
              {errors.respiration_rate_sleep && (
                <p className="text-xs text-destructive">
                  {errors.respiration_rate_sleep.message}
                </p>
              )}
            </FieldGroup>

            <FieldGroup
              label="Body Battery Morning Score (0-100)"
              description="Morning Body Battery reading"
            >
              <Input
                type="number"
                placeholder="e.g. 75"
                {...register("body_battery_morning", {
                  valueAsNumber: true,
                })}
              />
              {errors.body_battery_morning && (
                <p className="text-xs text-destructive">
                  {errors.body_battery_morning.message}
                </p>
              )}
            </FieldGroup>

            <FieldGroup
              label="Average Daily Steps"
              description="30-day average"
            >
              <Input
                type="number"
                placeholder="e.g. 8000"
                {...register("average_daily_steps", {
                  valueAsNumber: true,
                })}
              />
              {errors.average_daily_steps && (
                <p className="text-xs text-destructive">
                  {errors.average_daily_steps.message}
                </p>
              )}
            </FieldGroup>

            <FieldGroup
              label="Sleep Score Average (0-100)"
              description="Garmin sleep score average"
            >
              <Input
                type="number"
                placeholder="e.g. 80"
                {...register("sleep_score_avg", {
                  valueAsNumber: true,
                })}
              />
              {errors.sleep_score_avg && (
                <p className="text-xs text-destructive">
                  {errors.sleep_score_avg.message}
                </p>
              )}
            </FieldGroup>
          </div>

          <div className="mt-6">
            <FieldGroup
              label="Garmin Training Status"
              description="Current training status from Garmin Connect"
            >
              <Select
                value={watch("garmin_training_status") || ""}
                onValueChange={(val) =>
                  setValue(
                    "garmin_training_status",
                    val as (typeof TRAINING_STATUS_OPTIONS)[number]["value"],
                    { shouldValidate: true }
                  )
                }
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select training status" />
                </SelectTrigger>
                <SelectContent>
                  {TRAINING_STATUS_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FieldGroup>
          </div>
        </CardContent>
      </Card>

      <StepNavigation
        currentStep={5}
        onSubmit={onSubmit}
        isSubmitting={isSubmitting}
        canSkip={true}
      />
    </div>
  );
}
