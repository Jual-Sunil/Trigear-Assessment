import { Chip } from "@mui/material";
import type { ChipProps } from "@mui/material";

export interface EmailPriorityChipProps {
  /** Numeric priority score in the range 0–100, or null when unavailable. */
  priorityScore: number | null;
  /** MUI Chip size. Defaults to "small". */
  size?: ChipProps["size"];
}

interface PriorityTier {
  label: string;
  color: ChipProps["color"];
}

/**
 * Resolves a numeric 0–100 priority score to a display tier.
 *
 * @param score - Raw priority score.
 * @returns Tier label and MUI colour token.
 */
function resolveTier(score: number): PriorityTier {
  if (score >= 80) return { label: `${score} · Critical`, color: "error" };
  if (score >= 60) return { label: `${score} · High`, color: "warning" };
  if (score >= 40) return { label: `${score} · Medium`, color: "info" };
  return { label: `${score} · Low`, color: "default" };
}

/**
 * Renders a compact MUI Chip that communicates both the raw priority
 * score and its human-readable tier (Critical / High / Medium / Low).
 *
 * Null scores render as a neutral "—" chip. Scores ≥ 70 (the threshold
 * used by the Important Emails widget) are guaranteed to display in the
 * High or Critical tier, providing immediate visual signal.
 */
export function EmailPriorityChip({
  priorityScore,
  size = "small",
}: EmailPriorityChipProps) {
  if (priorityScore === null || priorityScore === undefined) {
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

  const { label, color } = resolveTier(priorityScore);

  return (
    <Chip
      label={label}
      size={size}
      color={color}
      variant="filled"
      sx={{ fontSize: "0.7rem", height: 20, fontWeight: 500 }}
    />
  );
}

export default EmailPriorityChip;
