import { z } from "zod";

/**
 * Step 6: Data Upload & Informed Consent
 *
 * Historical data upload, lab results, and legal acknowledgement.
 *
 * This schema covers only the free-text additional context field.
 * Consent checkboxes are handled by the page component directly and stored
 * in the consent_records table -- they are not part of this Zod schema
 * because consent is a separate audit-trailed concern.
 *
 * Lab result file uploads are handled via Supabase Storage and the
 * lab_results table, not through this schema.
 */
export const step6Schema = z.object({
  additional_context: z
    .string()
    .max(2000, "Maximum 2000 characters")
    .optional(),
});

export type Step6Data = z.infer<typeof step6Schema>;
