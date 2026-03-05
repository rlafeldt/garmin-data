import { NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Target markers for lab value extraction.
 * 20 common health markers relevant to the 5 BioIntelligence domains.
 */
const TARGET_MARKERS = [
  "Vitamin D (25-OH)",
  "Vitamin B12",
  "Ferritin",
  "Iron",
  "TSH",
  "Free T3",
  "Free T4",
  "Total Cholesterol",
  "LDL",
  "HDL",
  "Triglycerides",
  "Fasting Glucose",
  "HbA1c",
  "Total Testosterone",
  "Free Testosterone",
  "Cortisol",
  "CRP (hs-CRP)",
  "Magnesium",
  "Zinc",
  "Omega-3 Index",
];

interface ExtractedValue {
  marker_name: string;
  value: number | null;
  unit: string;
  reference_range: string | null;
  confidence: number;
}

interface RequestBody {
  file_path: string;
  file_type: string;
  profile_id: string;
}

/**
 * Server-side Supabase client using the service role key.
 * This client bypasses RLS and is safe for server-side use only.
 */
function getServiceSupabase() {
  const url = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !key) {
    throw new Error(
      "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables"
    );
  }

  return createClient(url, key);
}

/**
 * POST /api/extract-lab
 *
 * Accepts: { file_path, file_type, profile_id }
 *
 * Downloads the file from Supabase Storage, calls Anthropic API
 * (claude-haiku-4-5-20251001) for extraction, updates lab_results
 * table with extracted values.
 */
export async function POST(request: Request) {
  try {
    const body: RequestBody = await request.json();
    const { file_path, file_type, profile_id } = body;

    if (!file_path || !file_type || !profile_id) {
      return NextResponse.json(
        { error: "Missing required fields: file_path, file_type, profile_id" },
        { status: 400 }
      );
    }

    // Validate API key exists
    const anthropicApiKey = process.env.ANTHROPIC_API_KEY;
    if (!anthropicApiKey) {
      return NextResponse.json(
        { error: "ANTHROPIC_API_KEY not configured" },
        { status: 500 }
      );
    }

    // Download file from Supabase Storage
    const supabase = getServiceSupabase();
    const { data: fileData, error: downloadError } = await supabase.storage
      .from("lab-uploads")
      .download(file_path);

    if (downloadError || !fileData) {
      await updateLabStatus(supabase, file_path, "failed");
      return NextResponse.json(
        { error: `Failed to download file: ${downloadError?.message || "unknown error"}` },
        { status: 500 }
      );
    }

    // Convert file to base64
    const arrayBuffer = await fileData.arrayBuffer();
    const base64Data = Buffer.from(arrayBuffer).toString("base64");

    // Build content block based on file type
    const contentBlock = buildContentBlock(file_type, base64Data);

    // Call Anthropic API for extraction
    const client = new Anthropic({ apiKey: anthropicApiKey });

    const message = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 2048,
      messages: [
        {
          role: "user",
          content: [
            contentBlock,
            {
              type: "text",
              text: `Extract lab values from this document.
Target markers: ${TARGET_MARKERS.join(", ")}
For each found marker, return: marker_name, value (numeric), unit, reference_range.
Assign a confidence score (0.0-1.0) for each extraction.
Return a JSON array matching this schema: [{"marker_name": string, "value": number | null, "unit": string, "reference_range": string | null, "confidence": number}]
Only extract markers you can clearly identify. Skip unclear values.
Return ONLY the JSON array, no additional text.`,
            },
          ],
        },
      ],
    });

    // Parse response
    const responseText =
      message.content[0].type === "text" ? message.content[0].text : "";

    let extractedValues: ExtractedValue[];
    try {
      // Try to parse the response, handling potential markdown code blocks
      const jsonStr = responseText
        .replace(/```json\n?/g, "")
        .replace(/```\n?/g, "")
        .trim();
      extractedValues = JSON.parse(jsonStr);
    } catch {
      await updateLabStatus(supabase, file_path, "failed");
      return NextResponse.json(
        { error: "Failed to parse extraction response" },
        { status: 500 }
      );
    }

    // Validate extracted values structure
    extractedValues = extractedValues.map((v) => ({
      marker_name: String(v.marker_name || ""),
      value: typeof v.value === "number" ? v.value : null,
      unit: String(v.unit || ""),
      reference_range: v.reference_range ? String(v.reference_range) : null,
      confidence: typeof v.confidence === "number" ? v.confidence : 0.5,
    }));

    // Update lab_results table
    const { error: updateError } = await supabase
      .from("lab_results")
      .update({
        extraction_status: "extracted",
        extracted_values: extractedValues,
      })
      .eq("file_path", file_path);

    if (updateError) {
      console.error("Failed to update lab_results:", updateError);
    }

    return NextResponse.json({ values: extractedValues });
  } catch (err) {
    console.error("Lab extraction error:", err);

    // Try to update status to failed
    try {
      const body: RequestBody = await request.clone().json();
      const supabase = getServiceSupabase();
      await updateLabStatus(supabase, body.file_path, "failed");
    } catch {
      // Best-effort status update
    }

    const errorMessage =
      err instanceof Error ? err.message : "Internal server error";
    return NextResponse.json({ error: errorMessage }, { status: 500 });
  }
}

/**
 * Build the appropriate content block for Anthropic API based on file type.
 * PDFs use document type, images use image type.
 */
function buildContentBlock(
  fileType: string,
  base64Data: string
): Anthropic.DocumentBlockParam | Anthropic.ImageBlockParam {
  if (fileType === "application/pdf") {
    return {
      type: "document",
      source: {
        type: "base64",
        media_type: "application/pdf",
        data: base64Data,
      },
    };
  }

  // Image types: jpeg, png
  const mediaType = fileType as "image/jpeg" | "image/png" | "image/gif" | "image/webp";
  return {
    type: "image",
    source: {
      type: "base64",
      media_type: mediaType,
      data: base64Data,
    },
  };
}

/**
 * Update lab_results extraction status.
 */
async function updateLabStatus(
  supabaseClient: SupabaseClient,
  filePath: string,
  status: string
) {
  await supabaseClient
    .from("lab_results")
    .update({ extraction_status: status })
    .eq("file_path", filePath);
}
