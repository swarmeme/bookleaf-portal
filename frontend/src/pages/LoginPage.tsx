import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ErrorNote } from "../components/ui";

// Demo accounts from the seed data, offered as one-click fills for reviewers.
const DEMO_ACCOUNTS = [
  { label: "Author: Priya Sharma", email: "priya.sharma@email.com", password: "author123" },
  { label: "Author: Kavita Deshmukh (book in production)", email: "kavita.deshmukh@email.com", password: "author123" },
  { label: "Admin: Aarav Mehta", email: "admin@bookleaf.com", password: "admin123" },
];

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const user = await login(email, password);
      const home = user.role === "admin" ? "/admin/tickets" : "/books";
      const fromMatchesRole = from && from.startsWith("/admin") === (user.role === "admin");
      navigate(fromMatchesRole ? from : home, { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card card">
        <div className="brand brand-lg">
          <img src="/favicon.svg" alt="" width={34} height={34} />
          <span>BookLeaf</span>
        </div>
        <h1>Sign in to BookLeaf Support</h1>
        <p className="muted">Authors: see your books and get help. BookLeaf team: manage the support queue.</p>

        <form onSubmit={onSubmit} className="stack">
          <label className="field">
            <span>Email</span>
            <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <ErrorNote error={error} />
          <button className="btn btn-primary" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div className="demo-accounts">
          <p className="muted small">Demo accounts (all authors use <code>author123</code>):</p>
          {DEMO_ACCOUNTS.map((acc) => (
            <button
              key={acc.email}
              type="button"
              className="btn btn-link small"
              onClick={() => {
                setEmail(acc.email);
                setPassword(acc.password);
              }}
            >
              {acc.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
