"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  useForm,
  type UseFormReturn,
  type DefaultValues,
  type FieldValues,
  type Resolver,
} from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import type { ZodType } from "zod";
import { supabase } from "@/lib/supabase";

interface UseStepFormOptions<T extends FieldValues> {
  /** Zod schema for validation */
  schema: ZodType<T>;
  /** Step number (1-6) */
  stepNumber: number;
  /** Default values when no saved data exists */
  defaultValues?: DefaultValues<T>;
}

interface UseStepFormReturn<T extends FieldValues> {
  form: UseFormReturn<T>;
  onSubmit: () => void;
  isLoading: boolean;
  isSubmitting: boolean;
  profileId: string | null;
}

/**
 * Custom hook encapsulating react-hook-form + Supabase load/save pattern.
 *
 * On mount: queries `onboarding_profiles` for existing step data,
 * uses RHF `reset()` to populate form with saved values.
 *
 * On submit: upserts to `onboarding_profiles` with step data and
 * completion flag, then navigates to next step.
 *
 * Single-row pattern: always queries with `.limit(1)`, creates row
 * on first save if none exists.
 */
export function useStepForm<T extends FieldValues>({
  schema,
  stepNumber,
  defaultValues,
}: UseStepFormOptions<T>): UseStepFormReturn<T> {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [profileId, setProfileId] = useState<string | null>(null);
  const loadedRef = useRef(false);

  const form = useForm<T>({
    // zod v4 types are structurally compatible but nominally incompatible with @hookform/resolvers declarations
    resolver: zodResolver(schema as unknown as Parameters<typeof zodResolver>[0]) as Resolver<T>,
    defaultValues: defaultValues as DefaultValues<T>,
  });

  // Load existing data on mount
  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;

    async function loadExisting() {
      try {
        const { data, error } = await supabase
          .from("onboarding_profiles")
          .select("*")
          .limit(1)
          .single();

        if (error && error.code !== "PGRST116") {
          // PGRST116 = no rows returned, which is expected for new users
          console.error("Failed to load profile:", error);
          setIsLoading(false);
          return;
        }

        if (data) {
          setProfileId(data.id);
          const stepDataKey = `step_${stepNumber}_data` as keyof typeof data;
          const stepData = data[stepDataKey];
          if (
            stepData &&
            typeof stepData === "object" &&
            Object.keys(stepData as Record<string, unknown>).length > 0
          ) {
            form.reset(stepData as T);
          }
        }
      } catch (err) {
        console.error("Error loading profile:", err);
      } finally {
        setIsLoading(false);
      }
    }

    loadExisting();
  }, [stepNumber, form]);

  const onSubmit = useCallback(() => {
    form.handleSubmit(async (values: T) => {
      try {
        const stepDataKey = `step_${stepNumber}_data`;
        const stepCompleteKey = `step_${stepNumber}_complete`;
        const payload = {
          [stepDataKey]: values,
          [stepCompleteKey]: true,
          updated_at: new Date().toISOString(),
        };

        if (profileId) {
          // Update existing row
          const { error } = await supabase
            .from("onboarding_profiles")
            .update(payload)
            .eq("id", profileId);
          if (error) throw error;
        } else {
          // Create new row
          const { data, error } = await supabase
            .from("onboarding_profiles")
            .insert(payload)
            .select("id")
            .single();
          if (error) throw error;
          if (data) setProfileId(data.id);
        }

        // Navigate to next step (or complete page for step 6)
        if (stepNumber < 6) {
          router.push(`/onboarding/step-${stepNumber + 1}`);
        } else {
          router.push("/onboarding/complete");
        }
      } catch (err) {
        console.error("Failed to save step data:", err);
      }
    })();
  }, [form, stepNumber, profileId, router]);

  return {
    form,
    onSubmit,
    isLoading,
    isSubmitting: form.formState.isSubmitting,
    profileId,
  };
}
