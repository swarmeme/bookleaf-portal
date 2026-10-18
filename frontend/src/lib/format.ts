const rupeeFormat = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

export const rupees = (amount: number | null | undefined) => (amount == null ? "—" : rupeeFormat.format(amount));

export const formatDate = (iso: string | null | undefined) =>
  iso ? new Date(iso.length === 10 ? `${iso}T00:00:00` : iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "—";

export const formatDateTime = (iso: string) =>
  new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });

/** "5m", "3h", "2d": compact ticket age for the queue. */
export function age(iso: string, now = Date.now()): string {
  const minutes = Math.max(0, Math.floor((now - new Date(iso).getTime()) / 60000));
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

export const hoursSince = (iso: string, now = Date.now()) => (now - new Date(iso).getTime()) / 3_600_000;

export function timeAgo(iso: string): string {
  const a = age(iso);
  return a === "0m" ? "just now" : `${a} ago`;
}
