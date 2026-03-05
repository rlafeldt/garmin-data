"use client";

import { Controller } from "react-hook-form";
import { step3Schema, type Step3Data } from "@/lib/schemas/step-3";
import { useStepForm } from "@/hooks/use-step-form";
import { FieldGroup } from "@/components/onboarding/field-group";
import { MultiSelect } from "@/components/onboarding/multi-select";
import { StepNavigation } from "@/components/onboarding/step-navigation";
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

const DIETARY_PATTERN_OPTIONS = [
  { value: "omnivore", label: "Omnivore" },
  { value: "ketogenic", label: "Ketogenic" },
  { value: "low_carb_lchf", label: "Low carb/LCHF" },
  { value: "mediterranean", label: "Mediterranean" },
  { value: "paleo_ancestral", label: "Paleo/Ancestral" },
  { value: "carnivore_animal_based", label: "Carnivore/Animal-based" },
  { value: "plant_based_vegan", label: "Plant-based/Vegan" },
  { value: "cyclic", label: "Cyclic" },
];

const PRE_TRAINING_NUTRITION_OPTIONS = [
  { value: "fully_fasted", label: "Fully fasted" },
  { value: "coffee_only", label: "Coffee only" },
  { value: "light_carbs", label: "Light carbs" },
  { value: "full_meal_with_carbs", label: "Full meal with carbs" },
  { value: "protein_only", label: "Protein only" },
  { value: "mixed_meal", label: "Mixed meal" },
  { value: "varies_by_session", label: "Varies by session" },
];

const CARB_SOURCES_OPTIONS = [
  { value: "fruit", label: "Fruit" },
  { value: "root_vegetables", label: "Root vegetables" },
  { value: "legumes_lentils", label: "Legumes/lentils" },
  { value: "white_rice_potato", label: "White rice/potato" },
  { value: "whole_grains", label: "Whole grains" },
  { value: "refined_grains", label: "Refined grains" },
  { value: "ultra_processed_food", label: "Ultra-processed food" },
  { value: "sugar_sweetened_drinks", label: "Sugar-sweetened drinks" },
  { value: "avoids_most_carbs", label: "Avoids most carbs" },
];

const FREQUENCY_SCALE = [
  { value: "never", label: "Never" },
  { value: "occasionally", label: "Occasionally" },
  { value: "often", label: "Often" },
  { value: "always", label: "Always" },
];

const FASTED_TRAINING_SCALE = [
  { value: "never_tried", label: "Never tried" },
  { value: "cannot", label: "Cannot" },
  { value: "with_difficulty", label: "With difficulty" },
  { value: "easily", label: "Easily" },
];

const ENERGY_CONSISTENCY_SCALE = [
  { value: "always_consistent", label: "Always consistent" },
  { value: "mostly", label: "Mostly consistent" },
  { value: "variable", label: "Variable" },
  { value: "significant_crashes", label: "Significant crashes" },
];

const EATING_WINDOW_OPTIONS = [
  { value: "no_fasting", label: "No fasting" },
  { value: "twelve_twelve", label: "12:12" },
  { value: "sixteen_eight", label: "16:8" },
  { value: "eighteen_six", label: "18:6" },
  { value: "twenty_four", label: "20:4" },
  { value: "omad", label: "OMAD" },
  { value: "multi_day", label: "Multi-day" },
  { value: "variable", label: "Variable" },
];

const DAILY_CALORIES_OPTIONS = [
  { value: "under_1500", label: "< 1,500" },
  { value: "1500_2000", label: "1,500 - 2,000" },
  { value: "2000_2500", label: "2,000 - 2,500" },
  { value: "2500_3000", label: "2,500 - 3,000" },
  { value: "3000_3500", label: "3,000 - 3,500" },
  { value: "over_3500", label: "> 3,500" },
  { value: "dont_track", label: "Don't track" },
];

const PROTEIN_INTAKE_OPTIONS = [
  { value: "very_low", label: "Very low (< 0.6 g/kg)" },
  { value: "low", label: "Low (0.6 - 0.8 g/kg)" },
  { value: "moderate", label: "Moderate (1.0 - 1.6 g/kg)" },
  { value: "high", label: "High (1.6 - 2.0 g/kg)" },
  { value: "very_high", label: "Very high (> 2.0 g/kg)" },
];

const MEAL_TO_TRAINING_OPTIONS = [
  { value: "fasted_8h_plus", label: "Fasted (8h+)" },
  { value: "under_30min", label: "< 30 min" },
  { value: "30_60min", label: "30 - 60 min" },
  { value: "1_2h", label: "1 - 2 hours" },
  { value: "2_3h", label: "2 - 3 hours" },
  { value: "3h_plus", label: "3+ hours" },
  { value: "varies", label: "Varies" },
];

