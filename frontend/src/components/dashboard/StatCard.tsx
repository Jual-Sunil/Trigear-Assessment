import { Box, Card, CardContent, Skeleton, Typography } from "@mui/material";
import { type SxProps, type Theme } from "@mui/material/styles";

export interface StatCardProps {
  /** Display label rendered above the count value. */
  label: string;
  /** Numeric count to display; renders 0 when undefined. */
  value: number | undefined;
  /** MUI icon element rendered alongside the label. */
  icon: React.ReactNode;
  /** When true, renders a skeleton placeholder instead of the value. */
  isLoading: boolean;
  /** Optional accent color token applied to the left border stripe. */
  accentColor?: string;
  /** Optional additional MUI sx overrides for the root Card. */
  sx?: SxProps<Theme>;
}

/**
 * Renders a single labelled stat card for the dashboard overview grid.
 *
 * Displays an icon, a human-readable label, and a numeric count.
 * Handles loading state with a Skeleton placeholder and applies an
 * optional left-border accent stripe for visual differentiation.
 */
export function StatCard({
  label,
  value,
  icon,
  isLoading,
  accentColor,
  sx,
}: StatCardProps) {
  return (
    <Card
      variant="outlined"
      sx={{
        height: "100%",
        borderLeft: accentColor ? `3px solid ${accentColor}` : undefined,
        borderRadius: accentColor ? "0 8px 8px 0" : undefined,
        transition: "box-shadow 0.2s ease, transform 0.2s ease",
        "&:hover": {
          boxShadow: "0 4px 20px rgba(0,0,0,0.08)",
          transform: "translateY(-2px)",
        },
        ...sx,
      }}
    >
      <CardContent sx={{ p: 2.5, "&:last-child": { pb: 2.5 } }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            mb: 1.5,
          }}
        >
          {icon}
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              fontSize: "0.75rem",
              fontWeight: 500,
              letterSpacing: "0.05em",
              textTransform: "uppercase",
            }}
          >
            {label}
          </Typography>
        </Box>

        {isLoading ? (
          <Skeleton
            variant="text"
            width={64}
            height={44}
            sx={{ borderRadius: 1 }}
          />
        ) : (
          <Typography
            variant="h4"
            sx={{
              fontWeight: 700,
              fontSize: "2rem",
              lineHeight: 1,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {value ?? 0}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

export default StatCard;
