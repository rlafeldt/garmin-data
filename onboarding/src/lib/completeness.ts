import type { OnboardingProfile, CompletenessResult } from "./types";

/**
 * Calculate onboarding profile completeness from step completion flags.
 *
 * Returns a percentage (0-100), count of completed steps, list of
 * incomplete step numbers, and the suggested next step to complete.
 */
export function calculateCompleteness(
  profile: OnboardingProfile
): CompletenessResult {
  const steps = [
    profile.step_1_complete,
    profile.step_2_complete,
    profile.step_3_complete,
    profile.step_4_complete,
    profile.step_5_complete,
    profile.step_6_complete,
  ];

  const completedSteps = steps.filter(Boolean).length;
  const incompleteSteps = steps
    .map((complete, i) => (complete ? null : i + 1))
    .filter((s): s is number => s !== null);

  return {
    percentage: Math.round((completedSteps / 6) * 100),
    completedSteps,
    totalSteps: 6,
    incompleteSteps,
    suggestedNextStep: incompleteSteps[0] ?? null,
  };
}
