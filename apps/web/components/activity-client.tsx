"use client";

import { useEffect, useState } from "react";
import { Bot, Loader2 } from "lucide-react";
import { getDashboard } from "@/lib/api";
import type { ActivityEvent } from "@/lib/types";

export function ActivityClient() {
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboard()
      .then((dashboard) => setActivity(dashboard.recent_activity))
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load activity"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <div className="topline">
        <div>
          <p className="eyebrow">Audit trail</p>
          <h2>Activity</h2>
        </div>
      </div>
      {error ? <div className="error">{error}</div> : null}
      {loading ? (
        <div className="empty loading">
          <Loader2 size={22} /> Loading activity...
        </div>
      ) : null}
      <div className="list">
        {activity.map((event, index) => (
          <div className="panel event" key={`${event.event_type}-${index}`}>
            <header>
              <strong>{event.summary}</strong>
              <Bot size={18} />
            </header>
            <p className="muted">{event.detail || event.event_type}</p>
          </div>
        ))}
        {!loading && activity.length === 0 ? <div className="empty">No activity yet.</div> : null}
      </div>
    </>
  );
}