const INTRA_TRAINING_OPTIONS = [
  { value: "water_only", label: "Water only" },
  { value: "electrolytes", label: "Electrolytes" },
  { value: "gels_sports_drink", label: "Gels/sports drink" },
  { value: "whole_food", label: "Whole food" },
  { value: "nothing_under_60min", label: "Nothing (< 60 min)" },
];

const POST_WORKOUT_OPTIONS = [
  { value: "within_30min", label: "Within 30 min" },
  { value: "30_60min", label: "30 - 60 min" },
  { value: "1_2h", label: "1 - 2 hours" },
  { value: "2h_plus", label: "2+ hours" },
  { value: "extend_fast", label: "Extend fast" },
];

const WATER_INTAKE_OPTIONS = [
  { value: "under_1_5l", label: "< 1.5 L" },
  { value: "1_5_2_5l", label: "1.5 - 2.5 L" },
  { value: "2_5_3_5l", label: "2.5 - 3.5 L" },
  { value: "over_3_5l", label: "> 3.5 L" },
];

const STIMULANTS_OPTIONS = [
  { value: "black_coffee", label: "Black coffee" },
  { value: "espresso", label: "Espresso" },
  { value: "caffeine_pill", label: "Caffeine pill" },
  { value: "pre_workout", label: "Pre-workout" },
  { value: "energy_drink", label: "Energy drink" },
  { value: "yerba_mate_green_tea", label: "Yerba mate/green tea" },
  { value: "beta_alanine", label: "Beta-Alanine" },
  { value: "citrulline_arginine", label: "Citrulline/Arginine" },
  { value: "none", label: "None" },
];

const CAFFEINE_INTAKE_OPTIONS = [
  { value: "none", label: "None" },
  { value: "low", label: "Low (< 100 mg)" },
  { value: "moderate", label: "Moderate (100 - 200 mg)" },
  { value: "high", label: "High (200 - 400 mg)" },
  { value: "very_high", label: "Very high (400 mg+)" },
];

const CAFFEINE_CUTOFF_OPTIONS = [
  { value: "no_caffeine", label: "No caffeine" },
  { value: "before_10am", label: "Before 10am" },
  { value: "before_noon", label: "Before noon" },
  { value: "before_2pm", label: "Before 2pm" },
  { value: "afternoon", label: "Afternoon" },
  { value: "evening", label: "Evening" },
];

const ALCOHOL_OPTIONS = [
  { value: "none", label: "None" },
  { value: "occasional", label: "Occasional (< 1/week)" },
  { value: "moderate", label: "Moderate (1-7/week)" },
  { value: "regular", label: "Regular (> 7/week)" },
];

const FOOD_SENSITIVITIES_OPTIONS = [
  { value: "none", label: "None" },
  { value: "gluten_wheat", label: "Gluten/Wheat" },
  { value: "lactose_dairy", label: "Lactose/Dairy" },
  { value: "fructose", label: "Fructose" },
  { value: "fodmap", label: "FODMAP" },
  { value: "histamine_intolerance", label: "Histamine intolerance" },
  { value: "multiple", label: "Multiple" },
];

// --- Helper: inline radio group for metabolic signals ---

function SignalRadioGroup({
  name,
  options,
  value,
  onChange,
}: {
  name: string;
  options: { value: string; label: string }[];
  value: string | undefined;
  onChange: (v: string) => void;
}) {
  return (
    <RadioGroup
      value={value ?? ""}
      onValueChange={onChange}
      className="flex flex-wrap gap-3"
    >
      {options.map((option) => (
        <div key={option.value} className="flex items-center gap-1.5">
          <RadioGroupItem
            value={option.value}
            id={`${name}-${option.value}`}
          />
          <Label
            htmlFor={`${name}-${option.value}`}
            className="text-sm font-normal cursor-pointer"
          >
            {option.label}
          </Label>
        </div>
      ))}
    </RadioGroup>
  );
}

/**
 * Step 3: Metabolic & Nutrition Profile
 *
 * Assesses metabolic flexibility, dietary pattern, meal timing, hydration,
 * and stimulant use. This is the longest form -- fields are grouped into
 * clearly separated card sections.
 *
 * Required: dietary_pattern, pre_training_nutrition
 * All other fields optional.
 */
