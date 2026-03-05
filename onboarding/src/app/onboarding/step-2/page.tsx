"use client";

import { Controller } from "react-hook-form";
import { step2Schema, type Step2Data } from "@/lib/schemas/step-2";
import { useStepForm } from "@/hooks/use-step-form";
import { FieldGroup } from "@/components/onboarding/field-group";
import { MultiSelect } from "@/components/onboarding/multi-select";
import { SupplementPicker } from "@/components/onboarding/supplement-picker";
import { StepNavigation } from "@/components/onboarding/step-navigation";
import { Textarea } from "@/components/ui/textarea";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const HEALTH_CONDITIONS_OPTIONS = [
  { value: "type_2_diabetes", label: "Type 2 Diabetes" },
  { value: "hypertension", label: "Hypertension" },
  { value: "hypothyroidism", label: "Hypothyroidism" },
  { value: "hyperthyroidism", label: "Hyperthyroidism" },
  { value: "insulin_resistance", label: "Insulin Resistance" },
  { value: "pcos", label: "PCOS" },
  { value: "sleep_apnea", label: "Sleep Apnea" },
  { value: "cardiovascular_disease", label: "Cardiovascular Disease" },
  { value: "autoimmune_condition", label: "Autoimmune Condition" },
  { value: "anxiety_depression", label: "Anxiety/Depression" },
  { value: "gut_digestive_issues", label: "Gut/Digestive Issues" },
  { value: "none", label: "None" },
];

const RECOVERY_MODALITIES_OPTIONS = [
  { value: "cold_exposure_ice_bath", label: "Cold exposure/ice bath" },
  { value: "sauna", label: "Sauna" },
  { value: "contrast_therapy", label: "Contrast therapy" },
  { value: "massage_soft_tissue", label: "Massage/soft tissue" },
  { value: "red_light_therapy", label: "Red light therapy" },
  { value: "none", label: "None" },
  { value: "other", label: "Other" },
];

const SMOKING_OPTIONS = [
  { value: "non_smoker", label: "Non-smoker" },
  { value: "former_smoker", label: "Former smoker" },
  { value: "current_smoker", label: "Current smoker" },
  { value: "vaping_e_cigarettes", label: "Vaping/e-cigarettes" },
];

/**
 * Step 2: Health, Medications & Supplementation
 *
 * Contextualises biometric data, flags relevant interactions,
 * applies condition-specific evidence. All fields optional.
 */
export default function Step2Page() {
  const { form, onSubmit, isLoading, isSubmitting } = useStepForm<Step2Data>({
    schema: step2Schema,
    stepNumber: 2,
  });

  const {
    register,
    control,
    watch,
    setValue,
    formState: { errors },
  } = form;

  const healthConditions = watch("health_conditions") ?? [];
  const noSupplements = watch("no_supplements") ?? false;

  // When "None" is selected for health conditions, clear other selections
  type HealthCondition = NonNullable<Step2Data["health_conditions"]>[number];
  const handleHealthConditionsChange = (values: string[]) => {
    const typed = values as HealthCondition[];
    if (typed.includes("none") && !healthConditions.includes("none")) {
      // "None" was just selected -- clear others
      setValue("health_conditions", ["none"]);
    } else if (typed.includes("none") && typed.length > 1) {
      // Another condition selected while "None" was active -- remove "None"
      setValue(
        "health_conditions",
        typed.filter((v) => v !== "none")
      );
    } else {
      setValue("health_conditions", typed);
    }
  };

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
        <h1 className="text-2xl font-bold">Health & Medications</h1>
        <p className="text-muted-foreground mt-1">
          Contextualises your biometric data, flags relevant interactions, and
          applies condition-specific evidence. All fields are optional.
        </p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
      >
        {/* Health Conditions */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Health Conditions</CardTitle>
            <CardDescription>
              Select any existing conditions. Choose &quot;None&quot; if you have
              no diagnosed conditions.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <FieldGroup
              label="Existing Health Conditions"
              error={errors.health_conditions?.message as string}
            >
              <MultiSelect
                options={HEALTH_CONDITIONS_OPTIONS}
                value={healthConditions}
                onChange={handleHealthConditionsChange}
              />
            </FieldGroup>

            <FieldGroup
              label="Injury History / Surgeries / Clinical Context"
              description="Any relevant clinical history"
              error={errors.injury_history_text?.message as string}
            >
              <Textarea
                placeholder="e.g. ACL reconstruction 2023, chronic lower back issues..."
                {...register("injury_history_text")}
              />
            </FieldGroup>

            <FieldGroup
              label="Current Medications"
              error={errors.current_medications?.message as string}
            >
              <Textarea
                placeholder="e.g. Levothyroxine 50mcg, Metformin 500mg..."
                {...register("current_medications")}
              />
            </FieldGroup>

            <FieldGroup
              label="Smoking / Vaping Status"
              error={errors.smoking_status?.message as string}
            >
              <Controller
                name="smoking_status"
                control={control}
                render={({ field }) => (
                  <RadioGroup
                    value={field.value ?? ""}
                    onValueChange={field.onChange}
                    className="flex flex-wrap gap-3"
                  >
                    {SMOKING_OPTIONS.map((option) => (
                      <div key={option.value} className="flex items-center gap-2">
                        <RadioGroupItem
                          value={option.value}
                          id={`smoke-${option.value}`}
                        />
                        <Label
                          htmlFor={`smoke-${option.value}`}
                          className="font-normal cursor-pointer text-sm"
                        >
                          {option.label}
                        </Label>
                      </div>
                    ))}
                  </RadioGroup>
                )}
              />
            </FieldGroup>
          </CardContent>
        </Card>

        {/* Recovery */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Recovery Modalities</CardTitle>
          </CardHeader>
          <CardContent>
            <FieldGroup
              label="Recovery Modalities Used"
              description="Select all that apply"
              error={errors.recovery_modalities?.message as string}
            >
              <Controller
                name="recovery_modalities"
                control={control}
                render={({ field }) => (
                  <MultiSelect
                    options={RECOVERY_MODALITIES_OPTIONS}
                    value={field.value ?? []}
                    onChange={field.onChange}
                    columns={2}
                  />
                )}
              />
            </FieldGroup>
          </CardContent>
        </Card>

        {/* Supplementation */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Supplementation</CardTitle>
            <CardDescription>
              Select your current supplements across 8 categories, or check
              &quot;No supplements&quot; if you are not taking any.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <Controller
              name="supplements"
              control={control}
              render={({ field }) => (
                <SupplementPicker
                  value={field.value}
                  onChange={field.onChange}
                  noSupplements={noSupplements}
                  onNoSupplementsChange={(checked) =>
                    setValue("no_supplements", checked)
                  }
                />
              )}
            />

            <FieldGroup
              label="Other Supplements / Dosages / Brands"
              description="Any supplements not listed above, with dosages and brands"
              error={errors.other_supplements_text?.message as string}
            >
              <Textarea
                placeholder="e.g. AG1 daily, custom B12 methylcobalamin 5000mcg..."
                {...register("other_supplements_text")}
              />
            </FieldGroup>
          </CardContent>
        </Card>

        <StepNavigation
          currentStep={2}
          onSubmit={onSubmit}
          isSubmitting={isSubmitting}
          canSkip={true}
        />
      </form>
    </div>
  );
}
