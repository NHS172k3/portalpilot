"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Attribute,
  DocumentRecord,
  Profile,
  createProfile,
  getProfile,
  listDocuments,
  listProfiles,
  uploadDocument,
  upsertAttribute,
} from "./api";

type LoadState = "loading" | "ready" | "error";

const emptyAttribute: Omit<Attribute, "id"> = {
  key: "",
  label: "",
  value: "",
  sensitivity: "business",
  notes: "",
};

export function Workspace() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [message, setMessage] = useState("");
  const [newProfileName, setNewProfileName] = useState("");
  const [attributeDraft, setAttributeDraft] = useState(emptyAttribute);
  const [isSaving, setIsSaving] = useState(false);

  async function loadProfiles(nextSelectedId?: string) {
    setLoadState("loading");
    try {
      const rows = await listProfiles();
      setProfiles(rows);
      const nextId = nextSelectedId ?? selectedId ?? rows[0]?.id ?? null;
      setSelectedId(nextId);
      setLoadState("ready");
      setMessage("");
    } catch (error) {
      setLoadState("error");
      setMessage(error instanceof Error ? error.message : "Could not load profiles");
    }
  }

  async function loadDetail(profileId: string) {
    try {
      const [nextProfile, nextDocuments] = await Promise.all([
        getProfile(profileId),
        listDocuments(profileId),
      ]);
      setProfile(nextProfile);
      setDocuments(nextDocuments);
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not load profile");
    }
  }

  useEffect(() => {
    void loadProfiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedId) {
      void loadDetail(selectedId);
    } else {
      setProfile(null);
      setDocuments([]);
    }
  }, [selectedId]);

  async function handleCreateProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = newProfileName.trim();
    if (!name) {
      return;
    }
    setIsSaving(true);
    try {
      const created = await createProfile(name);
      setNewProfileName("");
      await loadProfiles(created.id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create profile");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSaveAttribute(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile) {
      return;
    }
    setIsSaving(true);
    try {
      await upsertAttribute(profile.id, {
        ...attributeDraft,
        key: attributeDraft.key.trim(),
        label: attributeDraft.label.trim(),
        value: attributeDraft.value.trim(),
        notes: attributeDraft.notes?.trim() || null,
      });
      setAttributeDraft(emptyAttribute);
      await loadDetail(profile.id);
      await loadProfiles(profile.id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not save attribute");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile) {
      return;
    }
    const input = event.currentTarget.elements.namedItem("document") as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }
    setIsSaving(true);
    try {
      await uploadDocument(profile.id, file);
      input.value = "";
      await loadDetail(profile.id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not upload document");
    } finally {
      setIsSaving(false);
    }
  }

  const factCount = useMemo(
    () => documents.reduce((total, document) => total + document.facts.length, 0),
    [documents],
  );

  return (
    <main>
      <div className="app-shell">
        <header className="topbar">
          <div>
            <p className="eyebrow">PortalPilot</p>
            <h1>Business profile</h1>
          </div>
          <div className="metric-strip" aria-label="Workspace summary">
            <div>
              <span>{profiles.length}</span>
              <small>Profiles</small>
            </div>
            <div>
              <span>{profile?.attributes?.length ?? 0}</span>
              <small>Attributes</small>
            </div>
            <div>
              <span>{factCount}</span>
              <small>Facts</small>
            </div>
          </div>
        </header>

        {message ? <div className="notice error">{message}</div> : null}

        <div className="workspace-grid">
          <aside className="sidebar" aria-label="Profiles">
            <form className="stack-form" onSubmit={handleCreateProfile}>
              <label htmlFor="profile-name">Profile name</label>
              <div className="inline-form">
                <input
                  id="profile-name"
                  value={newProfileName}
                  onChange={(event) => setNewProfileName(event.target.value)}
                  placeholder="New business profile"
                />
                <button type="submit" disabled={isSaving}>Add</button>
              </div>
            </form>

            {loadState === "loading" ? <div className="empty-state">Loading profiles</div> : null}
            {loadState === "error" ? <div className="empty-state">Unable to load profiles</div> : null}
            {loadState === "ready" && profiles.length === 0 ? (
              <div className="empty-state">No profiles yet</div>
            ) : null}

            <div className="profile-list">
              {profiles.map((row) => (
                <button
                  className={row.id === selectedId ? "profile-item active" : "profile-item"}
                  key={row.id}
                  onClick={() => setSelectedId(row.id)}
                  type="button"
                >
                  <strong>{row.name}</strong>
                  <span>{row.attribute_count ?? 0} attributes</span>
                </button>
              ))}
            </div>
          </aside>

          <section className="content-region">
            {profile ? (
              <>
                <section className="section-block">
                  <div className="section-heading">
                    <div>
                      <p className="section-kicker">Reusable facts</p>
                      <h2>{profile.name}</h2>
                    </div>
                  </div>

                  <form className="attribute-form" onSubmit={handleSaveAttribute}>
                    <input
                      aria-label="Attribute key"
                      value={attributeDraft.key}
                      onChange={(event) =>
                        setAttributeDraft((draft) => ({ ...draft, key: event.target.value }))
                      }
                      placeholder="key"
                      required
                    />
                    <input
                      aria-label="Attribute label"
                      value={attributeDraft.label}
                      onChange={(event) =>
                        setAttributeDraft((draft) => ({ ...draft, label: event.target.value }))
                      }
                      placeholder="Label"
                      required
                    />
                    <input
                      aria-label="Attribute value"
                      value={attributeDraft.value}
                      onChange={(event) =>
                        setAttributeDraft((draft) => ({ ...draft, value: event.target.value }))
                      }
                      placeholder="Value"
                      required
                    />
                    <select
                      aria-label="Sensitivity"
                      value={attributeDraft.sensitivity}
                      onChange={(event) =>
                        setAttributeDraft((draft) => ({ ...draft, sensitivity: event.target.value }))
                      }
                    >
                      <option value="public">public</option>
                      <option value="business">business</option>
                      <option value="personal">personal</option>
                      <option value="confidential">confidential</option>
                    </select>
                    <button type="submit" disabled={isSaving}>Save</button>
                  </form>

                  {profile.attributes?.length ? (
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Label</th>
                            <th>Value</th>
                            <th>Sensitivity</th>
                          </tr>
                        </thead>
                        <tbody>
                          {profile.attributes.map((attribute) => (
                            <tr key={attribute.key}>
                              <td>
                                <strong>{attribute.label}</strong>
                                <small>{attribute.key}</small>
                              </td>
                              <td>{attribute.value}</td>
                              <td>
                                <span className="pill">{attribute.sensitivity}</span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="empty-state">No attributes yet</div>
                  )}
                </section>

                <section className="section-block">
                  <div className="section-heading">
                    <div>
                      <p className="section-kicker">Document library</p>
                      <h2>Uploads</h2>
                    </div>
                    <form className="upload-form" onSubmit={handleUpload}>
                      <input name="document" type="file" />
                      <button type="submit" disabled={isSaving}>Upload</button>
                    </form>
                  </div>

                  {documents.length ? (
                    <div className="document-list">
                      {documents.map((document) => (
                        <article className="document-row" key={document.id}>
                          <div>
                            <strong>{document.filename}</strong>
                            <small>{document.mime}</small>
                          </div>
                          {document.facts.length ? (
                            <div className="fact-list">
                              {document.facts.map((fact) => (
                                <div className="fact-row" key={fact.id}>
                                  <span>{fact.key}</span>
                                  <strong>{fact.value}</strong>
                                  <small>{Math.round(fact.confidence * 100)}% confidence</small>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="empty-state compact">No facts extracted</div>
                          )}
                        </article>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state">No documents uploaded</div>
                  )}
                </section>
              </>
            ) : (
              <section className="section-block">
                <div className="empty-state">Select or create a profile</div>
              </section>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
