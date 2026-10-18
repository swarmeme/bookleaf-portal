// Mirrors the backend's Pydantic response models (see /docs for the OpenAPI schema).

export type Role = "author" | "admin";
export type TicketStatus = "open" | "in_progress" | "resolved" | "closed";
export type TicketCategory =
  | "royalty_payments"
  | "isbn_metadata"
  | "printing_quality"
  | "distribution_availability"
  | "book_status_production"
  | "general_inquiry";
export type TicketPriority = "critical" | "high" | "medium" | "low";
export type FieldSource = "ai" | "fallback" | "admin";
export type AIStatus = "pending" | "completed" | "failed" | "disabled";
export type PayoutStatus = "not_earning" | "paid_up" | "below_threshold" | "scheduled" | "possibly_overdue";

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  author_id: string | null;
}

export interface Book {
  id: string;
  author_id: string;
  title: string;
  isbn: string;
  genre: string | null;
  publication_date: string | null;
  status: string;
  is_published: boolean;
  mrp: number | null;
  author_royalty_per_copy: number | null;
  total_copies_sold: number;
  total_royalty_earned: number;
  royalty_paid: number;
  royalty_pending: number;
  last_royalty_payout_date: string | null;
  print_partner: string | null;
  available_on: string[];
}

export interface RoyaltySummary {
  total_earned: number;
  total_paid: number;
  total_pending: number;
  payout_threshold: number;
  meets_threshold: boolean;
  next_payout_date: string;
  books: { book_id: string; title: string; payout_status: PayoutStatus }[];
}

export interface Person {
  id: number;
  name: string;
}

export interface BookRef {
  id: string;
  title: string;
  status: string;
}

export interface Message {
  id: number;
  body: string;
  created_at: string;
  sender: Person & { role: Role };
  used_ai_draft?: boolean;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuthorTicketSummary {
  id: number;
  subject: string;
  book: BookRef | null;
  status: TicketStatus;
  category: TicketCategory | null;
  awaiting_team_reply: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface AuthorTicketDetail extends AuthorTicketSummary {
  description: string;
  attachment_name: string | null;
  resolved_at: string | null;
  messages: Message[];
}

export interface AdminTicketSummary {
  id: number;
  subject: string;
  author: { id: string; name: string; email: string };
  book: BookRef | null;
  status: TicketStatus;
  category: TicketCategory | null;
  category_source: FieldSource | null;
  priority: TicketPriority | null;
  priority_source: FieldSource | null;
  ai_status: AIStatus;
  assigned_admin: Person | null;
  awaiting_team_reply: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface Note {
  id: number;
  body: string;
  created_at: string;
  admin: Person;
}

export interface AdminTicketDetail extends AdminTicketSummary {
  description: string;
  attachment_name: string | null;
  ai_reasoning: string | null;
  first_responded_at: string | null;
  resolved_at: string | null;
  author: { id: string; name: string; email: string; phone: string | null; city: string | null; joined_date: string | null };
  book_details: Book | null;
  messages: Message[];
  internal_notes: Note[];
}

export interface TicketStats {
  open: number;
  in_progress: number;
  resolved: number;
  closed: number;
  unassigned: number;
  awaiting_reply: number;
  critical_open: number;
  pending_triage: number;
}

export interface Draft {
  status: "generated" | "cached" | "unavailable";
  draft: string | null;
  generated_at: string | null;
  message: string | null;
}


export interface QueueFilters {
  status?: TicketStatus[];
  category?: TicketCategory | "";
  priority?: TicketPriority | "";
  assigned?: "me" | "unassigned" | "";
  awaiting_reply?: boolean;
  created_from?: string;
  created_to?: string;
  q?: string;
  sort?: "urgency" | "newest" | "oldest" | "updated";
  page?: number;
}
