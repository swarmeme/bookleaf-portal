import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import {
  useAddNote,
  useAdminReply,
  useAdminTicket,
  useDraft,
  useRegenerateDraft,
  useRetriage,
  useTeam,
  useUpdateTicket,
} from "../../api/hooks";
import type { AdminTicketDetail, Book, TicketCategory, TicketPriority, TicketStatus } from "../../api/types";
import { useAuth } from "../../auth/AuthContext";
import Thread from "../../components/Thread";
import { ErrorNote, PageLoader, PriorityBadge, SourceTag, Spinner, StatusBadge } from "../../components/ui";
import { formatDate, formatDateTime, rupees, timeAgo } from "../../lib/format";
import { CATEGORIES, CATEGORY_LABELS, PRIORITIES, PRIORITY_LABELS, STATUSES, STATUS_LABELS } from "../../lib/labels";

export default function AdminTicketPage() {
  const id = Number(useParams().id);
  const { data: ticket, isPending, error } = useAdminTicket(id);

  if (isPending) return <PageLoader />;
  if (error) return <ErrorNote error={error} />;

  return (
    <div className="stack-lg">
      <div>
        <Link to="/admin/tickets" className="back">
          ← Ticket Queue
        </Link>
        <div className="ticket-title">
          <h1>{ticket.subject}</h1>
          <PriorityBadge priority={ticket.priority} pending={ticket.ai_status === "pending"} />
          <StatusBadge status={ticket.status} />
        </div>
        <p className="muted small">
          #{ticket.id} · from {ticket.author.name} · {ticket.book ? ticket.book.title : "General / Account"} · opened{" "}
          {formatDateTime(ticket.created_at)} ({timeAgo(ticket.created_at)})
        </p>
      </div>

      <div className="ticket-layout">
        <div className="stack-lg">
          <Thread
            viewer="admin"
            authorName={ticket.author.name}
            description={ticket.description}
            createdAt={ticket.created_at}
            attachmentName={ticket.attachment_name}
            messages={ticket.messages}
          />
          <Composer ticket={ticket} />
        </div>

        <aside className="stack">
          <TriagePanel ticket={ticket} />
          <WorkflowPanel ticket={ticket} />
          <NotesPanel ticket={ticket} />
          <AuthorPanel ticket={ticket} />
          {ticket.book_details && <BookPanel book={ticket.book_details} />}
        </aside>
      </div>
    </div>
  );
}

// --- Reply composer with AI draft --------------------------------------------------------

function Composer({ ticket }: { ticket: AdminTicketDetail }) {
  const unresolved = ticket.status === "open" || ticket.status === "in_progress";
  // Only draft automatically when the author is waiting on us; otherwise on request. Saves AI calls.
  const [requested, setRequested] = useState(false);
  const draftEnabled = (unresolved && ticket.awaiting_team_reply) || requested;
  const draft = useDraft(ticket.id, draftEnabled);
  const regenerate = useRegenerateDraft(ticket.id);
  const reply = useAdminReply(ticket.id);

  const [body, setBody] = useState("");
  const [fromDraft, setFromDraft] = useState(false); // composer text started from the AI draft
  const [edited, setEdited] = useState(false); // admin has typed: never overwrite their text

  const draftText = draft.data?.draft ?? null;
  const drafting = draft.isFetching || regenerate.isPending;
  const unavailable = draft.data?.status === "unavailable" ? draft.data.message : null;
  useEffect(() => {
    if (draftText && !edited) {
      setBody(draftText);
      setFromDraft(true);
    }
  }, [draftText, edited]);

  function applyDraft() {
    if (!draftText) return;
    setBody(draftText);
    setFromDraft(true);
    setEdited(false);
  }

  function send(status?: TicketStatus) {
    reply.mutate(
      { body, used_ai_draft: fromDraft, status },
      {
        onSuccess: () => {
          setBody("");
          setFromDraft(false);
          setEdited(false);
          setRequested(false);
        },
      },
    );
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    send();
  }


  return (
    <form className="card stack composer" onSubmit={onSubmit}>
      <div className="composer-head">
        <h2>Reply to {ticket.author.name.split(" ")[0]}</h2>
        <div className="row">
          {!draftEnabled && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setRequested(true)}>
              ✦ Draft with AI
            </button>
          )}
          {draftEnabled && !drafting && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => regenerate.mutate()}>
              {unavailable ? "↻ Try AI again" : "↻ Regenerate draft"}
            </button>
          )}
          {draftText && edited && body !== draftText && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={applyDraft}>
              Use AI draft
            </button>
          )}
        </div>
      </div>

      {drafting && (
        <div className="ai-bar">
          <Spinner label="Drafting a reply from the knowledge base and this author's account…" />
        </div>
      )}
      {!drafting && unavailable && <div className="alert alert-warn">{unavailable}</div>}
      {!drafting && fromDraft && draftText && (
        <div className="ai-bar">
          ✦ AI draft based on BookLeaf policy and this author's account data. Check the facts and edit before
          sending.
        </div>
      )}
      <ErrorNote error={regenerate.error} />

      <textarea
        rows={18}
        value={body}
        maxLength={5000}
        placeholder={drafting ? "" : "Write your reply to the author…"}
        onChange={(e) => {
          setBody(e.target.value);
          setEdited(true);
        }}
      />
      <ErrorNote error={reply.error} />
      <div className="row-end">
        <span className="muted small grow">The author sees this reply immediately.</span>
        <button type="submit" className="btn btn-ghost" disabled={!body.trim() || reply.isPending}>
          Send
        </button>
        <button type="button" className="btn btn-primary" disabled={!body.trim() || reply.isPending} onClick={() => send("resolved")}>
          {reply.isPending ? "Sending…" : "Send & resolve"}
        </button>
      </div>
    </form>
  );
}

