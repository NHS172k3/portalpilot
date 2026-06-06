"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Bot, FilePlus2, Loader2, Send, ShieldAlert } from "lucide-react";
import { createFiling, getDashboard } from "@/lib/api";
import type { Dashboard, FilingCard, FilingStatus } from "@/lib/types";

const columns: { status: FilingStatus; label: string }[] = [
  { status: "not_started", label: "Not Started" },
  { status: "in_progress", label: "In Progress" },
  { status: "needs_you", label: "Needs You" },
  { status: "completed", label: "Completed" },
];

export function DashboardClient() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [description, setDescription] = useState("");
  const [companyContext, setCompanyContext] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      setDashboard(await getDashboard());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load dashboard");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      await createFiling(description, companyContext);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create filing");
    } finally {
      setSubmitting(false);
    }
  }

  const hasFilings = useMemo(
    () => dashboard && Object.values(dashboard.board).some((cards) => cards.length > 0),
    [dashboard],
  );

  return (
    <>
      <div className="topline">
        <div>
          <p className="eyebrow">Background filing system</p>
          <h2>Tell the agent what needs filing.</h2>
        </div>
        <span className="badge warn">
          <ShieldAlert size={14} /> Human boundaries enforced
        </span>
      </div>

      <section className="hero-grid">
        <div className="panel intake">
          <div>
            <h3>User-added filing</h3>
            <p className="muted">
              PortalPilot researches official sources, drafts a filing plan, and pauses only for missing facts or human-only walls.
            </p>
          </div>
          <div className="form-stack">
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              aria-label="Filing need"
              placeholder="Describe the filing, renewal, licence, registration, or report you need prepared."
            />
            <input
              value={companyContext}
              onChange={(event) => setCompanyContext(event.target.value)}
              aria-label="Company context"
              placeholder="Optional context: entity stage, location, industry, deadline, or known reference number."
            />
            <div className="button-row">
              <button className="btn" onClick={submit} disabled={submitting || description.length < 8}>
                {submitting ? <Loader2 size={17} className="loading" /> : <Send size={17} />}
                Run filing agent
              </button>
              <Link className="btn secondary" href="/actions">
                Open inbox <ArrowRight size={17} />
              </Link>
            </div>
          </div>
        </div>

        <div className="metric-grid">
          <Metric value={dashboard?.needs_you_count ?? 0} label="Needs you" />
          <Metric value={dashboard?.in_progress_count ?? 0} label="In progress" />
          <Metric value={dashboard?.upcoming_deadlines ?? 0} label="Deadlines tracked" />
        </div>
      </section>

      {error ? <div className="section error">{error}</div> : null}

      <section className="section">
        <div className="topline">
          <h3>Filings board</h3>
          <Link href="/filings" className="badge">
            View all <ArrowRight size={14} />
          </Link>
        </div>
        {loading ? <div className="empty loading">Loading agent board...</div> : null}
        {!loading && !hasFilings ? (
          <div className="empty">
            <FilePlus2 size={24} />
            <p>No filings yet. Describe a filing need to create the first agent run.</p>
          </div>
        ) : null}
        {dashboard ? <Board dashboard={dashboard} /> : null}
      </section>

      <section className="section split">
        <div className="panel card-panel">
          <h3>Action Center</h3>
          <div className="list stacked-list">
            {dashboard?.requests.slice(0, 4).map((request) => (
              <Link className="request" href="/actions" key={request.id}>
                <header>
                  <strong>{request.title}</strong>
                  <span className={request.request_type === "human_wall_handoff" ? "badge danger" : "badge"}>{request.request_type}</span>
                </header>
                <p className="muted">{request.prompt}</p>
                <div className="meta-line">
                  {request.confidence ? <span>Confidence {Math.round(request.confidence * 100)}%</span> : null}
                  {request.source_type ? <span>Source {request.source_type}</span> : null}
                </div>
              </Link>
            ))}
            {dashboard && dashboard.requests.length === 0 ? <div className="empty">No open requests.</div> : null}
          </div>
        </div>
        <div className="panel card-panel">
          <h3>Recent activity</h3>
          <div className="list stacked-list">
            {dashboard?.recent_activity.map((event, index) => (
              <div className="event" key={`${event.event_type}-${index}`}>
                <header>
                  <strong>{event.summary}</strong>
                  <Bot size={18} />
                </header>
                <p className="muted">{event.detail || event.event_type}</p>
              </div>
            ))}
            {dashboard && dashboard.recent_activity.length === 0 ? <div className="empty">Agent events will appear here.</div> : null}
          </div>
        </div>
      </section>
    </>
  );
}

function Metric({ value, label }: { value: number; label: string }) {
  return (
    <div className="panel metric">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

export function Board({ dashboard }: { dashboard: Dashboard }) {
  return (
    <div className="board">
      {columns.map((column) => (
        <div className="column" key={column.status}>
          <div className="column-title">
            {column.label}
            <span>{dashboard.board[column.status]?.length || 0}</span>
          </div>
          {(dashboard.board[column.status] || []).map((card) => (
            <FilingCardView card={card} key={card.id} />
          ))}
        </div>
      ))}
    </div>
  );
}

export function FilingCardView({ card }: { card: FilingCard }) {
  const deadline = card.deadline ? new Date(card.deadline).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : null;

  return (
    <Link className="filing-card" href={`/filings/${card.id}`}>
      <div>
        <strong>{card.name}</strong>
        <span className="muted">
          {card.agency} / {card.jurisdiction}
        </span>
      </div>
      <div className="progress" aria-label={`${card.progress}% complete`}>
        <span style={{ width: `${card.progress}%` }} />
      </div>
      <div className="meta-line">
        <span className={card.open_requests > 0 ? "badge danger" : "badge"}>{card.open_requests} open requests</span>
        {deadline ? <span className="badge warn">Due {deadline}</span> : null}
      </div>
      <small className="muted">{card.last_agent_action}</small>
    </Link>
  );
}
