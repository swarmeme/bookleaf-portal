import { useState } from "react";
import { Link } from "react-router-dom";
import { useMyTickets } from "../../api/hooks";
import type { AuthorTicketSummary } from "../../api/types";
import { EmptyState, ErrorNote, PageLoader, StatusBadge } from "../../components/ui";
import { timeAgo } from "../../lib/format";
import { CATEGORY_LABELS } from "../../lib/labels";

type Tab = "active" | "done" | "all";
const isActive = (t: AuthorTicketSummary) => t.status === "open" || t.status === "in_progress";

export default function MyTicketsPage() {
  const { data, isPending, error } = useMyTickets();
  const [tab, setTab] = useState<Tab>("active");

  if (isPending) return <PageLoader />;
  if (error) return <ErrorNote error={error} />;

  const tickets = data.items.filter((t) => (tab === "all" ? true : tab === "active" ? isActive(t) : !isActive(t)));

  return (
    <div className="stack-lg">
      <div className="page-head">
        <div>
          <h1>My Tickets</h1>
          <p className="muted">Replies from the BookLeaf team appear here instantly.</p>
        </div>
        <Link to="/tickets/new" className="btn btn-primary">
          New ticket
        </Link>
      </div>

      <div className="tabs">
        {(["active", "done", "all"] as Tab[]).map((t) => (
          <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
            {t === "active" ? "Active" : t === "done" ? "Resolved & closed" : "All"}
          </button>
        ))}
      </div>

      {tickets.length === 0 ? (
        <EmptyState title={data.items.length === 0 ? "You haven't raised any tickets yet" : "Nothing here"}>
          {data.items.length === 0 && (
            <p>
              Questions about royalties, ISBNs, printing or your book's status? <Link to="/tickets/new">Ask us</Link>.
            </p>
          )}
        </EmptyState>
      ) : (
        <ul className="ticket-list">
          {tickets.map((t) => (
            <li key={t.id}>
              <Link to={`/tickets/${t.id}`} className="card ticket-row">
                <div className="ticket-row-main">
                  <span className="ticket-subject">{t.subject}</span>
                  <span className="muted small">
                    #{t.id} · {t.book ? t.book.title : "General / Account"}
                    {t.category && ` · ${CATEGORY_LABELS[t.category]}`} · updated {timeAgo(t.updated_at)}
                  </span>
                </div>
                <div className="ticket-row-side">
                  {isActive(t) && !t.awaiting_team_reply && <span className="badge reply-badge">New reply</span>}
                  <StatusBadge status={t.status} />
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
