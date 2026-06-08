import { cn } from "@/lib/utils";

/* ─── Base Skeleton ──────────────────────────── */
interface SkeletonProps {
  className?: string;
  style?: React.CSSProperties;
}

export function Skeleton({ className, style }: SkeletonProps) {
  return (
    <div
      className={cn("skeleton", className)}
      style={style}
      aria-hidden="true"
    />
  );
}

/* ─── Text Skeletons ─────────────────────────── */
export function SkeletonText({ width = "100%", className }: { width?: string | number; className?: string }) {
  return <Skeleton className={cn("skeleton-text", className)} style={{ width }} />;
}

export function SkeletonTextSm({ width = "100%" }: { width?: string | number }) {
  return <Skeleton className="skeleton-text-sm" style={{ width }} />;
}

export function SkeletonTitle({ width = "60%" }: { width?: string | number }) {
  return <Skeleton className="skeleton-text-title" style={{ width }} />;
}

/* ─── Shape Skeletons ────────────────────────── */
export function SkeletonAvatar({ size = 32 }: { size?: number }) {
  return (
    <Skeleton
      className="skeleton-avatar"
      style={{ width: size, height: size, flexShrink: 0 }}
    />
  );
}

export function SkeletonBadge() {
  return <Skeleton className="skeleton-badge" />;
}

export function SkeletonBtn() {
  return <Skeleton className="skeleton-btn" />;
}

export function SkeletonIcon() {
  return <Skeleton className="skeleton-icon" />;
}

/* ─── Composed Skeletons ─────────────────────── */

/** Matches the email list row layout */
export function SkeletonEmailRow() {
  return (
    <div className="skeleton-row" aria-hidden="true">
      <SkeletonAvatar />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <SkeletonText width="140px" />
          <SkeletonTextSm width="48px" />
        </div>
        <SkeletonText width="220px" />
        <SkeletonTextSm width="90%" />
      </div>
    </div>
  );
}

export function SkeletonEmailList({ rows = 6 }: { rows?: number }) {
  return (
    <div
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        overflow: "hidden",
      }}
      aria-busy="true"
      aria-label="Loading emails"
    >
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonEmailRow key={i} />
      ))}
    </div>
  );
}

/** Matches the task list item layout */
export function SkeletonTaskRow() {
  return (
    <div
      className="skeleton-row"
      style={{ gap: "var(--space-3)", alignItems: "flex-start" }}
      aria-hidden="true"
    >
      <Skeleton style={{ width: 16, height: 16, borderRadius: "var(--radius-sm)", flexShrink: 0, marginTop: 2 }} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
        <SkeletonText width="75%" />
        <div style={{ display: "flex", gap: 8 }}>
          <SkeletonBadge />
          <SkeletonBadge />
        </div>
      </div>
      <SkeletonTextSm width="60px" />
    </div>
  );
}

export function SkeletonTaskList({ rows = 5 }: { rows?: number }) {
  return (
    <div
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        overflow: "hidden",
      }}
      aria-busy="true"
      aria-label="Loading tasks"
    >
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonTaskRow key={i} />
      ))}
    </div>
  );
}

/** Matches the job card layout */
export function SkeletonJobCard() {
  return (
    <div
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-5)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-3)",
      }}
      aria-hidden="true"
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
          <SkeletonTitle width="70%" />
          <SkeletonText width="50%" />
        </div>
        <SkeletonIcon />
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
        <SkeletonBadge />
        <SkeletonBadge />
        <SkeletonBadge />
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: 4,
          paddingTop: "var(--space-4)",
          borderTop: "1px solid var(--border)",
        }}
      >
        <SkeletonTextSm width="80px" />
        <SkeletonBtn />
      </div>
    </div>
  );
}

export function SkeletonJobGrid({ count = 6 }: { count?: number }) {
  return (
    <div className="card-grid" aria-busy="true" aria-label="Loading jobs">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonJobCard key={i} />
      ))}
    </div>
  );
}

/** Matches interview card layout */
export function SkeletonInterviewCard() {
  return (
    <div
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-5)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-3)",
      }}
      aria-hidden="true"
    >
      <div style={{ display: "flex", gap: "var(--space-3)", alignItems: "flex-start" }}>
        <Skeleton style={{ width: 36, height: 36, borderRadius: "var(--radius-md)", flexShrink: 0 }} />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
          <SkeletonTitle width="65%" />
          <SkeletonText width="50%" />
        </div>
        <SkeletonBadge />
      </div>
      <div
        style={{
          display: "flex",
          gap: "var(--space-4)",
          paddingTop: "var(--space-3)",
          borderTop: "1px solid var(--border)",
        }}
      >
        <SkeletonTextSm width="90px" />
        <SkeletonTextSm width="70px" />
      </div>
    </div>
  );
}

export function SkeletonInterviewGrid({ count = 4 }: { count?: number }) {
  return (
    <div className="card-grid" aria-busy="true" aria-label="Loading interviews">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonInterviewCard key={i} />
      ))}
    </div>
  );
}

/** Matches dashboard stat cards */
export function SkeletonStatCard() {
  return (
    <div
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-5) var(--space-6)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-2)",
      }}
      aria-hidden="true"
    >
      <SkeletonTextSm width="80px" />
      <Skeleton style={{ height: 36, width: "60%", borderRadius: "var(--radius-md)" }} />
      <SkeletonTextSm width="100px" />
    </div>
  );
}

export function SkeletonStatsGrid({ count = 4 }: { count?: number }) {
  return (
    <div className="stats-grid" aria-busy="true" aria-label="Loading stats">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonStatCard key={i} />
      ))}
    </div>
  );
}

/** Search results skeleton */
export function SkeletonSearchResult() {
  return (
    <div
      className="skeleton-row"
      style={{ gap: "var(--space-3)", alignItems: "flex-start" }}
      aria-hidden="true"
    >
      <SkeletonIcon />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
        <SkeletonText width="55%" />
        <SkeletonTextSm width="85%" />
        <SkeletonTextSm width="40%" />
      </div>
      <SkeletonBadge />
    </div>
  );
}

export function SkeletonSearchResults({ rows = 5 }: { rows?: number }) {
  return (
    <div
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        overflow: "hidden",
      }}
      aria-busy="true"
      aria-label="Loading search results"
    >
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonSearchResult key={i} />
      ))}
    </div>
  );
}

/** Full page skeleton — header + stats + list */
export function SkeletonPage() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)" }}>
      {/* Page header */}
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
        <Skeleton className="skeleton-text-title" style={{ width: 200 }} />
        <SkeletonText width="320px" />
      </div>
      <SkeletonStatsGrid />
      <SkeletonEmailList rows={5} />
    </div>
  );
}
