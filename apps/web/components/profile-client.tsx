"use client";

import { useEffect, useState } from "react";
import { Building2, FileText, Loader2, Save, Upload, Users } from "lucide-react";
import { extractDocument, getProfile, updateProfile } from "@/lib/api";
import type { CompanyProfile, DocumentExtractResponse } from "@/lib/types";

const fields: { key: keyof CompanyProfile; label: string; multiline?: boolean }[] = [
  { key: "legal_name", label: "Legal name" },
  { key: "trading_name", label: "Trading name" },
  { key: "registration_id", label: "Registration ID" },
  { key: "address", label: "Address", multiline: true },
  { key: "industry_summary", label: "Industry summary", multiline: true },
  { key: "primary_contact_email", label: "Primary contact email" },
  { key: "primary_contact_phone", label: "Primary contact phone" },
  { key: "filing_notes", label: "Reusable filing notes", multiline: true },
];

export function ProfileClient() {
  const [profile, setProfile] = useState<CompanyProfile>({});
  const [fileName, setFileName] = useState("founder-notes.txt");
  const [content, setContent] = useState("Company: Example Labs Pte Ltd\nIndustry: software platform for operations teams\nContact: founder@example.com");
  const [extraction, setExtraction] = useState<DocumentExtractResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    getProfile()
      .then(setProfile)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load profile"))
      .finally(() => setLoading(false));
  }, []);

  async function saveProfile() {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      setProfile(await updateProfile(profile));
      setNotice("Profile saved. Agents will reuse these facts across filings.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile");
    } finally {
      setSaving(false);
    }
  }

  async function runExtraction() {
    setExtracting(true);
    setError(null);
    setNotice(null);
    try {
      setExtraction(await extractDocument(fileName, content));
      setNotice("Candidate facts extracted with source, confidence, and sensitivity labels.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not extract document");
    } finally {
      setExtracting(false);
    }
  }

  return (
    <>
      <div className="topline">
        <div>
          <p className="eyebrow">Shared knowledge base</p>
          <h2>Company Profile</h2>
        </div>
        <span className="badge warn">Reusable filing facts</span>
      </div>
      {error ? <div className="error">{error}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}
      {loading ? (
        <div className="empty loading">
          <Loader2 size={22} /> Loading profile...
        </div>
      ) : null}
      {!loading ? (
        <section className="split">
          <div className="panel card-panel">
            <h3 className="icon-heading">
              <Building2 /> Details
            </h3>
            <div className="form-stack stacked-list">
              {fields.map((field) =>
                field.multiline ? (
                  <textarea
                    key={field.key}
                    aria-label={field.label}
                    placeholder={field.label}
                    value={(profile[field.key] as string | null) || ""}
                    onChange={(event) => setProfile({ ...profile, [field.key]: event.target.value })}
                  />
                ) : (
                  <input
                    key={field.key}
                    aria-label={field.label}
                    placeholder={field.label}
                    value={(profile[field.key] as string | null) || ""}
                    onChange={(event) => setProfile({ ...profile, [field.key]: event.target.value })}
                  />
                ),
              )}
              <button className="btn" onClick={saveProfile} disabled={saving}>
                {saving ? <Loader2 size={17} className="loading" /> : <Save size={17} />}
                Save profile
              </button>
            </div>
          </div>

          <div className="panel card-panel">
            <h3 className="icon-heading">
              <FileText /> Document Library
            </h3>
            <p className="muted">
              Paste text from a short document to extract sourced candidate facts. Document instructions are treated as untrusted content.
            </p>
            <div className="form-stack">
              <input aria-label="File name" value={fileName} onChange={(event) => setFileName(event.target.value)} />
              <textarea aria-label="Document content" value={content} onChange={(event) => setContent(event.target.value)} />
              <button className="btn" onClick={runExtraction} disabled={extracting || content.length < 8}>
                {extracting ? <Loader2 size={17} className="loading" /> : <Upload size={17} />}
                Extract facts
              </button>
            </div>
            <div className="list stacked-list">
              {extraction?.facts.map((fact) => (
                <div className="field-row" key={`${fact.label}-${fact.value}`}>
                  <header>
                    <strong>{fact.label}</strong>
                    <span className="confidence">{Math.round(fact.confidence * 100)}%</span>
                  </header>
                  <p>{fact.value || "No value extracted"}</p>
                  <div className="meta-line">
                    <span>Source: {fact.source_type}</span>
                    <span>Sensitivity: {fact.sensitivity}</span>
                  </div>
                  {fact.evidence_note ? <p className="muted">{fact.evidence_note}</p> : null}
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      <section className="section panel card-panel">
        <h3 className="icon-heading">
          <Users /> People
        </h3>
        <p className="muted">
          People records are part of the shared filing knowledge base. Sensitive identifiers remain human-reviewed before use.
        </p>
        <div className="empty compact">No people records are loaded in this MVP view yet.</div>
      </section>
    </>
  );
}
