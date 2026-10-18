import { useState, type FormEvent } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useAuthorReply, useMyTicket } from "../../api/hooks";
import Thread from "../../components/Thread";
import { ErrorNote, PageLoader, StatusBadge } from "../../components/ui";
import { formatDate } from "../../lib/format";
import { CATEGORY_LABELS } from "../../lib/labels";

export default function TicketPage() {
  const id = Number(useParams().id);
  const justCreated = (useLocation().state as { created?: boolean } | null)?.created;
  const { data: ticket, isPending, error } = useMyTicket(id);
  const reply = useAuthorReply(id);
  const [body, setBody] = useState("");

  if (isPending) return <PageLoader />;
  if (error) return <ErrorNote error={error} />;

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    reply.mutate(body, { onSuccess: () => setBody("") });
  }

  const waiting = ticket.awaiting_team_reply && (ticket.status === "open" || ticket.status === "in_progress");

  return (
    <div className="narrow stack-lg">
      <div>
        <Link to="/tickets" className="back">
          ← My Tickets
        </Link>
        <div className="ticket-title">
          <h1>{ticket.subject}</h1>
          <StatusBadge status={ticket.status} />
        </div>
        <p className="muted small">
          Ticket #{ticket.id} · {ticket.book ? ticket.book.title : "General / Account"}
          {ticket.category && ` · ${CATEGORY_LABELS[ticket.category]}`} · opened {formatDate(ticket.created_at)}
        </p>
      </div>

      {justCreated && ticket.messages.length === 0 && (
        <div className="alert alert-success">
          Thanks, your ticket has been received. The BookLeaf team will reply here, and this page updates
          automatically.
        </div>
      )}

      <Thread
        viewer="author"
        authorName="You"
        description={ticket.description}
        createdAt={ticket.created_at}
        attachmentName={ticket.attachment_name}
        messages={ticket.messages}
      />

      {waiting && <p className="muted small center">Waiting for a reply from the BookLeaf team…</p>}

      {ticket.status === "closed" ? (
        <div className="alert">
          This ticket is closed. Need more help? <Link to="/tickets/new">Raise a new ticket</Link>.
        </div>
      ) : (
        <form className="card stack" onSubmit={onSubmit}>
          <label className="field">
            <span>{ticket.status === "resolved" ? "Still need help? Reply to reopen this ticket" : "Add a reply"}</span>
            <textarea rows={3} value={body} onChange={(e) => setBody(e.target.value)} maxLength={5000} />
          </label>
          <ErrorNote error={reply.error} />
          <div className="row-end">
            <button className="btn btn-primary" disabled={!body.trim() || reply.isPending}>
              {reply.isPending ? "Sending…" : "Send"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
