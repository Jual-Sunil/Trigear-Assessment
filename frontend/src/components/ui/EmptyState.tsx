import {
  Inbox,
  CheckSquare,
  Briefcase,
  Calendar,
  Search,
  FileText,
  Bell,
  Layers,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

/* ─── Base Empty State ───────────────────────── */
interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
  /** Use 'sm' inside panels, default for full-page fill */
  size?: "sm" | "default";
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
  size = "default",
}: EmptyStateProps) {
  return (
    <div
      className={cn("empty-state", className)}
      style={size === "sm" ? { padding: "var(--space-12) var(--space-6)" } : undefined}
      role="status"
      aria-label={title}
    >
      <div className="empty-state-icon-wrap">
        <Icon size={22} strokeWidth={1.5} aria-hidden="true" />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)", alignItems: "center" }}>
        <p className="empty-state-title">{title}</p>
        <p className="empty-state-description">{description}</p>
      </div>

      {action && (
        <div style={{ marginTop: "var(--space-2)" }}>
          {action}
        </div>
      )}
    </div>
  );
}

/* ─── Domain-Specific Empty States ──────────── */

export function EmptyEmails({ action }: { action?: React.ReactNode }) {
  return (
    <EmptyState
      icon={Inbox}
      title="No emails available yet"
      description="Emails synced from your connected accounts will appear here."
      action={action}
    />
  );
}

export function EmptyTasks({ action }: { action?: React.ReactNode }) {
  return (
    <EmptyState
      icon={CheckSquare}
      title="No tasks extracted yet"
      description="Tasks and action items detected in your emails will show up here."
      action={action}
    />
  );
}

export function EmptyJobs({ action }: { action?: React.ReactNode }) {
  return (
    <EmptyState
      icon={Briefcase}
      title="No job opportunities found"
      description="Job leads and opportunities parsed from your inbox will appear here."
      action={action}
    />
  );
}

export function EmptyInterviews({ action }: { action?: React.ReactNode }) {
  return (
    <EmptyState
      icon={Calendar}
      title="No interviews scheduled"
      description="Interview invitations and scheduling emails will be tracked here."
      action={action}
    />
  );
}

export function EmptySearch({ query }: { query?: string }) {
  return (
    <EmptyState
      icon={Search}
      title={query ? `No results for "${query}"` : "Search your inbox"}
      description={
        query
          ? "Try a different search term or adjust your filters."
          : "Search emails, jobs, interviews and tasks all from one place."
      }
    />
  );
}

export function EmptyDocuments({ action }: { action?: React.ReactNode }) {
  return (
    <EmptyState
      icon={FileText}
      title="No documents found"
      description="Attachments and documents from your emails will appear here."
      action={action}
    />
  );
}

export function EmptyNotifications() {
  return (
    <EmptyState
      icon={Bell}
      title="You're all caught up"
      description="No new notifications right now."
      size="sm"
    />
  );
}

export function EmptyGeneric({
  title = "Nothing here yet",
  description = "Data will appear here once it's available.",
  action,
}: {
  title?: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <EmptyState
      icon={Layers}
      title={title}
      description={description}
      action={action}
    />
  );
}
