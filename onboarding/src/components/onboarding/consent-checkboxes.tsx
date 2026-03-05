"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";

export interface ConsentValues {
  ai_disclaimer: boolean;
  data_processing: boolean;
  clinical_evaluation: boolean;
}

interface ConsentCheckboxesProps {
  values: ConsentValues;
  onChange: (values: ConsentValues) => void;
}

const CONSENT_ITEMS: {
  key: keyof ConsentValues;
  text: string;
}[] = [
  {
    key: "ai_disclaimer",
    text: "I understand that BioIntelligence is an AI research tool that synthesises peer-reviewed scientific literature. It does not provide medical diagnoses, prescribe treatments, or replace the advice of a qualified healthcare practitioner.",
  },
  {
    key: "data_processing",
    text: "I consent to my health and biometric data being processed to generate personalised insights. My data will not be sold or shared with third parties.",
  },
  {
    key: "clinical_evaluation",
    text: "I understand that all insights reflect the application of scientific literature to my individual data, and that I should seek clinical evaluation for any health concerns raised by these insights.",
  },
];

/**
 * Returns true only when all 3 consent checkboxes are checked.
 */
export function allConsentsGiven(values: ConsentValues): boolean {
  return (
    values.ai_disclaimer &&
    values.data_processing &&
    values.clinical_evaluation
  );
}

/**
 * Three informed consent checkboxes with exact text from CONTEXT.md.
 * Visual indicator (green border) when all 3 are checked.
 */
export function ConsentCheckboxes({
  values,
  onChange,
}: ConsentCheckboxesProps) {
  const allChecked = allConsentsGiven(values);

  function handleChange(key: keyof ConsentValues, checked: boolean) {
    onChange({ ...values, [key]: checked });
  }

  return (
    <div
      className={cn(
        "space-y-4 rounded-lg border-2 p-4 transition-colors",
        allChecked
          ? "border-green-500/50 bg-green-50/30 dark:bg-green-950/10"
          : "border-border"
      )}
    >
      <p className="text-sm font-medium">
        Informed Consent{" "}
        <span className="text-destructive">*</span>
      </p>
      <p className="text-xs text-muted-foreground">
        All three checkboxes must be checked to complete onboarding.
      </p>

      {CONSENT_ITEMS.map((item) => (
        <div key={item.key} className="flex items-start gap-3">
          <Checkbox
            id={`consent-${item.key}`}
            checked={values[item.key]}
            onCheckedChange={(checked) =>
              handleChange(item.key, checked === true)
            }
            className="mt-1 shrink-0"
          />
          <label
            htmlFor={`consent-${item.key}`}
            className="text-sm leading-relaxed cursor-pointer select-none"
          >
            {item.text}
          </label>
        </div>
      ))}

      {allChecked && (
        <p className="text-xs text-green-600 dark:text-green-400 font-medium">
          All consents provided
        </p>
      )}
    </div>
  );
}
