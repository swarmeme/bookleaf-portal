import { useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQueue, useStats } from "../../api/hooks";
import type { AdminTicketSummary, QueueFilters, TicketCategory, TicketPriority, TicketStatus } from "../../api/types";
import { EmptyState, ErrorNote, PageLoader, PriorityBadge, SourceTag, StatusBadge } from "../../components/ui";
import { age, hoursSince } from "../../lib/format";
import { CATEGORIES, CATEGORY_LABELS, PRIORITIES, PRIORITY_LABELS, STATUSES, STATUS_LABELS } from "../../lib/labels";

const DEFAULT_STATUSES: TicketStatus[] = ["open", "in_progress"];
// An unresolved ticket older than this gets its age highlighted.
const STALE_HOURS = 48;

/** Filters live in the URL so a filtered view survives navigation and can be shared. */
function useFilters(): [QueueFilters, (patch: Partial<QueueFilters>) => void] {
  const [params, setParams] = useSearchParams();
  const filters = useMemo<QueueFilters>(() => {
    const status = params.getAll("status") as TicketStatus[];
    return {
      status: params.has("status") ? status.filter(Boolean) : DEFAULT_STATUSES,
      category: (params.get("category") ?? "") as TicketCategory | "",
      priority: (params.get("priority") ?? "") as TicketPriority | "",
      assigned: (params.get("assigned") ?? "") as QueueFilters["assigned"],
      awaiting_reply: params.get("awaiting_reply") === "true" ? true : undefined,
      created_from: params.get("created_from") ?? "",
      created_to: params.get("created_to") ?? "",
      q: params.get("q") ?? "",
      sort: (params.get("sort") ?? "urgency") as QueueFilters["sort"],
      page: Number(params.get("page") ?? 1),
    };
  }, [params]);

  const update = (patch: Partial<QueueFilters>) => {
    const next = { ...filters, page: 1, ...patch };
    const out = new URLSearchParams();
    // An empty "status" param means "any status", distinct from the default (unresolved only).
    if (next.status && next.status.length) next.status.forEach((s) => out.append("status", s));
    else out.append("status", "");
    for (const key of ["category", "priority", "assigned", "created_from", "created_to", "q", "sort"] as const) {
      if (next[key]) out.set(key, String(next[key]));
    }
    if (next.awaiting_reply) out.set("awaiting_reply", "true");
    if (next.page && next.page > 1) out.set("page", String(next.page));
    setParams(out, { replace: true });
  };
  return [filters, update];
}

