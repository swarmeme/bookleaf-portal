// React Query hooks: one per endpoint. Mutations update or invalidate the cache so
// every view of a ticket stays consistent; live SSE events invalidate the same keys.

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type {
  AdminTicketDetail,
  AdminTicketSummary,
  AuthorTicketDetail,
  AuthorTicketSummary,
  Book,
  Draft,
  Page,
  Person,
  QueueFilters,
  RoyaltySummary,
  TicketCategory,
  TicketPriority,
  TicketStats,
  TicketStatus,
} from "./types";

export const keys = {
  books: ["books"] as const,
  royalty: ["royalty"] as const,
  myTickets: ["tickets", "mine"] as const,
  myTicket: (id: number) => ["tickets", "mine", id] as const,
  queue: (filters: QueueFilters) => ["tickets", "queue", filters] as const,
  adminTicket: (id: number) => ["tickets", "admin", id] as const,
  stats: ["tickets", "stats"] as const,
  draft: (id: number) => ["draft", id] as const,
  team: ["team"] as const,
};

// --- Author ---------------------------------------------------------------------------

export const useBooks = () => useQuery({ queryKey: keys.books, queryFn: () => api.get<Book[]>("/books") });

export const useRoyaltySummary = () =>
  useQuery({ queryKey: keys.royalty, queryFn: () => api.get<RoyaltySummary>("/royalties/summary") });

export const useMyTickets = () =>
  useQuery({ queryKey: keys.myTickets, queryFn: () => api.get<Page<AuthorTicketSummary>>("/tickets", { page_size: 100 }) });

export const useMyTicket = (id: number) =>
  useQuery({ queryKey: keys.myTicket(id), queryFn: () => api.get<AuthorTicketDetail>(`/tickets/${id}`) });

export interface NewTicket {
  book_id: string | null;
  subject: string;
  description: string;
  attachment_name: string | null;
}

export function useCreateTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: NewTicket) => api.post<AuthorTicketDetail>("/tickets", body),
    onSuccess: (ticket) => {
      qc.setQueryData(keys.myTicket(ticket.id), ticket);
      qc.invalidateQueries({ queryKey: keys.myTickets });
    },
  });
}

export function useAuthorReply(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => api.post<AuthorTicketDetail>(`/tickets/${id}/messages`, { body }),
    onSuccess: (ticket) => {
      qc.setQueryData(keys.myTicket(id), ticket);
      qc.invalidateQueries({ queryKey: keys.myTickets });
    },
  });
}

// --- Admin ----------------------------------------------------------------------------

export const useQueue = (filters: QueueFilters) =>
  useQuery({
    queryKey: keys.queue(filters),
    queryFn: () => api.get<Page<AdminTicketSummary>>("/admin/tickets", { ...filters, page_size: 25 }),
    placeholderData: keepPreviousData, // keep the table on screen while filters change
  });

export const useStats = () =>
  useQuery({ queryKey: keys.stats, queryFn: () => api.get<TicketStats>("/admin/tickets/stats") });

export const useAdminTicket = (id: number) =>
  useQuery({ queryKey: keys.adminTicket(id), queryFn: () => api.get<AdminTicketDetail>(`/admin/tickets/${id}`) });

export const useTeam = () =>
  useQuery({ queryKey: keys.team, queryFn: () => api.get<Person[]>("/admin/team"), staleTime: Infinity });

export function useDraft(id: number, enabled: boolean) {
  return useQuery({
    queryKey: keys.draft(id),
    queryFn: () => api.post<Draft>(`/admin/tickets/${id}/draft`),
    enabled,
    staleTime: Infinity, // the server caches the draft; only refetch when asked
    retry: false,
  });
}

export function useRegenerateDraft(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<Draft>(`/admin/tickets/${id}/draft`, {}, { regenerate: true }),
    onSuccess: (draft) => qc.setQueryData(keys.draft(id), draft),
  });
}

/** Shared by every admin mutation that returns the updated ticket. */
function useAdminTicketMutation<TArgs>(id: number, fn: (args: TArgs) => Promise<AdminTicketDetail>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (ticket) => {
      qc.setQueryData(keys.adminTicket(id), ticket);
      qc.invalidateQueries({ queryKey: ["tickets", "queue"] });
      qc.invalidateQueries({ queryKey: keys.stats });
    },
  });
}

export interface TicketPatch {
  status?: TicketStatus;
  category?: TicketCategory;
  priority?: TicketPriority;
  assigned_admin_id?: number | null;
}

export const useUpdateTicket = (id: number) =>
  useAdminTicketMutation(id, (patch: TicketPatch) => api.patch<AdminTicketDetail>(`/admin/tickets/${id}`, patch));

export function useAdminReply(id: number) {
  const qc = useQueryClient();
  return useAdminTicketMutation(
    id,
    async (body: { body: string; used_ai_draft: boolean; status?: TicketStatus }) => {
      const ticket = await api.post<AdminTicketDetail>(`/admin/tickets/${id}/messages`, body);
      qc.removeQueries({ queryKey: keys.draft(id) }); // the server dropped its cached draft too
      return ticket;
    },
  );
}

export const useAddNote = (id: number) =>
  useAdminTicketMutation(id, (body: string) => api.post<AdminTicketDetail>(`/admin/tickets/${id}/notes`, { body }));

export const useRetriage = (id: number) =>
  useAdminTicketMutation<void>(id, () => api.post<AdminTicketDetail>(`/admin/tickets/${id}/triage`));
