"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { calculateCompleteness } from "@/lib/completeness";
import type { OnboardingProfile, CompletenessResult } from "@/lib/types";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Check, Circle, ArrowRight } from "lucide-react";

const STEP_NAMES = [
  "Biological Profile",
  "Health & Medications",
  "Metabolic & Nutrition",
  "Training & Sleep",
  "Baseline Biometrics",
  "Data Upload & Consent",
] as const;

/**
 * Onboarding Completion Page
 *
 * Congratulatory page with BioIntelligence branding showing:
 * - Profile completeness summary via calculateCompleteness()
 * - Completed steps with checkmarks, incomplete with "Complete later" links
 * - Overall completion percentage bar
 * - Messaging about next steps
 */
export default function CompletePage() {
  const [profile, setProfile] = useState<OnboardingProfile | null>(null);
  const [completeness, setCompleteness] = useState<CompletenessResult | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadProfile() {
      try {
        const { data, error } = await supabase
          .from("onboarding_profiles")
          .select("*")
          .limit(1)
          .single();

        if (error && error.code !== "PGRST116") {
          console.error("Failed to load profile:", error);
          setIsLoading(false);
          return;
        }

        if (data) {
          const profileData = data as unknown as OnboardingProfile;
          setProfile(profileData);
          setCompleteness(calculateCompleteness(profileData));
        }
      } catch (err) {
        console.error("Error loading profile:", err);
      } finally {
        setIsLoading(false);
      }
    }

    loadProfile();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    );
  }

  const hasSkippedSteps =
    completeness && completeness.incompleteSteps.length > 0;

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      {/* Congratulations header */}
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">
            Profile Complete
          </CardTitle>
          <CardDescription className="text-base">
            Your profile is ready. BioIntelligence will use this data to
            personalise your Daily Protocol.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Completeness bar */}
          {completeness && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Profile completeness</span>
                <span className="font-medium">{completeness.percentage}%</span>
              </div>
              <Progress value={completeness.percentage} />
              <p className="text-xs text-muted-foreground text-center">
                {completeness.completedSteps} of {completeness.totalSteps} steps
                completed
              </p>
            </div>
          )}

          {/* Step status list */}
          <div className="space-y-2">
            {STEP_NAMES.map((name, index) => {
              const stepNumber = index + 1;
              const stepCompleteKey = `step_${stepNumber}_complete` as keyof OnboardingProfile;
              const isComplete = profile
                ? profile[stepCompleteKey] === true
                : false;

              return (
                <div
                  key={stepNumber}
                  className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-muted/50"
                >
                  <div className="flex items-center gap-3">
                    {isComplete ? (
                      <Check className="w-5 h-5 text-green-600 dark:text-green-400" />
                    ) : (
                      <Circle className="w-5 h-5 text-muted-foreground" />
                    )}
                    <span
                      className={
                        isComplete
                          ? "text-sm"
                          : "text-sm text-muted-foreground"
                      }
                    >
                      Step {stepNumber}: {name}
                    </span>
                  </div>
                  {!isComplete && (
                    <Link href={`/onboarding/step-${stepNumber}`}>
                      <Button variant="ghost" size="sm" className="text-xs gap-1">
                        Complete later
                        <ArrowRight className="w-3 h-3" />
                      </Button>
                    </Link>
                  )}
                </div>
              );
            })}
          </div>

          {/* Skipped steps message */}
          {hasSkippedSteps && (
            <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-3 text-sm text-blue-800 dark:border-blue-900/50 dark:bg-blue-950/20 dark:text-blue-300">
              You skipped some optional sections. You can complete them anytime
              from your profile page, or we will remind you via WhatsApp when
              more data would improve your insights.
            </div>
          )}

          {/* Action buttons */}
          <div className="flex flex-col gap-3 pt-2">
            <Link href="/profile" className="w-full">
              <Button className="w-full gap-2" variant="outline">
                View & Edit Profile
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Medical disclaimer */}
      <p className="text-xs text-muted-foreground text-center px-4">
        BioIntelligence is an AI research tool. It does not provide medical
        diagnoses, prescribe treatments, or replace clinical care. All insights
        are grounded in published scientific literature applied to your
        individual data.
      </p>
    </div>
  );
}
