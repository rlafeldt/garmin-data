"use client";

import { useState, useCallback } from "react";
import { useStepForm } from "@/hooks/use-step-form";
import { step6Schema } from "@/lib/schemas/step-6";
import { FieldGroup } from "@/components/onboarding/field-group";
import { LabUpload } from "@/components/onboarding/lab-upload";
import {
  ConsentCheckboxes,
  allConsentsGiven,
  type ConsentValues,
} from "@/components/onboarding/consent-checkboxes";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { supabase } from "@/lib/supabase";
import { useRouter } from "next/navigation";

const CONSENT_TEXTS: Record<keyof ConsentValues, string> = {
  ai_disclaimer:
    "I understand that BioIntelligence is an AI research tool that synthesises peer-reviewed scientific literature. It does not provide medical diagnoses, prescribe treatments, or replace the advice of a qualified healthcare practitioner.",
  data_processing:
    "I consent to my health and biometric data being processed to generate personalised insights. My data will not be sold or shared with third parties.",
  clinical_evaluation:
    "I understand that all insights reflect the application of scientific literature to my individual data, and that I should seek clinical evaluation for any health concerns raised by these insights.",
};

/**
 * Step 6: Data Upload & Informed Consent
 *
 * Two sections:
 * 1. Upload: Lab results/bloodwork upload + additional context textarea
 * 2. Consent: Three required consent checkboxes (ONBD-04)
 *
 * Lab upload is optional, but consent is mandatory.
 * Consent values are stored separately in consent_records table.
 */
export default function Step6Page() {
  const router = useRouter();
  const { form, isLoading, isSubmitting: formSubmitting, profileId } =
    useStepForm({
      schema: step6Schema,
      stepNumber: 6,
    });

  const {
    register,
    formState: { errors },
  } = form;

  const [consent, setConsent] = useState<ConsentValues>({
    ai_disclaimer: false,
    data_processing: false,
    clinical_evaluation: false,
  });

  const [consentError, setConsentError] = useState<string | null>(null);
  const [isCompleting, setIsCompleting] = useState(false);

  const onComplete = useCallback(async () => {
    // Validate consent
    if (!allConsentsGiven(consent)) {
      setConsentError(
        "All three consent checkboxes must be checked to complete onboarding."
      );
      return;
    }
    setConsentError(null);

    // Validate and save the text form data
    const isValid = await form.trigger();
    if (!isValid) return;

    setIsCompleting(true);

    try {
      const values = form.getValues();

      // Save step 6 data (additional context)
      const stepPayload = {
        step_6_data: values,
        step_6_complete: true,
        onboarding_complete: true,
        updated_at: new Date().toISOString(),
      };

      if (profileId) {
        const { error } = await supabase
          .from("onboarding_profiles")
          .update(stepPayload)
          .eq("id", profileId);
        if (error) throw error;
      } else {
        const { error } = await supabase
          .from("onboarding_profiles")
          .insert(stepPayload);
        if (error) throw error;
      }

      // Save consent records to consent_records table
      const consentRecords = (
        Object.entries(consent) as [keyof ConsentValues, boolean][]
      ).map(([key, value]) => ({
        profile_id: profileId,
        consent_type: key,
        consented: value,
        consent_text: CONSENT_TEXTS[key],
        consented_at: new Date().toISOString(),
      }));

      const { error: consentError } = await supabase
        .from("consent_records")
        .insert(consentRecords);

      if (consentError) {
        console.error("Failed to save consent records:", consentError);
        // Non-blocking: consent data is also captured in the completion flow
      }

      router.push("/onboarding/complete");
    } catch (err) {
      console.error("Failed to complete onboarding:", err);
    } finally {
      setIsCompleting(false);
    }
  }, [consent, form, profileId, router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    );
  }

  const isSubmitting = formSubmitting || isCompleting;

  return (
    <div className="space-y-6">
      {/* Upload Section */}
      <Card>
        <CardHeader>
          <CardTitle>Data Upload</CardTitle>
          <CardDescription>
            Upload lab results or bloodwork for AI-powered extraction. Values
            will be shown for your review before saving. This section is
            optional.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <LabUpload profileId={profileId} />

          <FieldGroup
            label="Additional Context"
            description="Recent life events, illness, travel, training blocks, race schedule, stressors that may affect your data"
          >
            <Textarea
              placeholder="e.g. Recovering from a cold last week, marathon training block started 3 weeks ago..."
              maxLength={2000}
              className="min-h-24"
              {...register("additional_context")}
            />
            {errors.additional_context && (
              <p className="text-xs text-destructive">
                {errors.additional_context.message}
              </p>
            )}
            <p className="text-xs text-muted-foreground text-right">
              Max 2000 characters
            </p>
          </FieldGroup>
        </CardContent>
      </Card>

      {/* Consent Section */}
      <Card>
        <CardHeader>
          <CardTitle>Informed Consent</CardTitle>
          <CardDescription>
            Please read and acknowledge the following before completing
            onboarding. All three checkboxes are required.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ConsentCheckboxes values={consent} onChange={setConsent} />
          {consentError && (
            <p className="text-sm text-destructive mt-3">{consentError}</p>
          )}
        </CardContent>
      </Card>

      {/* Navigation -- Complete button disabled without all consents */}
      <div className="flex justify-between pt-6 border-t border-border/40">
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2"
          onClick={() => router.push("/onboarding/step-5")}
          disabled={isSubmitting}
        >
          Back
        </button>
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2 disabled:pointer-events-none disabled:opacity-50"
          onClick={onComplete}
          disabled={isSubmitting || !allConsentsGiven(consent)}
        >
          {isSubmitting ? "Completing..." : "Complete Onboarding"}
        </button>
      </div>
    </div>
  );
}
