// Small presentational building blocks shared by both portals.

import type { ReactNode } from "react";
import { ApiError } from "../api/client";
import type { FieldSource, TicketPriority, TicketStatus } from "../api/types";
import { PRIORITY_LABELS, SOURCE_LABELS, STATUS_LABELS } from "../lib/labels";

export function StatusBadge({ status }: { status: TicketStatus }) {
  return <span className={`badge status-${status}`}>{STATUS_LABELS[status]}</span>;
}

export function PriorityBadge({ priority, pending }: { priority: TicketPriority | null; pending?: boolean }) {
  if (!priority) return <span className="badge priority-none">{pending ? "Triaging…" : "—"}</span>;
  return <span className={`badge priority-${priority}`}>{PRIORITY_LABELS[priority]}</span>;
}

const SOURCE_MARK: Record<FieldSource, string> = { ai: "AI", fallback: "Rules", admin: "Team" };

/** Small tag showing who set a triage field, so admins know what to double-check. */
export function SourceTag({ source }: { source: FieldSource | null }) {
  if (!source) return null;
  return (
    <span className={`source source-${source}`} title={SOURCE_LABELS[source]}>
      {SOURCE_MARK[source]}
    </span>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="spinner-wrap" role="status">
      <span className="spinner" aria-hidden />
      {label && <span>{label}</span>}
    </span>
  );
}

export function PageLoader() {
  return (
    <div className="page-loader">
      <Spinner label="Loading…" />
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof ApiError || error instanceof Error ? error.message : "Something went wrong.";
  return (
    <div className="alert alert-error" role="alert">
      {message}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <p className="empty-title">{title}</p>
      {children && <div className="empty-body">{children}</div>}
    </div>
  );
}

export function fieldError(error: unknown, field: string): string | undefined {
  return error instanceof ApiError ? error.details?.find((d) => d.field === field)?.message : undefined;
}
