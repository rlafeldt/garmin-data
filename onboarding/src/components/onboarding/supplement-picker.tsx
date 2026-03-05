"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

/**
 * Supplement categories with their items, matching CONTEXT.md field reference.
 * All identifiers use snake_case to match the Python-side data contract.
 */
const SUPPLEMENT_CATEGORIES = [
  {
    key: "foundational" as const,
    label: "Foundational",
    items: [
      { value: "vitamin_d3_k2", label: "Vitamin D3+K2" },
      { value: "magnesium_glycinate_malate", label: "Magnesium glycinate/malate" },
      { value: "omega_3_fish_oil", label: "Omega-3/Fish Oil" },
      { value: "zinc", label: "Zinc" },
      { value: "b_complex_b12", label: "B-Complex/B12" },
      { value: "vitamin_c", label: "Vitamin C" },
      { value: "iron", label: "Iron" },
      { value: "iodine", label: "Iodine" },
      { value: "selenium", label: "Selenium" },
      { value: "multivitamin", label: "Multivitamin" },
    ],
  },
  {
    key: "performance_recovery" as const,
    label: "Performance & Recovery",
    items: [
      { value: "creatine", label: "Creatine" },
      { value: "protein_powder", label: "Protein powder (whey/plant)" },
      { value: "bcaas_eaas", label: "BCAAs/EAAs" },
      { value: "beta_alanine", label: "Beta-Alanine" },
      { value: "citrulline_arginine", label: "Citrulline/Arginine" },
      { value: "taurine", label: "Taurine" },
      { value: "electrolytes_sodium", label: "Electrolytes/Sodium" },
      { value: "collagen_glycine", label: "Collagen/Glycine" },
      { value: "l_glutamine", label: "L-Glutamine" },
      { value: "carnitine", label: "Carnitine" },
      { value: "hmb", label: "HMB" },
    ],
  },
  {
    key: "hormonal_metabolic" as const,
    label: "Hormonal & Metabolic",
    items: [
      { value: "ashwagandha_ksm66", label: "Ashwagandha/KSM-66" },
      { value: "tongkat_ali", label: "Tongkat Ali" },
      { value: "maca_root", label: "Maca root" },
      { value: "berberine", label: "Berberine" },
      { value: "inositol", label: "Inositol" },
      { value: "dhea", label: "DHEA" },
      { value: "pregnenolone", label: "Pregnenolone" },
      { value: "alpha_lipoic_acid", label: "Alpha-lipoic acid" },
      { value: "chromium", label: "Chromium" },
    ],
  },
  {
    key: "longevity_cellular" as const,
    label: "Longevity & Cellular",
    items: [
      { value: "nad_nmn_nr", label: "NAD+/NMN/NR" },
      { value: "resveratrol_pterostilbene", label: "Resveratrol/Pterostilbene" },
      { value: "quercetin", label: "Quercetin" },
      { value: "spermidine", label: "Spermidine" },
      { value: "coq10_ubiquinol", label: "CoQ10/Ubiquinol" },
      { value: "pqq", label: "PQQ" },
      { value: "fisetin", label: "Fisetin" },
      { value: "rapamycin_prescribed", label: "Rapamycin (prescribed)" },
      { value: "metformin_prescribed", label: "Metformin (prescribed)" },
    ],
  },
  {
    key: "cognitive_neurological" as const,
    label: "Cognitive & Neurological",
    items: [
      { value: "lions_mane", label: "Lion's Mane" },
      { value: "bacopa_monnieri", label: "Bacopa monnieri" },
      { value: "rhodiola_rosea", label: "Rhodiola rosea" },
      { value: "phosphatidylserine", label: "Phosphatidylserine" },
      { value: "alpha_gpc_cdp_choline", label: "Alpha-GPC/CDP-Choline" },
      { value: "l_theanine", label: "L-Theanine" },
      { value: "magnesium_threonate", label: "Magnesium threonate" },
      { value: "nootropic_stack", label: "Nootropic stack" },
    ],
  },
  {
    key: "gut_immune" as const,
    label: "Gut & Immune",
    items: [
      { value: "probiotics", label: "Probiotics" },
      { value: "prebiotics_fibre", label: "Prebiotics/Fibre" },
      { value: "digestive_enzymes", label: "Digestive enzymes" },
      { value: "zinc_carnosine", label: "Zinc carnosine" },
      { value: "glutamine_gut_lining", label: "Glutamine (gut lining)" },
      { value: "oregano_oil_antimicrobials", label: "Oregano oil/antimicrobials" },
    ],
  },
  {
    key: "sleep_stress" as const,
    label: "Sleep & Stress",
    items: [
      { value: "melatonin", label: "Melatonin" },
      { value: "magnesium_glycinate_sleep", label: "Magnesium glycinate (sleep)" },
      { value: "apigenin", label: "Apigenin" },
      { value: "glycine_sleep", label: "Glycine (sleep)" },
      { value: "valerian_passionflower", label: "Valerian/Passionflower" },
      { value: "phosphatidylserine_cortisol", label: "Phosphatidylserine (cortisol)" },
    ],
  },
  {
    key: "ketogenic_metabolic" as const,
    label: "Ketogenic / Metabolic Support",
    items: [
      { value: "exogenous_ketones_bhb", label: "Exogenous ketones (BHB)" },
      { value: "mct_oil_c8", label: "MCT oil/C8" },
      { value: "acetyl_l_carnitine_alcar", label: "Acetyl-L-Carnitine (ALCAR)" },
    ],
  },
] as const;

