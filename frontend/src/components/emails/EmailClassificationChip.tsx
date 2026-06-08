import { Chip } from "@mui/material";
import type { ChipProps } from "@mui/material";

export interface EmailClassificationChipProps {
  /** Classification label returned by the API, e.g. "Work", "Interview". */
  classification: string | null;
  /** MUI Chip size. Defaults to "small". */
  size?: ChipProps["size"];
}

/**
 * Classification label → MUI colour mapping.
 * Covers all nine categories emitted by the classification service.
 */
const CLASSIFICATION_COLOUR: Record<
  string,
  ChipProps["color"]
> = {
  Work: "primary",
  Interview: "info",
  "Job Opportunity": "success",
  Finance: "warning",
  Personal: "secondary",
  Promotion: "default",
  Newsletter: "default",
  Spam: "error",
  Other: "default",
};

/**
 * Renders a compact MUI Chip for an email classification label.
 *
 * Maps each known category to a distinct MUI colour token so labels
 * are immediately scannable in list views. Unknown or null categories
 * render as a neutral "—" chip.
 */
export function EmailClassificationChip({
  classification,
  size = "small",
}: EmailClassificationChipProps) {
  if (!classification) {
    return (
      <Chip
        label="—"
        size={size}
        color="default"
        variant="outlined"
        sx={{ fontSize: "0.7rem", height: 20 }}
      />
    );
  }

  const color = CLASSIFICATION_COLOUR[classification] ?? "default";

  return (
    <Chip
      label={classification}
      size={size}
      color={color}
      variant="filled"
      sx={{ fontSize: "0.7rem", height: 20, fontWeight: 500 }}
    />
  );
}

export default EmailClassificationChip;
