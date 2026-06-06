"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, FilePlus2, Loader2 } from "lucide-react";
import { Board } from "@/components/dashboard-client";
import { getDashboard } from "@/lib/api";
import type { Dashboard } from "@/lib/types";

export function FilingsBoardClient() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboard()
      .then(setDashboard)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load filings"))
      .finally(() => setLoading(false));
  }, []);

  const hasFilings = useMemo(
    () => dashboard && Object.values(dashboard.board).some((cards) => cards.length > 0),
    [dashboard],
  );

  return (
    <>
      <div className="topline">
        <div>
          <p className="eyebrow">Filing operations</p>
          <h2>Filings board</h2>
        </div>
        <Link className="btn secondary" href="/">
          Add filing <ArrowRight size={17} />
        </Link>
      </div>

      {error ? <div className="error">{error}</div> : null}
      {loading ? (
        <div className="empty loading">
          <Loader2 size={22} /> Loading filings...
        </div>
      ) : null}
      {!loading && !hasFilings ? (
        <div className="empty">
          <FilePlus2 size={24} />
          <p>No filings are tracked yet. Add a filing from Home to start an agent run.</p>
        </div>
      ) : null}
      {dashboard ? <Board dashboard={dashboard} /> : null}

      <section className="section metric-grid">
        <div className="panel metric">
          <strong>{dashboard?.needs_you_count ?? 0}</strong>
          <span>Needs You items</span>
        </div>
        <div className="panel metric">
          <strong>{dashboard?.in_progress_count ?? 0}</strong>
          <span>Agent runs active</span>
        </div>
        <div className="panel metric">
          <strong>{dashboard?.upcoming_deadlines ?? 0}</strong>
          <span>Upcoming deadlines</span>
        </div>
      </section>
    </>
  );
}
