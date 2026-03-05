"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

const STEP_NAMES = [
  "Biological Profile",
  "Health & Medications",
  "Metabolic & Nutrition",
  "Training & Sleep",
  "Baseline Biometrics",
  "Data Upload & Consent",
] as const;

interface StepProgressProps {
  currentStep: number;
  completedSteps?: number[];
}

/**
 * Visual progress indicator showing "Step X of 6" with step names.
 * Highlights the current step, shows completed steps with a checkmark,
 * and renders skipped steps as accessible but muted.
 */
export function StepProgress({
  currentStep,
  completedSteps = [],
}: StepProgressProps) {
  return (
    <div className="w-full">
      <p className="text-sm font-medium text-muted-foreground mb-3">
        Step {currentStep} of {STEP_NAMES.length}:{" "}
        <span className="text-foreground">
          {STEP_NAMES[currentStep - 1]}
        </span>
      </p>

      {/* Step indicators - horizontal layout */}
      <div className="flex items-center gap-1">
        {STEP_NAMES.map((name, index) => {
          const stepNumber = index + 1;
          const isCurrent = stepNumber === currentStep;
          const isCompleted = completedSteps.includes(stepNumber);

          return (
            <div key={stepNumber} className="flex items-center flex-1">
              {/* Step circle */}
              <div
                className={cn(
                  "flex items-center justify-center w-8 h-8 rounded-full text-xs font-medium shrink-0 transition-colors",
                  isCurrent &&
                    "bg-primary text-primary-foreground ring-2 ring-primary/20",
                  isCompleted &&
                    !isCurrent &&
                    "bg-primary/10 text-primary",
                  !isCurrent &&
                    !isCompleted &&
                    "bg-muted text-muted-foreground"
                )}
                title={name}
              >
                {isCompleted && !isCurrent ? (
                  <Check className="w-4 h-4" />
                ) : (
                  stepNumber
                )}
              </div>

              {/* Connector line (not after last step) */}
              {stepNumber < STEP_NAMES.length && (
                <div
                  className={cn(
                    "h-0.5 flex-1 mx-1",
                    isCompleted ? "bg-primary/30" : "bg-muted"
                  )}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Step name for current step on mobile */}
      <div className="mt-2 hidden sm:flex justify-between">
        {STEP_NAMES.map((name, index) => (
          <span
            key={index}
            className={cn(
              "text-[10px] text-center flex-1",
              index + 1 === currentStep
                ? "text-foreground font-medium"
                : "text-muted-foreground"
            )}
          >
            {name}
          </span>
        ))}
      </div>
    </div>
  );
}
