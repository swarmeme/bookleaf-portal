import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useBooks, useCreateTicket } from "../../api/hooks";
import { ErrorNote, fieldError } from "../../components/ui";

const GENERAL = "";

export default function NewTicketPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const books = useBooks();
  const create = useCreateTicket();

  const [bookId, setBookId] = useState(params.get("book") ?? GENERAL);
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [attachment, setAttachment] = useState<File | null>(null);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    create.mutate(
      {
        book_id: bookId || null,
        subject,
        description,
        attachment_name: attachment?.name ?? null,
      },
      { onSuccess: (ticket) => navigate(`/tickets/${ticket.id}`, { state: { created: true } }) },
    );
  }

  return (
    <div className="narrow stack-lg">
      <div>
        <Link to="/tickets" className="back">
          ← My Tickets
        </Link>
        <h1>How can we help?</h1>
        <p className="muted">
          Tell us what's going on and the BookLeaf team will get back to you here. You'll see our reply on this page
          as soon as it's sent.
        </p>
      </div>

      <form className="card stack" onSubmit={onSubmit} noValidate>
        <label className="field">
          <span>Which book is this about?</span>
          <select value={bookId} onChange={(e) => setBookId(e.target.value)} disabled={books.isPending}>
            <option value={GENERAL}>General / Account level</option>
            {books.data?.map((book) => (
              <option key={book.id} value={book.id}>
                {book.title} ({book.status})
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Subject</span>
          <input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            maxLength={200}
            placeholder="e.g. Royalty for last quarter not received"
            required
          />
          <FieldError message={fieldError(create.error, "subject")} />
        </label>

        <label className="field">
          <span>Details</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={7}
            maxLength={5000}
            placeholder="Share as much detail as you can: dates, amounts, platform links, what you expected to see."
            required
          />
          <span className="hint">{description.length} / 5000</span>
          <FieldError message={fieldError(create.error, "description")} />
        </label>

        <label className="field">
          <span>Attachment (optional)</span>
          <input type="file" accept="image/*,.pdf" onChange={(e) => setAttachment(e.target.files?.[0] ?? null)} />
          <span className="hint">
            Screenshots or photos help (e.g. of a print defect). We'll note the file name on your ticket; the team may
            ask you to email the file itself.
          </span>
        </label>

        {create.error && !fieldError(create.error, "subject") && !fieldError(create.error, "description") && (
          <ErrorNote error={create.error} />
        )}

        <div className="row-end">
          <button className="btn btn-primary" disabled={create.isPending}>
            {create.isPending ? "Sending…" : "Submit ticket"}
          </button>
        </div>
      </form>
    </div>
  );
}

function FieldError({ message }: { message?: string }) {
  return message ? <span className="field-error">{message}</span> : null;
}