export default function Step3Page() {
  const { form, onSubmit, isLoading, isSubmitting } = useStepForm<Step3Data>({
    schema: step3Schema,
    stepNumber: 3,
  });

  const {
    control,
    formState: { errors },
  } = form;

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 bg-muted rounded w-1/3" />
        <div className="h-40 bg-muted rounded" />
        <div className="h-40 bg-muted rounded" />
        <div className="h-40 bg-muted rounded" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Metabolic & Nutrition Profile</h1>
        <p className="text-muted-foreground mt-1">
          Assesses your metabolic flexibility -- capacity to switch between fat
          and glucose oxidation. Covers dietary pattern, meal timing, hydration,
          and stimulants.
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
            <CardTitle className="text-lg">Dietary Essentials</CardTitle>
            <CardDescription>
              These fields are required for your nutrition profile.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <FieldGroup
              label="Current Dietary Pattern"
              required
              error={errors.dietary_pattern?.message as string}
            >
              <Controller
                name="dietary_pattern"
                control={control}
                render={({ field }) => (
                  <Select value={field.value ?? ""} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select dietary pattern" />
                    </SelectTrigger>
                    <SelectContent>
                      {DIETARY_PATTERN_OPTIONS.map((opt) => (
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
              label="Pre-Training Nutrition"
              required
              error={errors.pre_training_nutrition?.message as string}
            >
              <Controller
                name="pre_training_nutrition"
                control={control}
                render={({ field }) => (
                  <Select value={field.value ?? ""} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select pre-training approach" />
                    </SelectTrigger>
                    <SelectContent>
                      {PRE_TRAINING_NUTRITION_OPTIONS.map((opt) => (
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

        {/* Metabolic Flexibility Signals */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Metabolic Flexibility Signals</CardTitle>
            <CardDescription>
              These questions help assess your body&apos;s ability to switch
              between fuel sources. All optional.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <FieldGroup
              label="Energy crash / brain fog after carb-heavy meal"
              error={
                errors.metabolic_flexibility_signals?.energy_crash
                  ?.message as string
              }
            >
              <Controller
                name="metabolic_flexibility_signals.energy_crash"
                control={control}
                render={({ field }) => (
                  <SignalRadioGroup
                    name="energy-crash"
                    options={FREQUENCY_SCALE}
                    value={field.value}
                    onChange={field.onChange}
                  />
                )}
              />
            </FieldGroup>

            <FieldGroup
              label="Strong hunger / irritability when skipping a meal"
              error={
                errors.metabolic_flexibility_signals?.hunger_irritability
                  ?.message as string
              }
            >
              <Controller
                name="metabolic_flexibility_signals.hunger_irritability"
                control={control}
                render={({ field }) => (
                  <SignalRadioGroup
                    name="hunger"
                    options={FREQUENCY_SCALE}
                    value={field.value}
                    onChange={field.onChange}
                  />
                )}
              />
            </FieldGroup>

            <FieldGroup
              label="Ability to train fasted"
              error={
                errors.metabolic_flexibility_signals?.fasted_training
                  ?.message as string
              }
            >
              <Controller
                name="metabolic_flexibility_signals.fasted_training"
                control={control}
                render={({ field }) => (
                  <SignalRadioGroup
                    name="fasted"
                    options={FASTED_TRAINING_SCALE}
                    value={field.value}
                    onChange={field.onChange}
                  />
                )}
              />
            </FieldGroup>

            <FieldGroup
              label="Carb cravings in afternoon / evening"
              error={
                errors.metabolic_flexibility_signals?.carb_cravings
                  ?.message as string
              }
            >
              <Controller
                name="metabolic_flexibility_signals.carb_cravings"
                control={control}
                render={({ field }) => (
                  <SignalRadioGroup
                    name="cravings"
                    options={FREQUENCY_SCALE}
                    value={field.value}
                    onChange={field.onChange}
                  />
                )}
              />
            </FieldGroup>

            <FieldGroup
              label="Energy consistency throughout the day"
              error={
                errors.metabolic_flexibility_signals?.energy_consistency
                  ?.message as string
              }
            >
              <Controller
                name="metabolic_flexibility_signals.energy_consistency"
                control={control}
                render={({ field }) => (
                  <SignalRadioGroup
                    name="consistency"
                    options={ENERGY_CONSISTENCY_SCALE}
                    value={field.value}
                    onChange={field.onChange}
                  />
                )}
              />
            </FieldGroup>
          </CardContent>
        </Card>

        {/* Nutrition Details */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Nutrition Details</CardTitle>
            <CardDescription>
              Meal composition, timing, and hydration. All optional.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <FieldGroup
              label="Primary Carbohydrate Sources"
              description="Select all that apply"
              error={errors.primary_carb_sources?.message as string}
            >
              <Controller
                name="primary_carb_sources"
                control={control}
                render={({ field }) => (
                  <MultiSelect
                    options={CARB_SOURCES_OPTIONS}
                    value={field.value ?? []}
                    onChange={field.onChange}
                  />
                )}
              />
            </FieldGroup>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FieldGroup
                label="Eating Window / Fasting Protocol"
                error={errors.eating_window?.message as string}
              >
                <Controller
                  name="eating_window"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value ?? ""} onValueChange={field.onChange}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                      <SelectContent>
                        {EATING_WINDOW_OPTIONS.map((opt) => (
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
                label="Estimated Daily Calories"
                error={errors.estimated_daily_calories?.message as string}
              >
                <Controller
                  name="estimated_daily_calories"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value ?? ""} onValueChange={field.onChange}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                      <SelectContent>
                        {DAILY_CALORIES_OPTIONS.map((opt) => (
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
              label="Protein Intake Emphasis"
              error={errors.protein_intake_emphasis?.message as string}
            >
              <Controller
                name="protein_intake_emphasis"
                control={control}
                render={({ field }) => (
                  <Select value={field.value ?? ""} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select protein intake level" />
                    </SelectTrigger>
                    <SelectContent>
                      {PROTEIN_INTAKE_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </FieldGroup>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FieldGroup
                label="Time Between Last Meal and Training"
                error={errors.time_meal_to_training?.message as string}
              >
                <Controller
                  name="time_meal_to_training"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value ?? ""} onValueChange={field.onChange}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                      <SelectContent>
                        {MEAL_TO_TRAINING_OPTIONS.map((opt) => (
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
                label="Intra-Training Fuelling"
                error={errors.intra_training_fuelling?.message as string}
              >
                <Controller
                  name="intra_training_fuelling"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value ?? ""} onValueChange={field.onChange}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                      <SelectContent>
                        {INTRA_TRAINING_OPTIONS.map((opt) => (
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

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FieldGroup
                label="Post-Workout Nutrition Window"
                error={errors.post_workout_nutrition_window?.message as string}
              >
                <Controller
                  name="post_workout_nutrition_window"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value ?? ""} onValueChange={field.onChange}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                      <SelectContent>
                        {POST_WORKOUT_OPTIONS.map((opt) => (
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
                label="Daily Water Intake"
                error={errors.daily_water_intake?.message as string}
              >
                <Controller
                  name="daily_water_intake"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value ?? ""} onValueChange={field.onChange}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                      <SelectContent>
                        {WATER_INTAKE_OPTIONS.map((opt) => (
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
          </CardContent>
        </Card>

        {/* Stimulants */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Stimulants</CardTitle>
            <CardDescription>
              Pre-training stimulants and daily caffeine use. All optional.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <FieldGroup
              label="Pre-Training Stimulants"
              description="Select all that apply"
              error={errors.pre_training_stimulants?.message as string}
            >
              <Controller
                name="pre_training_stimulants"
                control={control}
                render={({ field }) => (
                  <MultiSelect
                    options={STIMULANTS_OPTIONS}
                    value={field.value ?? []}
                    onChange={field.onChange}
                  />
                )}
              />
            </FieldGroup>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FieldGroup
                label="Daily Caffeine Intake"
                error={errors.daily_caffeine_intake?.message as string}
              >
                <Controller
                  name="daily_caffeine_intake"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value ?? ""} onValueChange={field.onChange}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                      <SelectContent>
                        {CAFFEINE_INTAKE_OPTIONS.map((opt) => (
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
                label="Caffeine Cut-Off Time"
                error={errors.caffeine_cutoff_time?.message as string}
              >
                <Controller
                  name="caffeine_cutoff_time"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value ?? ""} onValueChange={field.onChange}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Select" />
                      </SelectTrigger>
                      <SelectContent>
                        {CAFFEINE_CUTOFF_OPTIONS.map((opt) => (
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
          </CardContent>
        </Card>

        {/* Other */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Other</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <FieldGroup
              label="Alcohol Consumption"
              error={errors.alcohol_consumption?.message as string}
            >
              <Controller
                name="alcohol_consumption"
                control={control}
                render={({ field }) => (
                  <Select value={field.value ?? ""} onValueChange={field.onChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent>
                      {ALCOHOL_OPTIONS.map((opt) => (
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
              label="Known Food Sensitivities"
              description="Select all that apply"
              error={errors.food_sensitivities?.message as string}
            >
              <Controller
                name="food_sensitivities"
                control={control}
                render={({ field }) => (
                  <MultiSelect
                    options={FOOD_SENSITIVITIES_OPTIONS}
                    value={field.value ?? []}
                    onChange={field.onChange}
                    columns={2}
                  />
                )}
              />
            </FieldGroup>
          </CardContent>
        </Card>

        <StepNavigation
          currentStep={3}
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
          canSkip={true}
        />
      </form>
    </div>
  );
}
