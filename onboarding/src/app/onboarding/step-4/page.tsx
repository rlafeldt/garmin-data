"use client";

import { Controller } from "react-hook-form";
import { step4Schema, type Step4Data } from "@/lib/schemas/step-4";
import { useStepForm } from "@/hooks/use-step-form";
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
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

// --- Option data ---

const TRAINING_PHASE_OPTIONS = [
  { value: "off_season", label: "Off-season" },
  { value: "base_aerobic", label: "Base/Aerobic" },
  { value: "build_race_specific", label: "Build/Race-specific" },
  { value: "peak_competition", label: "Peak/Competition" },
  { value: "taper", label: "Taper" },
  { value: "recovery_deload", label: "Recovery/Deload" },
  { value: "rehabilitation", label: "Rehabilitation" },
  { value: "no_structured_training", label: "No structured training" },
];

const CHRONOTYPE_OPTIONS = [
  { value: "definite_morning", label: "Definite morning" },
  { value: "moderate_morning", label: "Moderate morning" },
  { value: "intermediate", label: "Intermediate" },
  { value: "moderate_evening", label: "Moderate evening" },
  { value: "definite_evening", label: "Definite evening" },
];

const TRAINING_TIME_OPTIONS = [
  { value: "early_morning", label: "Early morning (5-8am)" },
  { value: "mid_morning", label: "Mid-morning (8-11am)" },
  { value: "midday", label: "Midday" },
  { value: "afternoon", label: "Afternoon (1-5pm)" },
  { value: "evening", label: "Evening (5-8pm)" },
  { value: "night", label: "Night (after 8pm)" },
  { value: "varies", label: "Varies" },
];

const SLEEP_CONSISTENCY_OPTIONS = [
  { value: "very_consistent", label: "Very consistent" },
  { value: "mostly", label: "Mostly (+/- 30 min)" },
  { value: "social_jetlag_1_2h", label: "Social jetlag (1-2 hours)" },
  { value: "significant_jetlag_2h_plus", label: "Significant jetlag (2h+)" },
  { value: "highly_irregular", label: "Highly irregular" },
];

const SLEEP_DURATION_OPTIONS = [
  { value: "under_5h", label: "< 5 hours" },
  { value: "5_6h", label: "5 - 6 hours" },
  { value: "6_7h", label: "6 - 7 hours" },
  { value: "7_8h", label: "7 - 8 hours" },
  { value: "8_9h", label: "8 - 9 hours" },
  { value: "over_9h", label: "> 9 hours" },
];

const SCREEN_EXPOSURE_OPTIONS = [
  { value: "no_screens_after_8pm", label: "No screens after 8pm" },
  { value: "screens_stop_1h_before", label: "Screens stop 1h before bed" },
  { value: "30min_before", label: "30 min before bed" },
  { value: "in_bed_until_sleep", label: "In bed until sleep" },
  { value: "blue_light_glasses", label: "Blue-light glasses used" },
];

const RECOVERY_LABELS: Record<number, string> = {
  1: "Exhausted",
  2: "Below average",
  3: "Moderate",
  4: "Good",
  5: "Fully restored",
};

const COGNITIVE_FATIGUE_OPTIONS = [
  { value: "rarely", label: "Rarely" },
  { value: "occasional_afternoon_dip", label: "Occasional afternoon dip" },
  { value: "regular_brain_fog", label: "Regular brain fog" },
  { value: "chronic", label: "Chronic" },
];

const DELIVERY_TIME_OPTIONS = [
  { value: "morning", label: "Morning" },
  { value: "post_workout", label: "Post-workout" },
  { value: "evening", label: "Evening" },
  { value: "flexible", label: "Flexible" },
];

/**
 * Step 4: Training Context & Sleep
 *
 * Periodisation context, circadian alignment, and sleep data for interpreting
 * daily HRV, VO2, and training load.
 *
 * Required: current_training_phase, chronotype
 * All other fields optional.
 */
