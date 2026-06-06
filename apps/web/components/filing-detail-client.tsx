"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ExternalLink, Loader2, MonitorCog, ShieldAlert } from "lucide-react";
import { getFiling, runComputerUse } from "@/lib/api";
import type { ComputerUseRunResponse, FilingDetail } from "@/lib/types";

export function FilingDetailClient({ id }: { id: string }) {
  const [detail, setDetail] = useState<FilingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [targetUrl, setTargetUrl] = useState("");
  const [runnerResult, setRunnerResult] = useState<ComputerUseRunResponse | null>(null);
  const [runnerError, setRunnerError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    getFiling(id)
      .then((loaded) => {
        setDetail(loaded);
        setTargetUrl(loaded.recommendation.sources[0]?.url || "");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load filing"));
  }, [id]);

  async function startBrowserRun() {
    if (!targetUrl.trim()) return;
    setRunning(true);
    setRunnerError(null);
    setRunnerResult(null);
    try {
      setRunnerResult(await runComputerUse(id, targetUrl.trim()));
    } catch (err) {
      setRunnerError(err instanceof Error ? err.message : "Computer-use run failed");
    } finally {
      setRunning(false);
    }
  }

  if (error) return <div className="error">{error}</div>;
  if (!detail) {
    return (
      <div className="empty loading">
        <Loader2 size={22} /> Loading filing...
      </div>
    );
  }

  return (
    <>
      <div className="topline">
        <div>
          <Link className="badge" href="/filings">
            <ArrowLeft size={14} /> Board
          </Link>
          <h2 className="return-title">{detail.card.name}</h2>
          <p className="muted">{detail.card.agency} / {detail.card.jurisdiction}</p>
        </div>
        <span className="badge warn">{detail.card.status.replaceAll("_", " ")}</span>
      </div>

      <section className="split">
        <div className="panel card-panel">
          <div className="section-heading">
            <h3>Recommendation evidence</h3>
            <span className="confidence">{Math.round(detail.recommendation.confidence * 100)}%</span>
          </div>
          <p>{detail.recommendation.reason}</p>
          <div className="meta-line">
            <span>{detail.recommendation.prerequisites.length} prerequisites</span>
            {detail.recommendation.fee_expectation ? <span>Fee: {detail.recommendation.fee_expectation}</span> : null}
            {detail.recommendation.deadline ? <span>Deadline: {detail.recommendation.deadline}</span> : null}
          </div>
          <div className="list">
            {detail.recommendation.sources.map((source) => (
              <a className="event" href={source.url} target="_blank" rel="noreferrer" key={source.url}>
                <header>
                  <strong>{source.title}</strong>
                  <ExternalLink size={16} />
                </header>
                <p className="muted">{source.summary}</p>
              </a>
            ))}
            {detail.recommendation.sources.length === 0 ? <div className="empty">No source links yet.</div> : null}
          </div>
          {detail.recommendation.warnings.length > 0 ? (
            <div className="notice">
              <span>{detail.recommendation.warnings.join(" ")}</span>
            </div>
          ) : null}
        </div>

        <div className="panel card-panel">
          <h3>Readiness</h3>
          <div className="list stacked-list">
            {detail.checklist.map((item) => (
              <div className="request" key={item.label}>
                <header>
                  <strong>{item.label}</strong>
                  <span className="badge">{item.status.replaceAll("_", " ")}</span>
                </header>
                <p className="muted">{item.reason}</p>
              </div>
            ))}
            {detail.checklist.length === 0 ? <div className="empty">No readiness checklist yet.</div> : null}
          </div>
        </div>
      </section>

      <section className="section panel card-panel">
        <div className="section-heading">
          <div>
            <h3>Safe browser run</h3>
            <p className="muted">OpenAI computer use prepares only non-final portal work and pauses at access or legal boundaries.</p>
          </div>
          <MonitorCog size={22} />
        </div>
        <div className="browser-runner">
          <label>
            Portal URL
            <input value={targetUrl} onChange={(event) => setTargetUrl(event.target.value)} placeholder="https://official-portal.example.gov/form" />
          </label>
          <button className="btn compact" onClick={startBrowserRun} disabled={running || !targetUrl.trim()}>
            {running ? <Loader2 size={17} className="spin" /> : <MonitorCog size={17} />}
            {running ? "Running..." : "Run safe browser agent"}
          </button>
        </div>
        {runnerError ? <div className="error">{runnerError}</div> : null}
        {runnerResult ? (
          <div className="list stacked-list">
            <div className="request">
              <header>
                <strong>{runnerResult.status.replaceAll("_", " ")}</strong>
                <span className="badge">{runnerResult.mode}</span>
              </header>
              <p className="muted">{runnerResult.blocked_reason || runnerResult.activity.at(-1)?.summary || "Browser run completed."}</p>
              {runnerResult.current_url ? <p className="muted">Current URL: {runnerResult.current_url}</p> : null}
            </div>
            {runnerResult.requests.map((request) => (
              <div className="request urgent" key={`${request.title}-${request.why_needed}`}>
                <header>
                  <strong><ShieldAlert size={16} /> {request.title}</strong>
                  <Link className="badge warn" href="/actions">Needs You</Link>
                </header>
                <p>{request.prompt}</p>
                <p className="muted">{request.why_needed}</p>
              </div>
            ))}
            {runnerResult.steps.map((step) => (
              <div className="event" key={`${step.step}-${step.action_type}`}>
                <header>
                  <strong>Step {step.step}: {step.action_type}</strong>
                  <span className="badge">{step.status}</span>
                </header>
                <p className="muted">{step.blocked_reason || step.summary}</p>
              </div>
            ))}
          </div>
        ) : null}
      </section>

      <section className="section panel card-panel">
        <div className="section-heading">
          <h3>Field confidence</h3>
          <span className="badge">{detail.fields.length} fields</span>
        </div>
        <div className="list stacked-list">
          {detail.fields.map((field) => (
            <div className="field-row" key={`${field.portal_section}-${field.field_label}`}>
              <header>
                <div>
                  <strong>{field.field_label}</strong>
                  <p className="muted">{field.portal_section}</p>
                </div>
                <div className="meta-line align-end">
                  <span className="badge">{field.status.replaceAll("_", " ")}</span>
                  <span className="confidence">{Math.round(field.confidence * 100)}%</span>
                </div>
              </header>
              <p>{field.proposed_value || "Left blank"}</p>
              <div className="meta-line">
                <span>Source: {field.source_type}</span>
                <span>Sensitivity: {field.sensitivity}</span>
              </div>
              <p className="muted">{field.reason}</p>
            </div>
          ))}
          {detail.fields.length === 0 ? <div className="empty">No field confidence records yet.</div> : null}
        </div>
      </section>
    </>
  );
}