// --- Sidebar panels ---------------------------------------------------------------------------

function TriagePanel({ ticket }: { ticket: AdminTicketDetail }) {
  const update = useUpdateTicket(ticket.id);
  const retriage = useRetriage(ticket.id);
  const pending = ticket.ai_status === "pending";
  const canRetriage = !pending && (ticket.ai_status !== "completed" || ticket.category_source === "admin" || ticket.priority_source === "admin");

  return (
    <section className="card panel">
      <h3>Triage</h3>
      {pending && <Spinner label="AI is triaging this ticket…" />}
      <label className="field">
        <span>
          Priority <SourceTag source={ticket.priority_source} />
        </span>
        <select
          value={ticket.priority ?? ""}
          onChange={(e) => update.mutate({ priority: e.target.value as TicketPriority })}
          disabled={update.isPending}
        >
          {!ticket.priority && <option value="">Not set</option>}
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {PRIORITY_LABELS[p]}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>
          Category <SourceTag source={ticket.category_source} />
        </span>
        <select
          value={ticket.category ?? ""}
          onChange={(e) => update.mutate({ category: e.target.value as TicketCategory })}
          disabled={update.isPending}
        >
          {!ticket.category && <option value="">Not set</option>}
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {CATEGORY_LABELS[c]}
            </option>
          ))}
        </select>
      </label>
      {ticket.ai_reasoning && <p className="reasoning small">“{ticket.ai_reasoning}”</p>}
      {canRetriage && (
        <button className="btn btn-ghost btn-sm" onClick={() => retriage.mutate()} disabled={retriage.isPending}>
          ✦ Re-run AI triage
        </button>
      )}
      <ErrorNote error={update.error ?? retriage.error} />
    </section>
  );
}