export default function QueuePage() {
  const [filters, setFilters] = useFilters();
  const queue = useQueue(filters);
  const stats = useStats();
  const navigate = useNavigate();

  const toggleStatus = (status: TicketStatus) => {
    const current = filters.status ?? [];
    setFilters({ status: current.includes(status) ? current.filter((s) => s !== status) : [...current, status] });
  };

  return (
    <div className="stack-lg">
      <div className="page-head">
        <div>
          <h1>Ticket Queue</h1>
          <p className="muted">Most urgent first, then oldest. New tickets appear automatically.</p>
        </div>
      </div>

      {stats.data && (
        <div className="queue-stats">
          <StatButton label="Need a reply" value={stats.data.awaiting_reply} onClick={() => setFilters({ status: DEFAULT_STATUSES, awaiting_reply: true, assigned: "" })} />
          <StatButton label="Critical open" value={stats.data.critical_open} tone="critical" onClick={() => setFilters({ status: DEFAULT_STATUSES, priority: "critical" })} />
          <StatButton label="Unassigned" value={stats.data.unassigned} onClick={() => setFilters({ status: DEFAULT_STATUSES, assigned: "unassigned" })} />
          <StatButton label="Open" value={stats.data.open} onClick={() => setFilters({ status: ["open"] })} />
          <StatButton label="In progress" value={stats.data.in_progress} onClick={() => setFilters({ status: ["in_progress"] })} />
          {stats.data.pending_triage > 0 && <span className="muted small">AI triaging {stats.data.pending_triage}…</span>}
        </div>
      )}

      <div className="card filters">
        <div className="chips" role="group" aria-label="Status">
          {STATUSES.map((s) => (
            <button key={s} className={`chip ${filters.status?.includes(s) ? "on" : ""}`} onClick={() => toggleStatus(s)}>
              {STATUS_LABELS[s]}
            </button>
          ))}
        </div>
        <div className="filter-row">
          <input
            key={filters.q}
            type="search"
            placeholder="Search subject or description"
            defaultValue={filters.q}
            onKeyDown={(e) => e.key === "Enter" && setFilters({ q: e.currentTarget.value })}
            onBlur={(e) => e.currentTarget.value !== filters.q && setFilters({ q: e.currentTarget.value })}
          />
          <select value={filters.category} onChange={(e) => setFilters({ category: e.target.value as TicketCategory })}>
            <option value="">All categories</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {CATEGORY_LABELS[c]}
              </option>
            ))}
          </select>
          <select value={filters.priority} onChange={(e) => setFilters({ priority: e.target.value as TicketPriority })}>
            <option value="">All priorities</option>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {PRIORITY_LABELS[p]}
              </option>
            ))}
          </select>
          <select value={filters.assigned} onChange={(e) => setFilters({ assigned: e.target.value as QueueFilters["assigned"] })}>
            <option value="">Anyone</option>
            <option value="me">Assigned to me</option>
            <option value="unassigned">Unassigned</option>
          </select>
          <label className="inline-field">
            From
            <input type="date" value={filters.created_from} onChange={(e) => setFilters({ created_from: e.target.value })} />
          </label>
          <label className="inline-field">
            To
            <input type="date" value={filters.created_to} onChange={(e) => setFilters({ created_to: e.target.value })} />
          </label>
          <select value={filters.sort} onChange={(e) => setFilters({ sort: e.target.value as QueueFilters["sort"] })}>
            <option value="urgency">Sort: urgency</option>
            <option value="oldest">Sort: oldest</option>
            <option value="newest">Sort: newest</option>
            <option value="updated">Sort: recently updated</option>
          </select>
          <label className="inline-field">
            <input type="checkbox" checked={!!filters.awaiting_reply} onChange={(e) => setFilters({ awaiting_reply: e.target.checked || undefined })} />
            Needs reply
          </label>
          <button className="btn btn-ghost btn-sm" onClick={() => setFilters({ status: DEFAULT_STATUSES, category: "", priority: "", assigned: "", created_from: "", created_to: "", q: "", sort: "urgency", awaiting_reply: undefined })}>
            Reset
          </button>
        </div>
      </div>

      {queue.isPending ? (
        <PageLoader />
      ) : queue.error ? (
        <ErrorNote error={queue.error} />
      ) : queue.data.items.length === 0 ? (
        <EmptyState title="No tickets match these filters">Try widening the status or date range.</EmptyState>
      ) : (
        <>
          <div className="card table-card">
            <table className="queue">
              <thead>
                <tr>
                  <th>Priority</th>
                  <th>Age</th>
                  <th>Ticket</th>
                  <th>Category</th>
                  <th>Status</th>
                  <th>Assignee</th>
                </tr>
              </thead>
              <tbody>
                {queue.data.items.map((t) => (
                  <QueueRow key={t.id} ticket={t} onOpen={() => navigate(`/admin/tickets/${t.id}`)} />
                ))}
              </tbody>
            </table>
          </div>
          <Pagination total={queue.data.total} page={queue.data.page} pageSize={queue.data.page_size} onPage={(page) => setFilters({ page })} />
        </>
      )}
    </div>
  );
}

function QueueRow({ ticket: t, onOpen }: { ticket: AdminTicketSummary; onOpen: () => void }) {
  const unresolved = t.status === "open" || t.status === "in_progress";
  const stale = unresolved && hoursSince(t.created_at) > STALE_HOURS;
  return (
    <tr className={`${t.priority === "critical" && unresolved ? "row-critical" : ""}`} onClick={onOpen}>
      <td>
        <PriorityBadge priority={t.priority} pending={t.ai_status === "pending"} />
        <SourceTag source={t.priority_source} />
      </td>
      <td className={stale ? "age-stale" : "age"} title={new Date(t.created_at).toLocaleString()}>
        {age(t.created_at)}
      </td>
      <td>
        <Link to={`/admin/tickets/${t.id}`} className="queue-subject" onClick={(e) => e.stopPropagation()}>
          {t.subject}
        </Link>
        <div className="muted small">
          #{t.id} · {t.author.name} · {t.book ? t.book.title : "General / Account"}
          {unresolved && t.awaiting_team_reply && <span className="needs-reply"> · needs reply</span>}
        </div>
      </td>
      <td>
        {t.category ? CATEGORY_LABELS[t.category] : <span className="muted">—</span>}
        <SourceTag source={t.category_source} />
      </td>
      <td>
        <StatusBadge status={t.status} />
      </td>
      <td>{t.assigned_admin?.name ?? <span className="muted">Unassigned</span>}</td>
    </tr>
  );
}

function StatButton({ label, value, tone, onClick }: { label: string; value: number; tone?: string; onClick: () => void }) {
  return (
    <button className={`qstat ${tone ?? ""} ${value === 0 ? "zero" : ""}`} onClick={onClick}>
      <span className="qstat-value">{value}</span>
      <span className="qstat-label">{label}</span>
    </button>
  );
}

function Pagination({ total, page, pageSize, onPage }: { total: number; page: number; pageSize: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="pagination">
      <span className="muted small">
        {total} ticket{total === 1 ? "" : "s"}
      </span>
      {pages > 1 && (
        <div className="row">
          <button className="btn btn-ghost btn-sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
            Previous
          </button>
          <span className="small">
            Page {page} of {pages}
          </span>
          <button className="btn btn-ghost btn-sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>
            Next
          </button>
        </div>
      )}
    </div>
  );
}
