import type { Message } from "../api/types";
import { formatDateTime } from "../lib/format";

interface Props {
  authorName: string;
  description: string;
  createdAt: string;
  attachmentName: string | null;
  messages: Message[];
  /** Which side is "me": authors see their own messages on the right, admins see the team's. */
  viewer: "author" | "admin";
}

/** The author-visible conversation: the original query followed by every message. */
export default function Thread({ authorName, description, createdAt, attachmentName, messages, viewer }: Props) {
  return (
    <ol className="thread">
      <Bubble mine={viewer === "author"} from={authorName} team={false} at={createdAt} label="Original query">
        <p className="pre">{description}</p>
        {attachmentName && <p className="attachment">📎 {attachmentName}</p>}
      </Bubble>
      {messages.map((m) => {
        const team = m.sender.role === "admin";
        return (
          <Bubble
            key={m.id}
            mine={team === (viewer === "admin")}
            team={team}
            from={team ? `${m.sender.name} · BookLeaf` : m.sender.name}
            at={m.created_at}
            label={viewer === "admin" && m.used_ai_draft ? "AI-assisted" : undefined}
          >
            <p className="pre">{m.body}</p>
          </Bubble>
        );
      })}
    </ol>
  );
}

function Bubble({
  mine,
  team,
  from,
  at,
  label,
  children,
}: {
  mine: boolean;
  team: boolean;
  from: string;
  at: string;
  label?: string;
  children: React.ReactNode;
}) {
  return (
    <li className={`bubble ${mine ? "mine" : ""} ${team ? "team" : "author"}`}>
      <div className="bubble-meta">
        <strong>{from}</strong>
        <span>{formatDateTime(at)}</span>
        {label && <span className="bubble-label">{label}</span>}
      </div>
      {children}
    </li>
  );
}
