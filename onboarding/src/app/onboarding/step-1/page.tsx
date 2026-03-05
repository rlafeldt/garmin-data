"use client";

import { Controller } from "react-hook-form";
import { step1Schema, type Step1Data } from "@/lib/schemas/step-1";
import { useStepForm } from "@/hooks/use-step-form";
import { FieldGroup } from "@/components/onboarding/field-group";
import { MultiSelect } from "@/components/onboarding/multi-select";
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

const PRIMARY_SPORT_OPTIONS = [
  { value: "running", label: "Running" },
  { value: "cycling", label: "Cycling" },
  { value: "triathlon", label: "Triathlon" },
  { value: "swimming", label: "Swimming" },
  { value: "strength_training", label: "Strength Training" },
  { value: "crossfit_hiit", label: "CrossFit/HIIT" },
  { value: "team_sports", label: "Team Sports" },
  { value: "hiking_trail", label: "Hiking/Trail" },
  { value: "mixed_general_fitness", label: "Mixed/General Fitness" },
  { value: "other", label: "Other" },
];

const ACTIVITY_LEVEL_OPTIONS = [
  { value: "sedentary", label: "Sedentary" },
  { value: "light", label: "Light" },
  { value: "moderate", label: "Moderate" },
  { value: "active", label: "Active" },
  { value: "very_active", label: "Very Active" },
];

const GOALS_OPTIONS = [
  { value: "performance", label: "Performance" },
  { value: "recovery", label: "Recovery" },
  { value: "metabolic_flexibility", label: "Metabolic Flexibility" },
  { value: "body_composition", label: "Body Composition" },
  { value: "longevity", label: "Longevity" },
  { value: "sleep_quality", label: "Sleep Quality" },
  { value: "stress_resilience", label: "Stress Resilience" },
  { value: "injury_prevention", label: "Injury Prevention" },
  { value: "cognitive_performance", label: "Cognitive Performance" },
];

const HORMONAL_STATUS_OPTIONS = [
  { value: "regular_tracking", label: "Regular (tracking)" },
  { value: "regular_not_tracking", label: "Regular (not tracking)" },
  { value: "irregular", label: "Irregular" },
  { value: "perimenopause", label: "Perimenopause" },
  { value: "post_menopause", label: "Post-menopause" },
  { value: "hormonal_contraception", label: "Hormonal contraception" },
  { value: "hrt", label: "HRT" },
  { value: "prefer_not_to_say", label: "Prefer not to say" },
];

const CYCLE_PHASE_OPTIONS = [
  { value: "menstrual", label: "Menstrual (days 1-5)" },
  { value: "follicular", label: "Follicular (days 6-13)" },
  { value: "ovulatory", label: "Ovulatory (days 13-16)" },
  { value: "luteal", label: "Luteal (days 17-28)" },
  { value: "not_applicable", label: "Not applicable" },
];

const STRESS_LABELS: Record<number, string> = {
  1: "Minimal",
  2: "Low",
  3: "Moderate",
  4: "High",
  5: "Chronic/Severe",
};

/**
 * Step 1: Biological Profile
 *
 * Core biometric data used to calibrate all AI interpretations.
 * Required: age, sex, height, weight, primary sport.
 * Optional: activity level, training volume, goals, stress, hormonal context (ONBD-08).
 */
