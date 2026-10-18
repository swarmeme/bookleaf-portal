import { Link } from "react-router-dom";
import { useBooks, useRoyaltySummary } from "../../api/hooks";
import type { Book, PayoutStatus, RoyaltySummary } from "../../api/types";
import { EmptyState, ErrorNote, PageLoader } from "../../components/ui";
import { formatDate, rupees } from "../../lib/format";
import { PAYOUT_LABELS, PRODUCTION_STAGES } from "../../lib/labels";

export default function BooksPage() {
  const books = useBooks();
  const royalty = useRoyaltySummary();

  if (books.isPending || royalty.isPending) return <PageLoader />;
  if (books.error || royalty.error) return <ErrorNote error={books.error ?? royalty.error} />;

  const payoutByBook = new Map(royalty.data.books.map((b) => [b.book_id, b.payout_status]));

  return (
    <div className="stack-lg">
      <div className="page-head">
        <div>
          <h1>My Books</h1>
          <p className="muted">Sales and royalties for every title you publish with BookLeaf.</p>
        </div>
        <Link to="/tickets/new" className="btn btn-primary">
          Ask a question
        </Link>
      </div>

      <RoyaltyOverview summary={royalty.data} />

      {books.data.length === 0 ? (
        <EmptyState title="No books yet">Once your manuscript is received, your book will appear here.</EmptyState>
      ) : (
        <div className="book-grid">
          {books.data.map((book) => (
            <BookCard key={book.id} book={book} payoutStatus={payoutByBook.get(book.id)} />
          ))}
        </div>
      )}
    </div>
  );
}

function RoyaltyOverview({ summary }: { summary: RoyaltySummary }) {
  let note: string;
  if (summary.total_pending === 0) note = "You're fully paid up. New royalties are calculated every quarter.";
  else if (summary.meets_threshold)
    note = `Your pending ${rupees(summary.total_pending)} is due in the payout on or before ${formatDate(summary.next_payout_date)}.`;
  else
    note = `Payouts start at ${rupees(summary.payout_threshold)}. Your ${rupees(summary.total_pending)} rolls over to the next quarter until it reaches that.`;

  return (
    <section className="card">
      <div className="stats-row">
        <Stat label="Total royalty earned" value={rupees(summary.total_earned)} />
        <Stat label="Paid to you" value={rupees(summary.total_paid)} />
        <Stat label="Pending" value={rupees(summary.total_pending)} highlight={summary.total_pending > 0} />
        <Stat label="Next payout date" value={formatDate(summary.next_payout_date)} />
      </div>
      <p className="muted small payout-note">
        {note} Royalties are calculated quarterly and paid by bank transfer within 45 days of each quarter ending.
      </p>
    </section>
  );
}

function Stat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`stat ${highlight ? "stat-highlight" : ""}`}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  );
}

function BookCard({ book, payoutStatus }: { book: Book; payoutStatus?: PayoutStatus }) {
  return (
    <article className="card book-card">
      <header className="book-head">
        <div>
          <h2>{book.title}</h2>
          <p className="muted small">
            {book.genre} · ISBN {book.isbn}
          </p>
        </div>
        <span className={`badge ${book.is_published ? "book-live" : "book-production"}`}>{book.status}</span>
      </header>

      {book.is_published ? (
        <>
          <dl className="facts">
            <Fact label="Published" value={formatDate(book.publication_date)} />
            <Fact label="MRP" value={rupees(book.mrp)} />
            <Fact label="Copies sold" value={book.total_copies_sold.toLocaleString("en-IN")} />
            <Fact label="Royalty earned" value={rupees(book.total_royalty_earned)} />
            <Fact label="Royalty paid" value={rupees(book.royalty_paid)} />
            <Fact label="Royalty pending" value={rupees(book.royalty_pending)} />
            <Fact label="Last payout" value={book.last_royalty_payout_date ? formatDate(book.last_royalty_payout_date) : "None yet"} />
            <Fact label="Payout status" value={payoutStatus ? PAYOUT_LABELS[payoutStatus] : "—"} />
          </dl>
          <p className="muted small">
            Available on: {book.available_on.length ? book.available_on.join(", ") : "not listed yet"}
          </p>
        </>
      ) : (
        <ProductionProgress status={book.status} />
      )}
      <footer className="book-foot">
        <Link to={`/tickets/new?book=${book.id}`} className="btn btn-link small">
          Question about this book?
        </Link>
      </footer>
    </article>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="fact">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

/** Books in production have no sales yet, so show where they are in the pipeline instead of a row of zeros. */
function ProductionProgress({ status }: { status: string }) {
  const stage = status.replace(/^In Production - /, "");
  const current = PRODUCTION_STAGES.indexOf(stage);
  return (
    <div className="production">
      <p className="small">
        Currently in <strong>{stage}</strong>. Sales and royalty figures will appear here once your book is live.
      </p>
      <ol className="stages">
        {PRODUCTION_STAGES.map((name, i) => (
          <li key={name} className={i < current ? "done" : i === current ? "current" : ""}>
            {name}
          </li>
        ))}
      </ol>
    </div>
  );
}