function WorkflowPanel({ ticket }: { ticket: AdminTicketDetail }) {
  const { user } = useAuth();
  const team = useTeam();
  const update = useUpdateTicket(ticket.id);
  const mine = ticket.assigned_admin?.id === user?.id;

  return (
    <section className="card panel">
      <h3>Workflow</h3>
      <label className="field">
        <span>Status</span>
        <select value={ticket.status} onChange={(e) => update.mutate({ status: e.target.value as TicketStatus })} disabled={update.isPending}>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>Assignee</span>
        <select
          value={ticket.assigned_admin?.id ?? ""}
          onChange={(e) => update.mutate({ assigned_admin_id: e.target.value ? Number(e.target.value) : null })}
          disabled={update.isPending}
        >
          <option value="">Unassigned</option>
          {team.data?.map((member) => (
            <option key={member.id} value={member.id}>
              {member.name}
              {member.id === user?.id ? " (me)" : ""}
            </option>
          ))}
        </select>
      </label>
      {!mine && (
        <button className="btn btn-ghost btn-sm" onClick={() => update.mutate({ assigned_admin_id: user!.id })} disabled={update.isPending}>
          Assign to me
        </button>
      )}
      <dl className="mini-facts small">
        <dt>First response</dt>
        <dd>{ticket.first_responded_at ? formatDateTime(ticket.first_responded_at) : "Not yet"}</dd>
        {ticket.resolved_at && (
          <>
            <dt>Resolved</dt>
            <dd>{formatDateTime(ticket.resolved_at)}</dd>
          </>
        )}
      </dl>
      <ErrorNote error={update.error} />
    </section>
  );
}

function NotesPanel({ ticket }: { ticket: AdminTicketDetail }) {
  const addNote = useAddNote(ticket.id);
  const [body, setBody] = useState("");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    addNote.mutate(body, { onSuccess: () => setBody("") });
  }

  return (
    <section className="card panel notes">
      <h3>
        Internal notes <span className="muted small">· not visible to the author</span>
      </h3>
      {ticket.internal_notes.length === 0 && <p className="muted small">No notes yet.</p>}
      <ul>
        {ticket.internal_notes.map((note) => (
          <li key={note.id}>
            <p className="pre small">{note.body}</p>
            <span className="muted small">
              {note.admin.name} · {formatDateTime(note.created_at)}
            </span>
          </li>
        ))}
      </ul>
      <form onSubmit={onSubmit} className="stack-sm">
        <textarea rows={2} value={body} onChange={(e) => setBody(e.target.value)} placeholder="Add a note for the team" maxLength={5000} />
        <ErrorNote error={addNote.error} />
        <button className="btn btn-ghost btn-sm" disabled={!body.trim() || addNote.isPending}>
          Add note
        </button>
      </form>
    </section>
  );
}

function AuthorPanel({ ticket }: { ticket: AdminTicketDetail }) {
  const a = ticket.author;
  return (
    <section className="card panel">
      <h3>Author</h3>
      <dl className="mini-facts small">
        <dt>Name</dt>
        <dd>
          {a.name} ({a.id})
        </dd>
        <dt>Email</dt>
        <dd>{a.email}</dd>
        {a.phone && (
          <>
            <dt>Phone</dt>
            <dd>{a.phone}</dd>
          </>
        )}
        {a.city && (
          <>
            <dt>City</dt>
            <dd>{a.city}</dd>
          </>
        )}
        <dt>Joined</dt>
        <dd>{formatDate(a.joined_date)}</dd>
      </dl>
    </section>
  );
}

function BookPanel({ book }: { book: Book }) {
  return (
    <section className="card panel">
      <h3>Book</h3>
      <dl className="mini-facts small">
        <dt>Title</dt>
        <dd>
          {book.title} ({book.id})
        </dd>
        <dt>ISBN</dt>
        <dd>{book.isbn}</dd>
        <dt>Status</dt>
        <dd>{book.status}</dd>
        {book.is_published && (
          <>
            <dt>Published</dt>
            <dd>{formatDate(book.publication_date)}</dd>
            <dt>MRP</dt>
            <dd>{rupees(book.mrp)}</dd>
            <dt>Copies sold</dt>
            <dd>{book.total_copies_sold.toLocaleString("en-IN")}</dd>
            <dt>Royalty earned</dt>
            <dd>{rupees(book.total_royalty_earned)}</dd>
            <dt>Paid / pending</dt>
            <dd>
              {rupees(book.royalty_paid)} / {rupees(book.royalty_pending)}
            </dd>
            <dt>Last payout</dt>
            <dd>{book.last_royalty_payout_date ? formatDate(book.last_royalty_payout_date) : "Never"}</dd>
            <dt>Printer</dt>
            <dd>{book.print_partner ?? "—"}</dd>
            <dt>Listed on</dt>
            <dd>{book.available_on.join(", ") || "—"}</dd>
          </>
        )}
      </dl>
    </section>
  );
}