export default function Step4Page() {
  const { form, onSubmit, isLoading, isSubmitting } = useStepForm<Step4Data>({
    schema: step4Schema,
    stepNumber: 4,
  });

  const {
    register,
    control,
    formState: { errors },
  } = form;

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 bg-muted rounded w-1/3" />
        <div className="h-40 bg-muted rounded" />
        <div className="h-40 bg-muted rounded" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Training Context & Sleep</h1>
        <p className="text-muted-foreground mt-1">
          Periodisation context, circadian alignment, and sleep data for
          interpreting your daily HRV, VO2, and training load.
        </p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
      >
        {/* Required Fields */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Training Phase & Chronotype</CardTitle>
            <CardDescription>
              These fields are required for your training profile.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <FieldGroup
              label="Current Training Phase"
              required
              error={errors.current_training_phase?.message as string}
            >
              <Controller
                name="current_training_phase"
                control={control}
                render={({ field }) => (
                  <Select value={field.value ?? ""} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select training phase" />
                    </SelectTrigger>
                    <SelectContent>
                      {TRAINING_PHASE_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </FieldGroup>

            <FieldGroup
              label="Chronotype"
              description="Your natural sleep preference"
              required
              error={errors.chronotype?.message as string}
            >
              <Controller
                name="chronotype"
                control={control}
                render={({ field }) => (
                  <Select value={field.value ?? ""} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select chronotype" />
                    </SelectTrigger>
                    <SelectContent>
                      {CHRONOTYPE_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </FieldGroup>
          </CardContent>
        </Card>

        {/* Training Context */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Training Context</CardTitle>
            <CardDescription>Optional training details.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <FieldGroup
              label="Next Race or Key Event"
              description="Maximum 200 characters"
              error={errors.next_race_event?.message as string}
            >
              <Input
                type="text"
                maxLength={200}
                placeholder='e.g. "Marathon -- 12 weeks out"'
                {...register("next_race_event")}
              />
            </FieldGroup>

            <FieldGroup
              label="Typical Training Time of Day"
              error={errors.typical_training_time?.message as string}
            >
              <Controller
                name="typical_training_time"
                control={control}
                render={({ field }) => (
                  <Select value={field.value ?? ""} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select typical time" />
                    </SelectTrigger>
                    <SelectContent>
                      {TRAINING_TIME_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </FieldGroup>
          </CardContent>
        </Card>

        {/* Sleep Context */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Sleep Context</CardTitle>
            <CardDescription>
              Sleep habits and recovery assessment. All optional.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FieldGroup
                label="Sleep Schedule Consistency"
                error={errors.sleep_schedule_consistency?.message as string}
              >
                <Controller
                  name="sleep_schedule_consistency"
                  control={control}
                  render={({ field }) => (
                    <Select
                      value={field.value ?? ""}
                      onValueChange={field.onChange}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                      <SelectContent>
                        {SLEEP_CONSISTENCY_OPTIONS.map((opt) => (
                          <SelectItem key={opt.value} value={opt.value}>
                            {opt.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </FieldGroup>

              <FieldGroup
                label="Average Sleep Duration"
                error={errors.average_sleep_duration?.message as string}
              >
                <Controller
                  name="average_sleep_duration"
                  control={control}
                  render={({ field }) => (
                    <Select
                      value={field.value ?? ""}
                      onValueChange={field.onChange}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                      <SelectContent>
                        {SLEEP_DURATION_OPTIONS.map((opt) => (
                          <SelectItem key={opt.value} value={opt.value}>
                            {opt.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </FieldGroup>
            </div>

            <FieldGroup
              label="Screen / Blue Light Exposure Before Bed"
              error={errors.screen_blue_light?.message as string}
            >
              <Controller
                name="screen_blue_light"
                control={control}
                render={({ field }) => (
                  <Select value={field.value ?? ""} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
                      {SCREEN_EXPOSURE_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </FieldGroup>

            <FieldGroup
              label="Subjective Recovery on Waking"
              error={errors.subjective_recovery_waking?.message as string}
            >
              <Controller
                name="subjective_recovery_waking"
                control={control}
                render={({ field }) => (
                  <RadioGroup
                    value={field.value?.toString() ?? ""}
                    onValueChange={(v) => field.onChange(parseInt(v, 10))}
                    className="flex flex-wrap gap-3"
                  >
                    {[1, 2, 3, 4, 5].map((level) => (
                      <div key={level} className="flex items-center gap-1.5">
                        <RadioGroupItem
                          value={level.toString()}
                          id={`recovery-${level}`}
                        />
                        <Label
                          htmlFor={`recovery-${level}`}
                          className="text-sm font-normal cursor-pointer"
                        >
                          {level} - {RECOVERY_LABELS[level]}
                        </Label>
                      </div>
                    ))}
                  </RadioGroup>
                )}
              />
            </FieldGroup>

            <FieldGroup
              label="Perceived Cognitive Fatigue"
              error={errors.perceived_cognitive_fatigue?.message as string}
            >
              <Controller
                name="perceived_cognitive_fatigue"
                control={control}
                render={({ field }) => (
                  <Select value={field.value ?? ""} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
                      {COGNITIVE_FATIGUE_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </FieldGroup>
          </CardContent>
        </Card>

        {/* Delivery Preference */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Delivery Preference</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <FieldGroup
              label="Preferred Insight Delivery Time"
              error={
                errors.preferred_insight_delivery_time?.message as string
              }
            >
              <Controller
                name="preferred_insight_delivery_time"
                control={control}
                render={({ field }) => (
                  <Select value={field.value ?? ""} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select preferred time" />
                    </SelectTrigger>
                    <SelectContent>
                      {DELIVERY_TIME_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </FieldGroup>
            <p className="text-xs text-muted-foreground">
              This preference will be used for future delivery scheduling.
            </p>
          </CardContent>
        </Card>

        <StepNavigation
          currentStep={4}
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
          canSkip={true}
        />
      </form>
    </div>
  );
}