type CategoryKey = (typeof SUPPLEMENT_CATEGORIES)[number]["key"];

interface SupplementData {
  foundational: string[];
  performance_recovery: string[];
  hormonal_metabolic: string[];
  longevity_cellular: string[];
  cognitive_neurological: string[];
  gut_immune: string[];
  sleep_stress: string[];
  ketogenic_metabolic: string[];
}

interface SupplementPickerProps {
  /** Current supplement selections by category */
  value: SupplementData | undefined;
  /** Callback when selections change */
  onChange: (data: SupplementData) => void;
  /** Whether "No supplements" is checked */
  noSupplements: boolean;
  /** Callback when "No supplements" changes */
  onNoSupplementsChange: (checked: boolean) => void;
}

const EMPTY_SUPPLEMENTS: SupplementData = {
  foundational: [],
  performance_recovery: [],
  hormonal_metabolic: [],
  longevity_cellular: [],
  cognitive_neurological: [],
  gut_immune: [],
  sleep_stress: [],
  ketogenic_metabolic: [],
};

/**
 * Categorised supplement selector with 8 expandable groups.
 * Categories are collapsed by default and expand on tap.
 * Includes a "No supplements" checkbox that clears all selections.
 */
export function SupplementPicker({
  value,
  onChange,
  noSupplements,
  onNoSupplementsChange,
}: SupplementPickerProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<CategoryKey>>(
    new Set()
  );

  const supplements = value ?? EMPTY_SUPPLEMENTS;

  const toggleCategory = (key: CategoryKey) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const handleItemToggle = (
    categoryKey: CategoryKey,
    itemValue: string,
    checked: boolean
  ) => {
    const current = supplements[categoryKey] ?? [];
    const updated = checked
      ? [...current, itemValue]
      : current.filter((v) => v !== itemValue);

    onChange({
      ...supplements,
      [categoryKey]: updated,
    });

    // If user selects something, uncheck "No supplements"
    if (checked && noSupplements) {
      onNoSupplementsChange(false);
    }
  };

  const handleNoSupplements = (checked: boolean) => {
    onNoSupplementsChange(checked);
    if (checked) {
      // Clear all selections
      onChange(EMPTY_SUPPLEMENTS);
    }
  };

  const totalSelected = Object.values(supplements).reduce(
    (sum, arr) => sum + (arr?.length ?? 0),
    0
  );

  return (
    <div className="space-y-3">
      {/* No supplements option */}
      <div className="flex items-center gap-2 pb-2 border-b border-border/40">
        <Checkbox
          id="no-supplements"
          checked={noSupplements}
          onCheckedChange={(checked) => handleNoSupplements(checked === true)}
        />
        <Label
          htmlFor="no-supplements"
          className="text-sm font-normal cursor-pointer"
        >
          No supplements
        </Label>
        {totalSelected > 0 && (
          <span className="text-xs text-muted-foreground ml-auto">
            {totalSelected} selected
          </span>
        )}
      </div>

      {/* Category groups */}
      {!noSupplements && (
        <div className="space-y-1">
          {SUPPLEMENT_CATEGORIES.map((category) => {
            const isExpanded = expandedCategories.has(category.key);
            const categoryItems = supplements[category.key] ?? [];
            const selectedCount = categoryItems.length;

            return (
              <div key={category.key} className="border border-border/40 rounded-md">
                {/* Category header */}
                <button
                  type="button"
                  onClick={() => toggleCategory(category.key)}
                  className="flex items-center justify-between w-full px-3 py-2.5 text-sm font-medium hover:bg-accent/50 rounded-md transition-colors"
                >
                  <div className="flex items-center gap-2">
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-muted-foreground" />
                    )}
                    {category.label}
                  </div>
                  {selectedCount > 0 && (
                    <span className="text-xs text-primary bg-primary/10 px-2 py-0.5 rounded-full">
                      {selectedCount}
                    </span>
                  )}
                </button>

                {/* Category items */}
                {isExpanded && (
                  <div className="px-3 pb-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {category.items.map((item) => (
                      <div key={item.value} className="flex items-center gap-2">
                        <Checkbox
                          id={`supp-${item.value}`}
                          checked={categoryItems.includes(item.value)}
                          onCheckedChange={(checked) =>
                            handleItemToggle(
                              category.key,
                              item.value,
                              checked === true
                            )
                          }
                        />
                        <Label
                          htmlFor={`supp-${item.value}`}
                          className="text-sm font-normal cursor-pointer"
                        >
                          {item.label}
                        </Label>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
