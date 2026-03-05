"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

interface StepNavigationProps {
  currentStep: number;
  totalSteps?: number;
  onSubmit: () => void;
  isSubmitting: boolean;
  canSkip?: boolean;
}

/**
 * Step navigation with Back, Next/Complete, and optional "Skip for now" buttons.
 *
 * - Back button is hidden on step 1.
 * - Final step shows "Complete" instead of "Next".
 * - "Skip for now" ghost button navigates forward without saving.
 */
export function StepNavigation({
  currentStep,
  totalSteps = 6,
  onSubmit,
  isSubmitting,
  canSkip = true,
}: StepNavigationProps) {
  const router = useRouter();

  const isLastStep = currentStep === totalSteps;

  return (
    <div className="flex justify-between pt-6 border-t border-border/40">
      {currentStep > 1 ? (
        <Button
          type="button"
          variant="outline"
          onClick={() => router.push(`/onboarding/step-${currentStep - 1}`)}
          disabled={isSubmitting}
        >
          Back
        </Button>
      ) : (
        <div />
      )}

      <div className="flex gap-2">
        {canSkip && !isLastStep && (
          <Button
            type="button"
            variant="ghost"
            onClick={() => router.push(`/onboarding/step-${currentStep + 1}`)}
            disabled={isSubmitting}
          >
            Skip for now
          </Button>
        )}
        <Button type="button" onClick={onSubmit} disabled={isSubmitting}>
          {isSubmitting
            ? "Saving..."
            : isLastStep
              ? "Complete"
              : "Next"}
        </Button>
      </div>
    </div>
  );
}
