import { Label } from "@/components/ui/label";

interface FieldGroupProps {
  /** Label text for the field group */
  label: string;
  /** Optional description text below the label */
  description?: string;
  /** Whether the field group is required */
  required?: boolean;
  /** Error message to display */
  error?: string;
  /** Child form elements */
  children: React.ReactNode;
}

/**
 * Wrapper component for form field groups with label, description,
 * optional "required" indicator, and error display.
 * Provides consistent spacing across all wizard steps.
 */
export function FieldGroup({
  label,
  description,
  required = false,
  error,
  children,
}: FieldGroupProps) {
  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium">
        {label}
        {required && <span className="text-destructive ml-1">*</span>}
      </Label>
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
      {children}
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </div>
  );
}
