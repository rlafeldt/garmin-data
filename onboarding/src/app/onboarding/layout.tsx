"use client";

import { usePathname } from "next/navigation";
import { StepProgress } from "@/components/onboarding/step-progress";

/**
 * Onboarding layout wrapper with step progress indicator.
 * Reads the current step number from the URL path segment.
 */
export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  // Extract step number from /onboarding/step-N
  const stepMatch = pathname.match(/step-(\d+)/);
  const currentStep = stepMatch ? parseInt(stepMatch[1], 10) : 1;

  return (
    <div className="flex flex-col gap-6">
      <StepProgress currentStep={currentStep} />
      {children}
    </div>
  );
}