export default function Step1Page() {
  const { form, onSubmit, isLoading, isSubmitting } = useStepForm<Step1Data>({
    schema: step1Schema,
    stepNumber: 1,
  });

  const {
    register,
    control,
    watch,
    formState: { errors },
  } = form;

  const biologicalSex = watch("biological_sex");
  const showHormonalContext = biologicalSex === "female";

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
        <h1 className="text-2xl font-bold">Biological Profile</h1>
        <p className="text-muted-foreground mt-1">
          Core biometric data used to calibrate all AI interpretations and
          establish your individual physiological baseline.
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
            <CardTitle className="text-lg">Essential Information</CardTitle>
            <CardDescription>
              These fields are required for your profile.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <FieldGroup
              label="Age"
              required
              error={errors.age?.message as string}
            >
              <Input
                type="number"
                placeholder="e.g. 32"
                {...register("age", { valueAsNumber: true })}
                aria-invalid={!!errors.age}
              />
            </FieldGroup>

            <FieldGroup
              label="Biological Sex"
              required
              error={errors.biological_sex?.message as string}
            >
              <Controller
                name="biological_sex"
                control={control}
                render={({ field }) => (
                  <RadioGroup
                    value={field.value ?? ""}
                    onValueChange={field.onChange}
                    className="flex flex-wrap gap-4"
                  >
                    {[
                      { value: "male", label: "Male" },
                      { value: "female", label: "Female" },
                      { value: "prefer_not_to_say", label: "Prefer not to say" },
                    ].map((option) => (
                      <div key={option.value} className="flex items-center gap-2">
                        <RadioGroupItem value={option.value} id={`sex-${option.value}`} />
                        <Label htmlFor={`sex-${option.value}`} className="font-normal cursor-pointer">
                          {option.label}
                        </Label>
                      </div>
                    ))}
                  </RadioGroup>
                )}
              />
            </FieldGroup>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FieldGroup
                label="Height (cm)"
                required
                error={errors.height_cm?.message as string}
              >
                <Input
                  type="number"
                  placeholder="e.g. 175"
                  {...register("height_cm", { valueAsNumber: true })}
                  aria-invalid={!!errors.height_cm}
                />
              </FieldGroup>

              <FieldGroup
                label="Weight (kg)"
                required
                error={errors.weight_kg?.message as string}
              >
                <Input
                  type="number"
                  step="0.1"
                  placeholder="e.g. 72"
                  {...register("weight_kg", { valueAsNumber: true })}
                  aria-invalid={!!errors.weight_kg}
                />
              </FieldGroup>
            </div>

            <FieldGroup
              label="Primary Sport / Activity"
              required
              error={errors.primary_sport?.message as string}
            >
              <Controller
                name="primary_sport"
                control={control}
                render={({ field }) => (
                  <Select value={field.value ?? ""} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select your primary sport" />
                    </SelectTrigger>
                    <SelectContent>
                      {PRIMARY_SPORT_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </FieldGroup>
          </CardContent>
        </Card>

        {/* Hormonal Context (ONBD-08) - conditional for female athletes */}
        {showHormonalContext && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="text-lg">Hormonal Context</CardTitle>
              <CardDescription>
                Hormonal status affects HRV, recovery, substrate utilisation, and
                sleep architecture across the menstrual cycle.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <FieldGroup
                label="Hormonal / Menstrual Status"
                error={errors.hormonal_status?.message as string}
              >
                <Controller
                  name="hormonal_status"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value ?? ""} onValueChange={field.onChange}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                      <SelectContent>
                        {HORMONAL_STATUS_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </FieldGroup>

              <FieldGroup
                label="Current Cycle Phase"
                error={errors.cycle_phase?.message as string}
              >
                <Controller
                  name="cycle_phase"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value ?? ""} onValueChange={field.onChange}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select phase" />
                      </SelectTrigger>
                      <SelectContent>
                        {CYCLE_PHASE_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </FieldGroup>
            </CardContent>
          </Card>
        )}

        {/* Optional Fields */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Additional Details</CardTitle>
            <CardDescription>
              Optional -- these help refine your insights but can be added later.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <FieldGroup
              label="Occupational Activity Level"
              error={errors.occupational_activity_level?.message as string}
            >
              <Controller
                name="occupational_activity_level"
                control={control}
                render={({ field }) => (
                  <Select value={field.value ?? ""} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select activity level" />
                    </SelectTrigger>
                    <SelectContent>
                      {ACTIVITY_LEVEL_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </FieldGroup>

            <FieldGroup
              label="Weekly Training Volume (hours/week)"
              description="0-25 hours per week"
              error={errors.weekly_training_volume_hours?.message as string}
            >
              <Input
                type="number"
                min={0}
                max={25}
                step={0.5}
                placeholder="e.g. 8"
                {...register("weekly_training_volume_hours", {
                  valueAsNumber: true,
                })}
              />
            </FieldGroup>

            <FieldGroup
              label="Primary Goals"
              description="Select all that apply"
              error={errors.primary_goals?.message as string}
            >
              <Controller
                name="primary_goals"
                control={control}
                render={({ field }) => (
                  <MultiSelect
                    options={GOALS_OPTIONS}
                    value={field.value ?? []}
                    onChange={field.onChange}
                  />
                )}
              />
            </FieldGroup>

            <FieldGroup
              label="Perceived Chronic Stress Level"
              error={errors.perceived_stress_level?.message as string}
            >
              <Controller
                name="perceived_stress_level"
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
                          id={`stress-${level}`}
                        />
                        <Label
                          htmlFor={`stress-${level}`}
                          className="text-sm font-normal cursor-pointer"
                        >
                          {level} - {STRESS_LABELS[level]}
                        </Label>
                      </div>
                    ))}
                  </RadioGroup>
                )}
              />
            </FieldGroup>
          </CardContent>
        </Card>

        <StepNavigation
          currentStep={1}
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
          canSkip={false}
        />
      </form>
    </div>
  );
}
