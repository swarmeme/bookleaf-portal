import type { FieldSource, PayoutStatus, TicketCategory, TicketPriority, TicketStatus } from "../api/types";

export const STATUS_LABELS: Record<TicketStatus, string> = {
  open: "Open",
  in_progress: "In Progress",
  resolved: "Resolved",
  closed: "Closed",
};

export const CATEGORY_LABELS: Record<TicketCategory, string> = {
  royalty_payments: "Royalty & Payments",
  isbn_metadata: "ISBN & Metadata",
  printing_quality: "Printing & Quality",
  distribution_availability: "Distribution & Availability",
  book_status_production: "Book Status & Production",
  general_inquiry: "General Inquiry",
};

export const PRIORITY_LABELS: Record<TicketPriority, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

export const SOURCE_LABELS: Record<FieldSource, string> = {
  ai: "Set by AI",
  fallback: "Set by keyword rules (AI unavailable)",
  admin: "Set by the team",
};

export const PAYOUT_LABELS: Record<PayoutStatus, string> = {
  not_earning: "No royalties yet",
  paid_up: "Fully paid",
  below_threshold: "Rolls over (below minimum)",
  scheduled: "Due next payout",
  possibly_overdue: "Due next payout",
};

export const STATUSES = Object.keys(STATUS_LABELS) as TicketStatus[];
export const CATEGORIES = Object.keys(CATEGORY_LABELS) as TicketCategory[];
export const PRIORITIES = Object.keys(PRIORITY_LABELS) as TicketPriority[];

// The canonical production pipeline from the knowledge base, used to show progress.
export const PRODUCTION_STAGES = [
  "Manuscript Received",
  "Editing",
  "Cover Design",
  "Typesetting",
  "Proofreading",
  "ISBN Assignment",
  "Printing",
  "Distribution Setup",
  "Published & Live",
];
