// Subscribes to the server's SSE stream and refreshes affected queries, so a reply from
// the team shows up on the author's screen (and new tickets in the admin queue) without
// a page refresh.

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { keys } from "./hooks";

const EVENT_TYPES = ["ticket.created", "ticket.updated", "ticket.message", "ticket.note"] as const;

export type LiveStatus = "connecting" | "live" | "reconnecting";

export function useLiveUpdates(): LiveStatus {
  const qc = useQueryClient();
  const [status, setStatus] = useState<LiveStatus>("connecting");

  useEffect(() => {
    const source = new EventSource("/api/events");
    let wasDisconnected = false;

    source.onopen = () => {
      setStatus("live");
      // Events sent while we were disconnected are gone; refetch everything ticket-related once.
      if (wasDisconnected) qc.invalidateQueries({ queryKey: ["tickets"] });
    };
    // EventSource reconnects by itself (the server sets retry: 3000).
    source.onerror = () => {
      wasDisconnected = true;
      setStatus("reconnecting");
    };

    const onEvent = (event: MessageEvent) => {
      const { type, ticket_id } = JSON.parse(event.data) as { type: string; ticket_id: number };
      qc.invalidateQueries({ queryKey: ["tickets", "queue"] });
      qc.invalidateQueries({ queryKey: keys.stats });
      qc.invalidateQueries({ queryKey: keys.myTickets, exact: true });
      qc.invalidateQueries({ queryKey: keys.myTicket(ticket_id) });
      qc.invalidateQueries({ queryKey: keys.adminTicket(ticket_id) });
      if (type === "ticket.message") qc.invalidateQueries({ queryKey: keys.draft(ticket_id) });
    };
    EVENT_TYPES.forEach((type) => source.addEventListener(type, onEvent));

    return () => source.close();
  }, [qc]);

  return status;
}
