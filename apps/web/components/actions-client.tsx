"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, ExternalLink, Loader2, Send, ShieldAlert } from "lucide-react";
import { answerRequest, getDashboard } from "@/lib/api";
import type { ActionRequest } from "@/lib/types";

export function ActionsClient() {
  const [requests, setRequests] = useState<ActionRequest[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [submittingId, setSubmittingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const dashboard = await getDashboard();
      setRequests(dashboard.requests);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load requests");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function submit(request: ActionRequest) {
    setSubmittingId(request.id);
    setError(null);
    try {
      await answerRequest(request.id, answers[request.id] || "Completed by human.");
      setAnswers((current) => ({ ...current, [request.id]: "" }));
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save response");
    } finally {
      setSubmittingId(null);
    }
  }

  return (
    <>
      <div className="topline">
        <div>
          <p className="eyebrow">Agent inbox</p>
          <h2>Clear what only a human can clear.</h2>
        </div>
        <span className={requests.some((request) => request.request_type === "human_wall_handoff") ? "badge danger" : "badge"}>
          {requests.length} open
        </span>
      </div>
      {error ? <div className="error">{error}</div> : null}
      {loading ? <div className="empty loading"><Loader2 size={22} /> Loading requests...</div> : null}
      {!loading && requests.length === 0 ? <div className="empty"><CheckCircle2 size={24} /> No open requests.</div> : null}
      <div className="list">
        {requests.map((request) => (
          <div className="panel request" key={request.id}>
            <header>
              <div>
                <strong>{request.title}</strong>
                <p className="muted">{request.filing_name}</p>
              </div>
              <span className={request.request_type === "human_wall_handoff" ? "badge danger" : "badge"}>
                {request.request_type.replaceAll("_", " ")}
              </span>
            </header>
            <p>{request.prompt}</p>
            <p className="muted">{request.why_needed}</p>
            <div className="meta-line">
              {request.confidence ? <span className="confidence">{Math.round(request.confidence * 100)}% confidence</span> : null}
              {request.source_type ? <span>Source: {request.source_type}</span> : null}
              {request.proposed_answer ? <span>Agent proposed an answer</span> : null}
            </div>
            {request.request_type === "human_wall_handoff" ? (
              <div className="notice">
                <ShieldAlert size={18} />
                <span>PortalPilot will not handle credentials, MFA, legal declarations, submission, endorsement, or payment.</span>
              </div>
            ) : null}
            {request.portal_url ? (
              <a className="btn secondary inline-action" href={request.portal_url} target="_blank" rel="noreferrer">
                Open handoff location <ExternalLink size={17} />
              </a>
            ) : null}
            <div className="form-stack">
              <textarea
                aria-label={`Answer ${request.title}`}
                placeholder={request.proposed_answer || "Answer or confirm completion"}
                value={answers[request.id] || ""}
                onChange={(event) => setAnswers({ ...answers, [request.id]: event.target.value })}
              />
              <button className="btn" onClick={() => submit(request)} disabled={submittingId === request.id}>
                {submittingId === request.id ? <Loader2 size={17} className="loading" /> : <Send size={17} />}
                Save and resume
              </button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
