"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ExternalLink, Loader2, MonitorCog, ShieldAlert, X } from "lucide-react";
import { closeComputerUseAccessSession, getApiUrl, getFiling, isLocalApiUrl, resumeComputerUseAccessSession, startComputerUseAccessSession } from "@/lib/api";
import type { ComputerUseAccessSessionResponse, ComputerUseRunResponse, FilingDetail } from "@/lib/types";

export function FilingDetailClient({ id }: { id: string }) {
  const [detail, setDetail] = useState<FilingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [targetUrl, setTargetUrl] = useState("");
  const [accessSession, setAccessSession] = useState<ComputerUseAccessSessionResponse | null>(null);
  const [runnerResult, setRunnerResult] = useState<ComputerUseRunResponse | null>(null);
  const [runnerError, setRunnerError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const localApi = isLocalApiUrl();

  function normalizedPortalUrl() {
    const value = targetUrl.trim();
    try {
      const url = new URL(value);
      if (!["http:", "https:"].includes(url.protocol)) {
        return { error: "Use an http or https official portal URL." };
      }
      return { url: url.toString() };
    } catch {
      return { error: "Enter a valid official portal URL before opening the assisted browser." };
    }
  }

  useEffect(() => {
    getFiling(id)
      .then((loaded) => {
        setDetail(loaded);
        const sourceUrl = loaded.recommendation.sources[0]?.url || "";
        setTargetUrl(sourceUrl.includes("example.invalid") ? "" : sourceUrl);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load filing"));
  }, [id]);

  async function startBrowserRun() {
    const portal = normalizedPortalUrl();
    if (portal.error || !portal.url) {
      setRunnerError(portal.error || "Enter a valid official portal URL.");
      return;
    }
    setRunning(true);
    setRunnerError(null);
    setRunnerResult(null);
    setAccessSession(null);
    try {
      setAccessSession(await startComputerUseAccessSession(id, portal.url));
    } catch (err) {
      setRunnerError(err instanceof Error ? err.message : "Could not start assisted browser");
    } finally {
      setRunning(false);
    }
  }

  async function resumeBrowserRun() {
    if (!accessSession) return;
    const portal = normalizedPortalUrl();
    if (portal.error || !portal.url) {
      setRunnerError(portal.error || "Enter a valid official portal URL.");
      return;
    }
    setRunning(true);
    setRunnerError(null);
    try {
      const result = await resumeComputerUseAccessSession(id, accessSession.session_id, portal.url);
      setRunnerResult(result);
      setDetail(await getFiling(id));
      if (!(result.status === "blocked" && result.user_handoff_used && !result.user_handoff_timed_out)) {
        setAccessSession(null);
      }
    } catch (err) {
      setRunnerError(err instanceof Error ? err.message : "Could not resume browser agent");
    } finally {
      setRunning(false);
    }
  }

  async function closeBrowserSession() {
    if (!accessSession) return;
    setRunning(true);
    setRunnerError(null);
    try {
      await closeComputerUseAccessSession(id, accessSession.session_id);
      setAccessSession(null);
    } catch (err) {
      setRunnerError(err instanceof Error ? err.message : "Could not close assisted browser");
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

  const hasBrowserObservation = detail.checklist.length > 0 || detail.fields.length > 0;

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

      {hasBrowserObservation ? (
      <section className="split">
        <div className="panel card-panel">
          <div className="section-heading">
            <h3>Observed recommendation</h3>
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
          <h3>Observed readiness</h3>
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
      ) : (
      <section className="section panel card-panel">
        <div className="section-heading">
          <div>
            <h3>Browser observation required</h3>
            <p className="muted">PortalPilot creates the recommendation, readiness checklist, field confidence records, and questions only after the browser agent observes the live form.</p>
          </div>
          <ShieldAlert size={22} />
        </div>
      </section>
      )}

      <section className="section panel card-panel">
        <div className="section-heading">
          <div>
            <h3>Safe browser run</h3>
            <p className="muted">OpenAI computer use opens a visible browser for access steps, then resumes only non-final portal work.</p>
          </div>
          <MonitorCog size={22} />
        </div>
        {!localApi ? (
          <div className="notice">
            <strong>Local API required for visible browser handoff.</strong>
            <span>Your UI is pointing at {getApiUrl()}. For this demo, set NEXT_PUBLIC_API_URL to your local FastAPI server so Chromium opens on this machine.</span>
          </div>
        ) : null}
        <div className="browser-runner">
          <label>
            Portal URL
            <input value={targetUrl} onChange={(event) => setTargetUrl(event.target.value)} placeholder="https://official-portal.example.gov/form" />
          </label>
          <button className="btn compact" onClick={startBrowserRun} disabled={running || !targetUrl.trim()}>
            {running ? <Loader2 size={17} className="spin" /> : <MonitorCog size={17} />}
            {running ? "Working..." : "Open assisted browser"}
          </button>
        </div>
        {runnerError ? <div className="error">{runnerError}</div> : null}
        {accessSession ? (
          <div className="notice">
            <strong>Visible browser session ready.</strong>
            <span>{accessSession.prompt}</span>
            {accessSession.current_url ? <span>Current URL: {accessSession.current_url}</span> : null}
            {accessSession.handoff_reason ? <span>{accessSession.handoff_reason}</span> : null}
            <button className="btn compact" onClick={resumeBrowserRun} disabled={running}>
              {running ? <Loader2 size={17} className="spin" /> : <MonitorCog size={17} />}
              Resume agent
            </button>
            <button className="btn secondary compact" onClick={closeBrowserSession} disabled={running}>
              <X size={17} />
              Close session
            </button>
          </div>
        ) : null}
        {runnerResult ? (
          <div className="list stacked-list">
            {runnerResult.recommendation ? (
              <div className="request">
                <header>
                  <strong>{runnerResult.recommendation.filing_name}</strong>
                  <span className="confidence">{Math.round(runnerResult.recommendation.confidence * 100)}%</span>
                </header>
                <p className="muted">{runnerResult.recommendation.reason}</p>
              </div>
            ) : null}
            <div className="request">
              <header>
                <strong>{runnerResult.status.replaceAll("_", " ")}</strong>
                <span className="badge">{runnerResult.mode}</span>
              </header>
              <p className="muted">{runnerResult.blocked_reason || runnerResult.activity.at(-1)?.summary || "Browser run completed."}</p>
              {runnerResult.user_handoff_used ? (
                <p className="notice">
                  {runnerResult.user_handoff_timed_out
                    ? "The access handoff timed out before the page became safe for the agent to resume."
                    : "A visible Chromium window was handed to you for login, CAPTCHA, MFA, or authorization."}
                </p>
              ) : null}
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
            {runnerResult.checklist.map((item) => (
              <div className="event" key={`${item.label}-${item.status}`}>
                <header>
                  <strong>{item.label}</strong>
                  <span className="badge">{item.status.replaceAll("_", " ")}</span>
                </header>
                <p className="muted">{item.reason}</p>
              </div>
            ))}
            {runnerResult.fields.map((field) => (
              <div className="field-row" key={`${field.portal_section}-${field.field_label}`}>
                <header>
                  <div>
                    <strong>{field.field_label}</strong>
                    <p className="muted">{field.portal_section}</p>
                  </div>
                  <span className="badge">{field.status.replaceAll("_", " ")}</span>
                </header>
                <p className="muted">{field.reason}</p>
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

      {hasBrowserObservation ? (
      <section className="section panel card-panel">
        <div className="section-heading">
          <h3>Observed field confidence</h3>
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
        </div>
      </section>
      ) : null}
    </>
  );
}
