"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabase";
import { calculateCompleteness } from "@/lib/completeness";
import type {
  OnboardingProfile,
  CompletenessResult,
  LabResult,
} from "@/lib/types";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Check,
  Circle,
  Pencil,
  FileText,
  Upload,
  ShieldCheck,
} from "lucide-react";

const STEP_INFO = [
  { name: "Biological Profile", summaryKeys: ["age", "biological_sex", "height_cm", "weight_kg", "primary_sport"] },
  { name: "Health & Medications", summaryKeys: ["health_conditions", "smoking_status"] },
  { name: "Metabolic & Nutrition", summaryKeys: ["dietary_pattern", "pre_training_nutrition"] },
  { name: "Training & Sleep", summaryKeys: ["current_training_phase", "chronotype"] },
  { name: "Baseline Biometrics", summaryKeys: ["hrv_rmssd", "resting_hr", "vo2_max"] },
  { name: "Data Upload & Consent", summaryKeys: ["additional_context"] },
] as const;

/**
 * Format step data values for display in profile summary cards.
 */
function formatStepSummary(
  stepNumber: number,
  data: Record<string, unknown>
): string {
  if (!data || Object.keys(data).length === 0) return "No data entered";

  const info = STEP_INFO[stepNumber - 1];
  const parts: string[] = [];

  for (const key of info.summaryKeys) {
    const val = data[key];
    if (val !== undefined && val !== null && val !== "") {
      const label = key
        .replace(/_/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());

      if (Array.isArray(val)) {
        parts.push(`${label}: ${val.length} selected`);
      } else if (typeof val === "object") {
        const count = Object.values(val as Record<string, unknown[]>).flat()
          .length;
        parts.push(`${label}: ${count} items`);
      } else {
        parts.push(`${label}: ${String(val)}`);
      }
    }
  }

  return parts.length > 0 ? parts.join(", ") : "Data entered";
}

/**
 * Profile Page (ONBD-05)
 *
 * Profile edit/view page allowing updates to any step after initial onboarding.
 * Shows each step as a card with completion status and summary.
 * Can be deep-linked from WhatsApp nudges.
 */
export default function ProfilePage() {
  const [profile, setProfile] = useState<OnboardingProfile | null>(null);
  const [completeness, setCompleteness] = useState<CompletenessResult | null>(
    null
  );
  const [labResults, setLabResults] = useState<LabResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        // Load profile
        const { data: profileData, error: profileError } = await supabase
          .from("onboarding_profiles")
          .select("*")
          .limit(1)
          .single();

        if (profileError && profileError.code !== "PGRST116") {
          console.error("Failed to load profile:", profileError);
        }

        if (profileData) {
          const typedProfile = profileData as unknown as OnboardingProfile;
          setProfile(typedProfile);
          setCompleteness(calculateCompleteness(typedProfile));

          // Load lab results
          const { data: labData } = await supabase
            .from("lab_results")
            .select("*")
            .eq("profile_id", profileData.id)
            .order("created_at", { ascending: false });

          if (labData) {
            setLabResults(labData as unknown as LabResult[]);
          }
        }
      } catch (err) {
        console.error("Error loading profile data:", err);
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-sm text-muted-foreground">Loading profile...</p>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-4">
        <p className="text-sm text-muted-foreground">
          No profile found. Start onboarding to create your profile.
        </p>
        <Link href="/onboarding/step-1">
          <Button>Start Onboarding</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      {/* Header with completeness */}
      <div className="space-y-3">
        <h1 className="text-2xl font-semibold">Your Profile</h1>
        {completeness && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">
                Profile completeness
              </span>
              <span className="font-medium">{completeness.percentage}%</span>
            </div>
            <Progress value={completeness.percentage} />
          </div>
        )}
      </div>

      {/* Step cards */}
      <div className="space-y-3">
        {STEP_INFO.map((info, index) => {
          const stepNumber = index + 1;
          const profileRecord = profile as unknown as Record<string, unknown>;
          const isComplete = profileRecord[`step_${stepNumber}_complete`] === true;
          const stepData =
            (profileRecord[`step_${stepNumber}_data`] as Record<string, unknown>) || {};

          return (
            <Card key={stepNumber}>
              <CardContent className="py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 min-w-0">
                    {isComplete ? (
                      <Check className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5 shrink-0" />
                    ) : (
                      <Circle className="w-5 h-5 text-muted-foreground mt-0.5 shrink-0" />
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-medium">
                        Step {stepNumber}: {info.name}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5 truncate">
                        {isComplete
                          ? formatStepSummary(stepNumber, stepData)
                          : "Incomplete"}
                      </p>
                    </div>
                  </div>
                  <Link href={`/onboarding/step-${stepNumber}`}>
                    <Button
                      variant="outline"
                      size="sm"
                      className="shrink-0 gap-1"
                    >
                      <Pencil className="w-3 h-3" />
                      Edit
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Lab results section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Lab Results
          </CardTitle>
          <CardDescription>
            Uploaded lab results and their extraction status
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {labResults.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No lab results uploaded yet.
            </p>
          ) : (
            labResults.map((lab) => (
              <div
                key={lab.id}
                className="flex items-center justify-between py-2 px-3 rounded-lg border"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <FileText className="w-4 h-4 text-muted-foreground shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm truncate">{lab.file_path.split("/").pop()}</p>
                    <p className="text-xs text-muted-foreground">
                      {lab.upload_date} -- {lab.extraction_status}
                    </p>
                  </div>
                </div>
                {lab.extraction_status === "confirmed" && (
                  <span className="text-xs text-green-600 dark:text-green-400 font-medium">
                    {lab.confirmed_values.length} markers
                  </span>
                )}
              </div>
            ))
          )}

          <Link href="/onboarding/step-6" className="block">
            <Button variant="outline" size="sm" className="gap-2 w-full">
              <Upload className="w-4 h-4" />
              Upload New Lab Results
            </Button>
          </Link>
        </CardContent>
      </Card>

      {/* Consent status */}
      {profile.onboarding_complete && (
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <ShieldCheck className="w-5 h-5 text-green-600 dark:text-green-400 shrink-0" />
              <div>
                <p className="text-sm font-medium">Informed Consent</p>
                <p className="text-xs text-muted-foreground">
                  All three consent checkboxes acknowledged
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Medical disclaimer */}
      <p className="text-xs text-muted-foreground text-center px-4 pb-6">
        BioIntelligence is an AI research tool. It does not provide medical
        diagnoses, prescribe treatments, or replace clinical care. All insights
        are grounded in published scientific literature applied to your
        individual data.
      </p>
    </div>
  );
}
