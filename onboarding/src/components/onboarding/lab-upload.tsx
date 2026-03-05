"use client";

import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { supabase } from "@/lib/supabase";
import { cn } from "@/lib/utils";
import type { ExtractedLabValue } from "@/lib/types";
import { Upload, FileText, Loader2, Check, AlertCircle } from "lucide-react";

interface LabUploadFile {
  id: string;
  fileName: string;
  filePath: string;
  fileType: string;
  uploadDate: string;
  status: "uploading" | "extracting" | "review" | "confirmed" | "failed";
  extractedValues: ExtractedLabValue[];
  confirmedValues: ExtractedLabValue[];
  error?: string;
}

interface LabUploadProps {
  profileId: string | null;
}

const ACCEPTED_TYPES = "image/jpeg,image/png,application/pdf";
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

/**
 * File upload component for lab results.
 *
 * Accepts PDF and image files, uploads to Supabase Storage bucket
 * "lab-uploads", triggers extraction via /api/extract-lab, and
 * displays extracted values in editable fields for user review.
 */
export function LabUpload({ profileId }: LabUploadProps) {
  const [files, setFiles] = useState<LabUploadFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const selectedFiles = e.target.files;
    if (!selectedFiles || selectedFiles.length === 0) return;

    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      await processFile(file);
    }

    // Reset input so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  async function processFile(file: File) {
    // File size check
    if (file.size > MAX_FILE_SIZE) {
      const errorFile: LabUploadFile = {
        id: crypto.randomUUID(),
        fileName: file.name,
        filePath: "",
        fileType: file.type,
        uploadDate: new Date().toISOString().split("T")[0],
        status: "failed",
        extractedValues: [],
        confirmedValues: [],
        error: "File exceeds 10MB limit",
      };
      setFiles((prev) => [...prev, errorFile]);
      return;
    }

    const fileId = crypto.randomUUID();
    const ext = file.name.split(".").pop() || "bin";
    const storagePath = `${profileId || "anonymous"}/${Date.now()}.${ext}`;

    // Add file to list as uploading
    const newFile: LabUploadFile = {
      id: fileId,
      fileName: file.name,
      filePath: storagePath,
      fileType: file.type,
      uploadDate: new Date().toISOString().split("T")[0],
      status: "uploading",
      extractedValues: [],
      confirmedValues: [],
    };
    setFiles((prev) => [...prev, newFile]);

    try {
      // Upload to Supabase Storage
      const { error: uploadError } = await supabase.storage
        .from("lab-uploads")
        .upload(storagePath, file, {
          contentType: file.type,
          upsert: false,
        });

      if (uploadError) throw uploadError;

      // Create lab_results record
      if (profileId) {
        await supabase.from("lab_results").insert({
          profile_id: profileId,
          upload_date: newFile.uploadDate,
          file_path: storagePath,
          file_type: file.type,
          extraction_status: "pending",
        });
      }

      // Update status to extracting
      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileId ? { ...f, status: "extracting" as const } : f
        )
      );

      // Call extraction API
      const response = await fetch("/api/extract-lab", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          file_path: storagePath,
          file_type: file.type,
          profile_id: profileId,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.error || `Extraction failed (${response.status})`
        );
      }

      const result = await response.json();
      const extracted: ExtractedLabValue[] = result.values || [];

      // Update file with extracted values
      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileId
            ? {
                ...f,
                status: "review" as const,
                extractedValues: extracted,
                confirmedValues: extracted.map((v) => ({ ...v })),
              }
            : f
        )
      );
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Upload failed";
      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileId
            ? { ...f, status: "failed" as const, error: errorMessage }
            : f
        )
      );
    }
  }

  function updateConfirmedValue(
    fileId: string,
    index: number,
    field: keyof ExtractedLabValue,
    value: string | number | null
  ) {
    setFiles((prev) =>
      prev.map((f) => {
        if (f.id !== fileId) return f;
        const updated = [...f.confirmedValues];
        updated[index] = { ...updated[index], [field]: value };
        return { ...f, confirmedValues: updated };
      })
    );
  }

  function updateLabDate(fileId: string, date: string) {
    setFiles((prev) =>
      prev.map((f) => (f.id === fileId ? { ...f, uploadDate: date } : f))
    );
  }

  async function confirmValues(fileId: string) {
    const file = files.find((f) => f.id === fileId);
    if (!file || !profileId) return;

    try {
      // Save confirmed values to lab_results table
      await supabase
        .from("lab_results")
        .update({
          confirmed_values: file.confirmedValues,
          extraction_status: "confirmed",
          upload_date: file.uploadDate,
        })
        .eq("file_path", file.filePath);

      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileId ? { ...f, status: "confirmed" as const } : f
        )
      );
    } catch (err) {
      console.error("Failed to confirm values:", err);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          className="gap-2"
        >
          <Upload className="w-4 h-4" />
          Upload Lab Results
        </Button>
        <span className="text-xs text-muted-foreground">
          PDF, JPEG, or PNG (max 10MB)
        </span>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        onChange={handleFileSelect}
        className="hidden"
        multiple
      />

      {/* Uploaded files list */}
      {files.map((file) => (
        <div
          key={file.id}
          className="rounded-lg border p-4 space-y-3"
        >
          {/* File header */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <FileText className="w-4 h-4 shrink-0 text-muted-foreground" />
              <span className="text-sm font-medium truncate">
                {file.fileName}
              </span>
              <StatusBadge status={file.status} />
            </div>
            <div className="shrink-0">
              <Input
                type="date"
                value={file.uploadDate}
                onChange={(e) => updateLabDate(file.id, e.target.value)}
                className="w-40 h-8 text-xs"
                disabled={file.status === "confirmed"}
              />
            </div>
          </div>

          {/* Error message */}
          {file.error && (
            <div className="flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {file.error}
            </div>
          )}

          {/* Extracted values review */}
          {(file.status === "review" || file.status === "confirmed") &&
            file.confirmedValues.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">
                  Extracted Values ({file.confirmedValues.length} markers)
                </p>
                <div className="space-y-2">
                  {file.confirmedValues.map((val, idx) => (
                    <div
                      key={idx}
                      className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-2 items-center text-sm"
                    >
                      <Input
                        value={val.marker_name}
                        onChange={(e) =>
                          updateConfirmedValue(
                            file.id,
                            idx,
                            "marker_name",
                            e.target.value
                          )
                        }
                        className="h-8 text-xs"
                        disabled={file.status === "confirmed"}
                        placeholder="Marker"
                      />
                      <Input
                        type="number"
                        value={val.value ?? ""}
                        onChange={(e) =>
                          updateConfirmedValue(
                            file.id,
                            idx,
                            "value",
                            e.target.value ? Number(e.target.value) : null
                          )
                        }
                        className="h-8 w-20 text-xs"
                        disabled={file.status === "confirmed"}
                        placeholder="Value"
                      />
                      <Input
                        value={val.unit}
                        onChange={(e) =>
                          updateConfirmedValue(
                            file.id,
                            idx,
                            "unit",
                            e.target.value
                          )
                        }
                        className="h-8 w-20 text-xs"
                        disabled={file.status === "confirmed"}
                        placeholder="Unit"
                      />
                      <Input
                        value={val.reference_range ?? ""}
                        onChange={(e) =>
                          updateConfirmedValue(
                            file.id,
                            idx,
                            "reference_range",
                            e.target.value || null
                          )
                        }
                        className="h-8 w-28 text-xs"
                        disabled={file.status === "confirmed"}
                        placeholder="Ref range"
                      />
                      <ConfidenceDot confidence={val.confidence} />
                    </div>
                  ))}
                </div>

                {file.status === "review" && (
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => confirmValues(file.id)}
                    className="mt-2 gap-1"
                  >
                    <Check className="w-3 h-3" />
                    Confirm Values
                  </Button>
                )}
              </div>
            )}

          {/* Loading indicators */}
          {file.status === "uploading" && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" />
              Uploading...
            </div>
          )}
          {file.status === "extracting" && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin" />
              Extracting lab values...
            </div>
          )}
        </div>
      ))}

      {files.length === 0 && (
        <p className="text-xs text-muted-foreground">
          Upload lab results or bloodwork (PDF or image). Values will be
          extracted automatically and shown for your review before saving.
        </p>
      )}
    </div>
  );
}

function StatusBadge({
  status,
}: {
  status: LabUploadFile["status"];
}) {
  const styles: Record<LabUploadFile["status"], string> = {
    uploading: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
    extracting: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
    review: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
    confirmed: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
    failed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  };

  const labels: Record<LabUploadFile["status"], string> = {
    uploading: "Uploading",
    extracting: "Extracting",
    review: "Review",
    confirmed: "Confirmed",
    failed: "Failed",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium",
        styles[status]
      )}
    >
      {labels[status]}
    </span>
  );
}

function ConfidenceDot({ confidence }: { confidence: number }) {
  const color =
    confidence >= 0.8
      ? "bg-green-500"
      : confidence >= 0.5
        ? "bg-yellow-500"
        : "bg-red-500";

  const label =
    confidence >= 0.8
      ? "High confidence"
      : confidence >= 0.5
        ? "Medium confidence"
        : "Low confidence";

  return (
    <div className="flex items-center gap-1" title={`${label} (${(confidence * 100).toFixed(0)}%)`}>
      <div className={cn("w-2.5 h-2.5 rounded-full shrink-0", color)} />
    </div>
  );
}
