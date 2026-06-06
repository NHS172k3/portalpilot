"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { FieldRecord, FormDefinition, FormField, getForm, getTask } from "../../api";

type PageState = "not_ready" | "fillable_section" | "ready_for_user_review" | "blocked_or_unknown";

function parseOptions(options: string[] | null): string[] {
  return Array.isArray(options) ? options : [];
}

function fieldControl(field: FormField, value: string | boolean, setValue: (value: string | boolean) => void) {
  const common = {
    id: field.key,
    name: field.key,
    "data-portal-field": field.key,
    "data-portal-label": field.label,
    "data-human-only": String(field.human_only),
    "aria-label": field.label,
    disabled: field.human_only || field.provenance === "retrieved",
  };

  if (field.type === "checkbox") {
    return (
      <label className="check-row">
        <input
          {...common}
          checked={Boolean(value)}
          onChange={(event) => setValue(event.target.checked)}
          type="checkbox"
        />
        <span>{field.label}</span>
      </label>
    );
  }

  if (field.type === "radio") {
    return (
      <div className="option-stack" role="radiogroup" aria-label={field.label}>
        {parseOptions(field.options).map((option) => (
          <label className="check-row" key={option}>
            <input
              {...common}
              checked={value === option}
              onChange={() => setValue(option)}
              type="radio"
              value={option}
            />
            <span>{option}</span>
          </label>
        ))}
      </div>
    );
  }

  if (field.type === "select" || field.type === "multi_select") {
    const selectValue =
      field.type === "multi_select"
        ? Array.isArray(value)
          ? value
          : String(value || "")
            ? [String(value)]
            : []
        : String(value ?? "");

    return (
      <select
        {...common}
        multiple={field.type === "multi_select"}
        onChange={(event) => setValue(event.target.value)}
        value={selectValue}
      >
        <option value="">Select</option>
        {parseOptions(field.options).map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }

  if (field.type === "upload") {
    return <input {...common} type="file" />;
  }

  if (field.type === "button") {
    return (
      <button className="secondary-button" data-portal-action={field.key} disabled={field.human_only} type="button">
        {field.label}
      </button>
    );
  }

  const inputType = field.type === "date" || field.type === "number" ? field.type : "text";
  return (
    <input
      {...common}
      onChange={(event) => setValue(event.target.value)}
      placeholder={field.provenance === "retrieved" ? "Retrieved by portal" : ""}
      type={inputType}
      value={String(value ?? "")}
    />
  );
}

function valuesFromRecords(fields: FormField[], records: FieldRecord[]): Record<string, string | boolean> {
  const fieldByKey = new Map(fields.map((field) => [field.key, field]));
  const nextValues: Record<string, string | boolean> = {};
  for (const record of records) {
    if (!record.proposed_value || !["filled", "needs_review"].includes(record.status)) {
      continue;
    }
    const field = fieldByKey.get(record.field_key);
    if (!field || field.human_only || field.provenance === "retrieved") {
      continue;
    }
    nextValues[record.field_key] =
      field.type === "checkbox" ? ["1", "true", "yes", "checked", "on"].includes(record.proposed_value.toLowerCase()) : normalizeControlValue(field, record.proposed_value);
  }
  return nextValues;
}

function orderedDraftEntries(fields: FormField[], records: FieldRecord[]): [string, string | boolean][] {
  const values = valuesFromRecords(fields, records);
  return fields.flatMap((field) => (field.key in values ? [[field.key, values[field.key]] as [string, string | boolean]] : []));
}

function normalizeControlValue(field: FormField, value: string): string {
  if (field.type !== "date") {
    return value;
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return value;
  }
  const match = value.match(/^(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})$/);
  if (!match) {
    return value;
  }
  const months: Record<string, string> = {
    jan: "01",
    january: "01",
    feb: "02",
    february: "02",
    mar: "03",
    march: "03",
    apr: "04",
    april: "04",
    may: "05",
    jun: "06",
    june: "06",
    jul: "07",
    july: "07",
    aug: "08",
    august: "08",
    sep: "09",
    september: "09",
    oct: "10",
    october: "10",
    nov: "11",
    november: "11",
    dec: "12",
    december: "12",
  };
  const month = months[match[2].toLowerCase()];
  return month ? `${match[3]}-${month}-${match[1].padStart(2, "0")}` : value;
}

export function MirrorForm({ formId, replay, taskId }: { formId: string; replay?: boolean; taskId?: string }) {
  const [form, setForm] = useState<FormDefinition | null>(null);
  const [values, setValues] = useState<Record<string, string | boolean>>({});
  const [animatedKeys, setAnimatedKeys] = useState<string[]>([]);
  const [pageState, setPageState] = useState<PageState>("not_ready");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    let cancelled = false;

    async function loadMirror() {
      try {
        const nextForm = await getForm(formId);
        if (cancelled) return;
        setForm(nextForm);
        setAnimatedKeys([]);
        if (taskId) {
          const task = await getTask(taskId);
          if (cancelled) return;
          const entries = orderedDraftEntries(nextForm.fields, task.field_records);
          if (replay && entries.length) {
            setValues({});
            setMessage("Replaying agent fill from persisted field records");
            entries.forEach(([fieldKey, value], index) => {
              timers.push(
                setTimeout(() => {
                  setValues((current) => ({ ...current, [fieldKey]: value }));
                  setAnimatedKeys((current) => [...current.filter((key) => key !== fieldKey), fieldKey]);
                }, 350 + index * 260),
              );
            });
          } else {
            const nextValues = Object.fromEntries(entries);
            setValues(nextValues);
            setAnimatedKeys(Object.keys(nextValues));
            setMessage(Object.keys(nextValues).length ? "Loaded agent-filled draft values from the selected task" : "No agent-filled values found for this task");
          }
        } else {
          setValues({});
          setAnimatedKeys([]);
          setMessage("");
        }
        setPageState("fillable_section");
      } catch (error) {
        if (cancelled) return;
        setPageState("blocked_or_unknown");
        setMessage(error instanceof Error ? error.message : "Could not load form");
      }
    }

    void loadMirror();
    return () => {
      cancelled = true;
      timers.forEach(clearTimeout);
    };
  }, [formId, replay, taskId]);

  const sections = useMemo(() => {
    const grouped = new Map<string, FormField[]>();
    for (const field of form?.fields ?? []) {
      grouped.set(field.section, [...(grouped.get(field.section) ?? []), field]);
    }
    return Array.from(grouped.entries());
  }, [form]);

  function updateValue(fieldKey: string, value: string | boolean) {
    setValues((current) => ({ ...current, [fieldKey]: value }));
  }

  function handleSaveDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPageState("ready_for_user_review");
    setMessage("Draft saved");
  }

  return (
    <main data-portal-backend="mirror" data-portal-state={pageState}>
      <div className="app-shell">
        <header className="topbar mirror-topbar">
          <div>
            <p className="eyebrow">Mirror portal</p>
            <h1>{form?.name ?? "Loading form"}</h1>
            {form ? (
              <p className="mirror-meta">
                {form.jurisdiction} · {form.agency} · {form.fields.length} fields
                {taskId ? ` · draft from ${taskId}` : ""}
              </p>
            ) : null}
          </div>
          <div className="metric-strip" aria-label="Mirror summary">
            <div>
              <span>{sections.length}</span>
              <small>Sections</small>
            </div>
            <div>
              <span>{Object.keys(values).length}</span>
              <small>{replay ? "Filled live" : "Filled"}</small>
            </div>
          </div>
        </header>

        {message ? <div className="notice">{message}</div> : null}
        {pageState === "blocked_or_unknown" ? <div className="notice error">Unable to load mirror form</div> : null}

        {form ? (
          <form className="mirror-form" data-portal-form-id={form.id} onSubmit={handleSaveDraft}>
            {sections.map(([section, fields]) => (
              <section className="section-block mirror-section" data-portal-section={section} key={section}>
                <div className="section-heading">
                  <div>
                    <p className="section-kicker">Section</p>
                    <h2>{section}</h2>
                  </div>
                </div>
                <div className="field-grid">
                  {fields.map((field) => (
                    <div
                      className={[
                        "field-row",
                        field.human_only ? "human-only" : "",
                        replay && animatedKeys.includes(field.key) ? "replay-filled" : "",
                      ]
                        .filter(Boolean)
                        .join(" ")}
                      data-portal-field-row={field.key}
                      key={field.key}
                    >
                      {field.type !== "checkbox" && field.type !== "button" ? (
                        <label htmlFor={field.key}>
                          {field.label}
                          {field.required ? <span aria-label="required"> *</span> : null}
                        </label>
                      ) : null}
                      {fieldControl(field, values[field.key] ?? "", (value) => updateValue(field.key, value))}
                      <div className="field-meta">
                        <span>{field.type}</span>
                        <span>{field.sensitivity}</span>
                        {field.human_only ? <span>human-only</span> : null}
                        {field.provenance === "retrieved" ? <span>retrieved</span> : null}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            ))}

            <div className="mirror-actions">
              <button data-portal-action="save_draft" type="submit">
                Save draft
              </button>
            </div>
          </form>
        ) : (
          <section className="section-block">
            <div className="empty-state">Loading form</div>
          </section>
        )}
      </div>
    </main>
  );
}
