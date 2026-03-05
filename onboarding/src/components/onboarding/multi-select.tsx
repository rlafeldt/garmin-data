"use client";

import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

interface MultiSelectOption {
  value: string;
  label: string;
}

interface MultiSelectProps {
  /** Available options */
  options: MultiSelectOption[];
  /** Currently selected values */
  value: string[];
  /** Callback when selection changes */
  onChange: (values: string[]) => void;
  /** Number of columns on desktop (default: 3) */
  columns?: 2 | 3;
}

/**
 * Reusable multi-select component using shadcn/ui Checkbox components.
 * Renders as a grid of checkboxes (2 columns on mobile, 3 on desktop).
 * Integrates with RHF via Controller.
 */
export function MultiSelect({
  options,
  value = [],
  onChange,
  columns = 3,
}: MultiSelectProps) {
  const handleToggle = (optionValue: string, checked: boolean) => {
    if (checked) {
      onChange([...value, optionValue]);
    } else {
      onChange(value.filter((v) => v !== optionValue));
    }
  };

  return (
    <div
      className={`grid grid-cols-2 gap-3 ${
        columns === 3 ? "md:grid-cols-3" : "md:grid-cols-2"
      }`}
    >
      {options.map((option) => (
        <div key={option.value} className="flex items-center gap-2">
          <Checkbox
            id={`ms-${option.value}`}
            checked={value.includes(option.value)}
            onCheckedChange={(checked) =>
              handleToggle(option.value, checked === true)
            }
          />
          <Label
            htmlFor={`ms-${option.value}`}
            className="text-sm font-normal cursor-pointer"
          >
            {option.label}
          </Label>
        </div>
      ))}
    </div>
  );
}
