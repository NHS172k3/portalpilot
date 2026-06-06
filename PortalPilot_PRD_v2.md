# PortalPilot — Product Requirements Document (v2)

## 1. Summary

PortalPilot is an **AI-native dashboard for businesses** that turns government and institutional form-filing from a manual chore into a managed, mostly-autonomous background process.

A business sets up a **company profile** once — structured details plus an uploaded library of documents — and PortalPilot's agents use it as a shared knowledge base. From there, agents work in the background to **discover relevant filings, draft and fill them autonomously, and only pull the human in when they genuinely need something**: a missing piece of information, or a human-only step the agent is not permitted to take (login, CAPTCHA, legal sign-off, payment, final submission).

The product surface is a dashboard, not a wizard:

- A **company profile** with structured fields and a document library.
- A **filings board** organized by status: Not Started, In Progress, Needs You, Completed.
- An **Action Center** — a single inbox of everything the agents need from the human, across all filings.
- A live **activity feed** showing what each agent is doing, with per-field confidence and source attribution.

The core shift from v1: PortalPilot is no longer a single-session "open the portal and click *Agent take over now*" tool. It is a persistent dashboard where **multiple background agents run continuously across many filings**, and the human's job is reduced to answering targeted requests and clearing the human-only walls.

The original safety boundary is preserved exactly: **the agent never logs in, never solves CAPTCHA, never approves MFA, never accepts legal declarations, never endorses, never pays, and never submits.** Those are not failures — they are first-class, structured handoffs surfaced in the Action Center.

**General-purpose by design.** PortalPilot is not built around any single form, portal, or jurisdiction. The product and its UI are **use-case-agnostic**: the dashboard, board, profile, Action Center, and review surfaces are generic and driven by each filing's own requirements as *data*, never by domain-specific screens hard-coded into the interface. A user landing on PortalPilot should see a general filing dashboard, not a registration tool.

**Demo scenario.** For demos we showcase **startup registration** (e.g. registering a Singapore company via BizFile/ACRA). This is one concrete instance flowing through the generic surfaces — chosen because it exercises discovery, document extraction, autonomous fill, missing-info requests, and human-only walls in a single story. Nothing about the demo scenario should leak into the product's visual identity or navigation.

---

## 2. Problem

Businesses interact with government and institutional portals constantly, not once: company registration, annual returns, tax filings, licence renewals, grant applications, employment and immigration filings, regulatory disclosures, and more. The friction is chronic, not a one-time event:

- **Discovery** — businesses don't reliably know which filings apply to them right now, or which are coming due.
- **Data gathering** — every form needs fields scattered across documents, prior filings, spreadsheets, emails, and people's heads.
- **Manual transcription** — someone copies the same information into yet another portal, carefully, because the forms are legally sensitive.
- **Tracking** — there is no single place that shows what's done, what's in progress, and what's stuck waiting on a human.

Existing tools either (a) do nothing autonomously and just store documents, or (b) automate blindly with brittle RPA that breaks on portal changes and can't be trusted near legal boundaries.

PortalPilot reduces the burden by:

- maintaining a persistent, reusable company profile and document library;
- continuously discovering which filings apply and surfacing them on a board;
- letting agents fill forms autonomously in the background using the profile, documents, and live regulatory research;
- attaching field-level confidence and sources to everything the agent does;
- pausing precisely when it needs human input or hits a human-only wall — and asking clearly;
- and never crossing the legal/submission boundary, keeping the human accountable for what is filed.

---

## 3. Product Principles

1. **Background-first, not session-first.** Agents are persistent workers. The default state is "agents are working"; the human is interrupted only when necessary.
2. **Two pause triggers, both explicit.** An agent pauses and asks the human only when (a) it is missing information it cannot infer with sufficient confidence, or (b) it reaches a human-only wall (login, CAPTCHA, MFA, legal declaration, endorsement, payment, final submit). Everything in between, it does on its own.
3. **The human boundary is permanent.** The agent never enters credentials, never solves CAPTCHA, never signs declarations, never pays, never submits. This is enforced both in agent instructions and in a backend action executor, regardless of what any model output requests.
4. **Profile and documents are the shared brain.** Agents draw from one reusable knowledge base so the business never re-enters the same fact twice.
5. **Agents both discover and execute.** Agents propose relevant filings *and* the business can add its own. The board reflects both.
6. **Everything is attributed.** Every value an agent proposes carries a confidence score, a source (profile / document / context / official source / inference), and a sensitivity label. Nothing is a black box.
7. **Untrusted input is treated as untrusted.** Portal pages and uploaded documents may contain adversarial instructions; agents never follow instructions embedded in them.
8. **Use-case-agnostic and config-driven.** No surface is bespoke to one domain. Filing-specific structure (which fields exist, which documents are needed, which steps are human-only) is loaded as configuration/data per filing; the UI renders it generically. Adding a new filing type requires data and prompts, not new screens.
9. **Not professional advice.** PortalPilot prepares filings; it is not legal, tax, accounting, or corporate-secretarial advice, and says so where it matters.

---

## 4. Users

- **Founder / small business owner** — wants filings handled with minimal involvement; touches the product mainly through the Action Center.
- **Operations / compliance lead** — manages many filings across deadlines; lives in the filings board and activity feed.
- **Finance / admin** — supplies documents and answers data requests; cares about accuracy and audit trail.
- **External advisor (future)** — accountant or corporate secretary invited to review or clear specific requests.

Primary day-one persona: a non-technical business representative who wants to delegate filing work but stay in control of anything legally binding.

---

## 5. Information Architecture & Navigation

The dashboard's primary navigation is optimized around **the human's job in a background-agent system**: answer what's asked, watch progress, manage the knowledge base. It is **identical across all use cases** — the same six surfaces serve startup registration, tax filings, licence renewals, or any other domain. Nothing in the chrome names a specific form or jurisdiction; domain specifics appear only as content inside these generic surfaces. The optimization rationale follows the tab list.

### 5.1 Primary navigation

1. **Home (Overview)** — the command center. At-a-glance: count of items needing the human, filings in progress, upcoming deadlines, and a recent activity strip. Answers "what should I do right now, and what are my agents doing?"
2. **Filings** — the board. Status columns: **Not Started · In Progress · Needs You · Completed** (plus a Blocked/Archived filter). Each card shows progress, status, last agent action, and what's pending. Opening a filing reveals its detail view (fields, pre-fill preview, per-field confidence, activity, and the requests scoped to it).
3. **Action Center** — the single inbox of everything agents need from the human, across all filings. This is the operationalized version of "information the agent needs." Items are typed (data request, human-wall handoff, confirmation, warning) and answered inline; answering resumes the agent automatically.
4. **Company Profile** — the shared brain, in three parts: **Details** (structured company data), **Document Library** (uploads → extracted facts), and **People** (position holders, shareholders, contacts).
5. **Activity** — chronological, filterable feed of agent runs and events: discoveries, fills, skips, pauses, blocked actions, completions. Doubles as the audit trail.
6. **Settings** — autonomy policy, notifications, connectors/portals, data retention, and team/advisor access (future).

### 5.2 Why this structure (optimization notes)

- **"Needs You" is a status, not just an inbox.** Your original three statuses (Not Started / In Progress / Completed) don't capture the defining state of a background-agent system: *the agent did all it could and is now waiting on a human*. Promoting this to a first-class column on the board (and mirroring it in the Action Center) makes the human's queue unmissable.
- **Action Center is global, not per-form.** Requests span many filings simultaneously. A single cross-filing inbox means the human answers a batch of questions in one sitting instead of hunting through forms. The same items also appear inside each filing's detail view for context.
- **Home is a command center, not a landing page.** In an autonomous product the home screen's job is triage: surface what needs attention and prove the agents are working. This is the AI-native default.
- **Profile is split into Details / Documents / People.** Treating the document library and people (position holders, shareholders) as first-class — not buried sub-fields — matches how forms actually consume data and keeps the knowledge base maintainable.
- **Activity is both feed and audit.** One timeline serves the AI-native "watch your agents work" experience and the compliance need for an audit log, avoiding a redundant surface.

---

## 6. Core Concepts (Domain Model)

- **Company Profile** — stable business data reused across all filings.
- **Document** — an uploaded file (short-lived by default) processed into extracted facts.
- **Extracted Fact** — a structured value derived from a document or context, with source, confidence, and sensitivity.
- **Filing** — one government/institutional form or workflow tracked on the board, with a lifecycle status.
- **Agent Run** — one background execution attempt against a filing (research, fill, or resume).
- **Agent Request** — a structured ask surfaced to the human in the Action Center (data request, human-wall handoff, confirmation, or warning).
- **Field Confidence Record** — per-field explanation of what the agent did: value, source(s), confidence, status, sensitivity, reason.
- **Activity Event** — one meaningful, logged occurrence in the workflow.
- **Autonomy Policy** — user-configurable rules for how far agents may act before pausing.
- **Regulatory Recommendation** — an agent-researched suggestion that a particular filing applies, with evidence.

---

## 7. Functional Requirements

### 7.1 Home / Overview

- Shows a prioritized **"Needs You"** summary: count and preview of open Action Center items.
- Shows **In Progress** filings with live progress and the agent's current step.
- Shows **upcoming deadlines** and overdue items.
- Shows a **recent activity** strip (latest agent events across all filings).
- Provides quick entry points: add a filing, upload a document, open the Action Center.

### 7.2 Company Profile

**Details.** A small **generic core** of reusable company data plus an **extensible field set**. The generic core includes: legal/trading name, registration ID if one exists, address, industry/activity summary, primary contact email and phone, and reusable filing notes. Beyond the core, fields are **defined as data, not hard-coded UI** — a filing declares the fields it needs, and the profile renders and stores them generically. (For the startup-registration demo, that data set adds fields like financial year end, intended entity type, and name-application reference; these appear through the same generic field rendering, not a bespoke registration form.)

**Document Library.** The business uploads internal/setup documents (PDF, Word, plain text, spreadsheets, email exports, images where feasible). Each document is processed into **extracted facts**, each carrying: value; source type (`business_profile`, `filing_context`, `uploaded_document`, `official_source`, `agent_inference`); confidence (0–1); optional evidence note; sensitivity label (`public`, `business`, `personal`, `confidential`). Documents are **short-lived by default** and not retained beyond what's needed, configurable in Settings.

**People.** Position holders, shareholders, directors, and contacts, with the attributes filings commonly require — stored once, reused everywhere. Sensitive identifiers are handled as `personal`/`confidential` and never auto-filled without explicit human action.

### 7.3 Filings Board

- Filings are displayed as cards in status columns: **Not Started, In Progress, Needs You, Completed** (with Blocked and Archived available via filter).
- Each card shows: filing name, jurisdiction/agency, status, progress indicator, last agent action + timestamp, number of open requests, and any deadline.
- Filings are created two ways: **agent-discovered** (see 7.6) and **user-added** (search a catalog or describe the need in natural language; the agent then researches and configures it).
- **Filing detail view** contains: overview + recommendation evidence; the pre-fill preview with per-field confidence (7.8); the requests scoped to this filing; and this filing's slice of the activity feed.

### 7.4 Action Center (Information the Agent Needs)

The Action Center is the unified, cross-filing inbox of **Agent Requests**. Request types:

- **Data request** — the agent is missing a fact it can't infer with sufficient confidence (e.g. "What is the financial year end?"). The human answers inline; the answer is optionally saved back to the profile.
- **Human-wall handoff** — the agent reached a human-only step and needs the human to perform it (e.g. "Log in and complete authentication/MFA," "Solve the CAPTCHA," "Review and submit"). Includes a deep link to the exact portal location.
- **Confirmation** — the agent has a proposed value or action that needs sign-off before proceeding (e.g. choosing among candidate options for a field).
- **Warning / blocker** — a condition the agent can't resolve (e.g. an intermediary or third party may be required, or the activity needs a separate approval/licence). Classifies the filing as `blocked` or `needs_professional_assistance` rather than pretending to proceed.

(In the startup-registration demo these surface as, e.g., "Log in to BizFile and complete Singpass/MFA," confirming an SSIC activity code, or flagging that a Corporate Service Provider may be required — but the request *types* and UI are generic.)

Behavior:

- Each item shows the question, the filing it belongs to, why it's being asked, and any agent-proposed answer with its confidence and source.
- Answering or clearing an item **automatically resumes** the relevant agent run.
- Items are batchable: the human can clear several in one session.
- Each item mirrors into its filing's detail view for context.

### 7.5 Background Agent Engine

Agents run **continuously in the background**, not on manual invocation. The engine is built on the **OpenAI Responses API**, orchestrated with the **OpenAI Agents SDK** (whose human-handoff and lifecycle-hook primitives back PortalPilot's pause/resume request model). For each filing, an agent run:

1. Loads available knowledge: profile, document facts, filing context, and prior official-source research.
2. Advances the filing as far as it can autonomously.
3. Pauses on either trigger — **missing information** or a **human-only wall** — and emits a typed Agent Request.
4. Resumes automatically once the corresponding request is answered/cleared.
5. Logs every step as Activity Events with field-level confidence.

**Autonomy policy (Settings, 7.12)** controls how far agents go before pausing — e.g. auto-fill high-confidence business fields vs. confirm everything; auto-discover filings vs. suggest only. The two hard pause triggers always apply regardless of policy.

### 7.6 Regulatory Discovery & Recommendations

- Agents run agentic **live-web research over official sources using OpenAI web search** to determine which filings apply to the business and surface them as **Not Started** cards (agent-discovered filings).
- Each recommendation includes: recommended form/workflow; reason; prerequisites; fee/payment expectation; deadline/timeline; source link(s) and brief summary; warnings/blockers; and a recommendation confidence.
- Research is restricted to official/authoritative sources; results are shown with links and confidence so the human can trust without being overwhelmed.
- The discovery and recommendation logic is domain-agnostic. *Demo scenario:* when the context indicates registering a Singapore company after name approval, the expected recommendation is the BizFile "Register new business entity" workflow — produced by the same generic discovery flow that would surface a tax filing or licence renewal.

### 7.7 Document Upload & Extraction

- Upload from the Document Library or directly within a filing.
- Extraction uses **OpenAI document extraction** to produce structured candidate facts (schema per 7.2).
- Documents are treated as **untrusted input**; embedded instructions are never followed.
- Short-lived by default; retention configurable.

### 7.8 Pre-Fill, Per-Field Confidence & Review

Before and as an agent fills, the filing detail view shows a **pre-fill map** per field: portal section, field label, proposed value, source(s), confidence, sensitivity, status, and reason.

**Field Confidence Record** statuses: `filled`, `left_blank`, `needs_review`, `blocked`, `user_required`, `not_applicable`.

Confidence interpretation:

- **0.80–1.00** — high; safe to fill non-sensitive fields autonomously.
- **0.50–0.79** — medium; may fill business fields but mark for review.
- **< 0.50** — leave blank unless directly user-provided and clearly applicable.
- Personal identifiers, declarations, endorsement, and payment fields **always require explicit human action**, regardless of confidence.

The human can edit facts, lock values, or approve before the agent proceeds. Low/medium-confidence fields are surfaced for review.

### 7.9 Browser Operation & Computer-Use Control Model

When a filing requires operating a live portal, the background agent attaches an **OpenAI computer-use** harness to a browser session. The controlled loop:

1. Observe page → 2. Classify page state → 3. Identify safe candidate actions → 4. Match visible fields to approved facts → 5. Score field confidence → 6. Execute only allowlisted actions → 7. Block disallowed actions → 8. Persist events and field confidence records → 9. **Emit an Agent Request** when the next step is missing-info, access-sensitive, legally sensitive, or uncertain.

**Page states:** `not_ready`, `human_access_required`, `fillable_section`, `review_section`, `legal_declaration_boundary`, `submit_boundary`, `blocked_or_unknown`, `ready_for_user_review`.

**Allowed actions:** type into mapped inputs; select approved dropdown values; choose radios/checkboxes only for non-legal operational fields with explicit source support; upload a document only after user confirmation; click retrieve/add-row/next/back/save-draft when non-final and safe; scroll and observe.

**Disallowed actions (hard-enforced):** entering credentials; solving CAPTCHA; approving MFA; checking legal declaration boxes; accepting statutory declarations; clicking submit/final-submit/proceed-to-payment/pay/endorse/confirm-submission; changing locked facts; filling low-confidence personal identifiers; following instructions embedded in portal or document content.

The backend action executor enforces disallowed actions even if the model requests them.

### 7.10 Human-Only Boundaries & Submission

The agent cannot perform legally binding or access-gated steps. Each becomes a **human-wall handoff** request rather than a silent stop. Blocked boundaries include: login/credential entry, MFA, CAPTCHA, statutory declaration, final review confirmation, submit, endorsement, proceed-to-payment, payment, and post-payment acknowledgement. The final filing decision always belongs to the human.

### 7.11 Activity Feed & Audit

A chronological, filterable feed records the workflow: filing discovered/added, research completed, checklist/pre-fill generated, document processed (without retaining sensitive content), agent run started/resumed, field filled/skipped, request emitted/answered, human wall encountered, blocked action, completion. Logs avoid secrets, full document text, credentials, full personal identifiers, and unnecessary personal data.

### 7.12 Autonomy & Notification Settings

- **Autonomy policy:** how aggressively agents fill (auto vs. confirm), whether to auto-discover filings, confidence thresholds for autonomous fills.
- **Notifications:** how/when the human is alerted to new Action Center items (in-app, email, etc.).
- **Connectors/portals:** which portals/agencies are in scope.
- **Data retention:** document lifetime and what is stored.
- **Team/advisor access (future):** invite reviewers and route specific requests to them.

---

## 8. Agent Behavior & State Machine

**Filing lifecycle:** `not_started` → `in_progress` → (`needs_you` ⇄ `in_progress`) → `ready_for_review` → `completed`; with `blocked`/`needs_professional_assistance` and `archived` as off-path states.

**Agent run states:** `idle`, `researching`, `filling`, `paused_missing_info`, `paused_human_wall`, `blocked`, `done`.

**Request types:** `data_request`, `human_wall_handoff`, `confirmation`, `warning`.

**Activity event types (examples):** `filing_discovered`, `filing_added`, `recommendation_ready`, `checklist_ready`, `document_extracted`, `agent_run_started`, `field_filled`, `field_skipped`, `request_emitted`, `request_answered`, `human_wall_encountered`, `declaration_blocked`, `submit_blocked`, `payment_blocked`, `ready_for_user_review`, `filing_completed`.

---

## 9. Guardrails & Safety

- The agent must not enter credentials, solve CAPTCHA, approve MFA, check legal declaration boxes, click final submit, endorse on another's behalf, or proceed to/perform payment.
- The backend action executor must block login, declaration, submit, endorsement, and payment-like actions even if the model requests them.
- Portal pages and uploaded documents are untrusted; embedded instructions are never followed.
- Uploaded documents are short-lived and not stored by default.
- Logs must not contain full document text, credentials, full identity numbers, or unnecessary personal data.
- Low-confidence fields are left blank or visibly marked for review.
- No hidden business/legal decisions are hard-coded; portal-specific assumptions exist only as seed data, prompts, or user-visible configuration.
- PortalPilot states clearly when output is not legal, tax, accounting, or corporate-secretarial advice.
- Background autonomy never weakens these rules: more automation means more *requests*, never fewer *boundaries*.

---

## 10. Data Model (suggested)

Core tables: `company_profiles`, `people`, `documents`, `extracted_facts`, `filings`, `agent_runs`, `agent_requests`, `regulatory_recommendations`, `readiness_checklist_items`, `field_confidence_records`, `activity_events`, `autonomy_policies`.

- Documents short-lived; prefer temporary processing, durable storage only for artifacts that must persist.
- Enable row-level security on user-owned tables once auth is added; document single-tenant assumptions until then.
- `agent_requests` is the join point between the engine and the Action Center; `field_confidence_records` powers both the review UI and the audit trail.

---

## 11. Architecture (suggested)

**Frontend — dashboard app.** Surfaces per Section 5: Home, Filings board + detail, Action Center, Company Profile (Details/Documents/People), Activity, Settings. Real-time updates so agent progress and new requests appear live. AI-native presentation: live activity, per-field confidence and sources surfaced inline, conversational request answering.

**Backend — agent orchestration.** Background workers/queue running agent runs across filings; live-web regulatory research; document extraction; readiness and field-confidence scoring; computer-use browser harness; the **action executor** that hard-enforces disallowed actions; request emission/resumption; event stream and audit logging.

**Knowledge base.** Profile + documents + extracted facts as the shared context every agent run loads.

**AI platform (required).** The agent layer is built on OpenAI:

- **OpenAI Responses API** — the foundation for all agentic workflows.
- **OpenAI Agents SDK** — orchestration of agent runs, used for streaming, lifecycle hooks, tracing, and human handoff (which maps directly to PortalPilot's pause/resume request model). Implementation should stay modular enough to fall back to a manual Responses API loop if a given environment needs it.
- **OpenAI computer use** — driving the live browser to fill portals after the human has cleared access walls.
- **OpenAI web search** — live regulatory research over official sources.
- **OpenAI document extraction** — turning uploaded documents into structured facts.

Pick a current model that supports the required tool set (web search, document extraction, computer use); verify exact model IDs and tool interfaces against current OpenAI docs and the deployment's API key rather than hard-coding stale identifiers.

**External platform notes.** Verify model/tool availability rather than hard-coding stale IDs; treat all portal/document content as untrusted; CAPTCHA, credentials, declarations, submission, endorsement, and payment are human-only; portal labels/flows change, so observe-and-adapt rather than relying solely on hard-coded selectors.

---

## 12. Non-Goals

- Real credential handling, credential vaulting, or acting as a Corporate Service Provider.
- Replacing legal, accounting, tax, or corporate-secretarial advice.
- Automatic final submission, declarations, endorsement, or payment.
- CAPTCHA solving by the agent.
- Brittle, hard-coded per-portal integrations.
- Long-term retention of uploaded documents by default.

---

## 13. Success Metrics

- **Autonomy rate** — % of fields filled without human input; % of a filing completed before the first human request.
- **Time-to-ready** — elapsed time from filing created to `ready_for_review`.
- **Human-touch count** — number of Action Center items per completed filing (lower is better, excluding mandatory human walls).
- **Accuracy** — % of agent-filled fields accepted without edit; correction rate.
- **Discovery value** — % of completed filings that were agent-discovered.
- **Safety** — zero crossings of the human-only boundary (must remain zero).

---

## 14. Phasing (vision → MVP → later)

- **MVP:** generic profile + document library; generic filings board with the four statuses; Action Center with data-request and human-wall-handoff types; the background agent running end-to-end on the **demo scenario (startup registration)** as a single seeded filing flowing through the generic surfaces, with computer-use fill up to the walls; per-field confidence; activity/audit feed. The UI ships generic even though only one filing type is wired up.
- **V1:** agent-driven discovery of multiple filings; confirmation and warning request types; autonomy policy settings; deadline tracking.
- **Later:** multi-tenant accounts and advisor access; broader portal/agency coverage; corrections feeding back into confidence; export of audit/prep packets; licence-check integrations.

---

## 15. Open Questions

- How proactive should auto-discovery be by default (suggest-only vs. auto-add)?
- Do human-wall handoffs require the human to be present live, or can the agent prepare a draft and resume later from a saved state?
- What's the right retention default for documents that recur across periodic filings (e.g. annual returns)?
- How are recurring/periodic filings modeled — as new filings each cycle, or as a renewing filing object?

---

## 16. One-Line Pitch

PortalPilot is the AI-native dashboard where background agents discover, prepare, and fill your business's government filings on their own — pausing only to ask for what they're missing or to hand you the steps a human must take — so the work happens for you while the final, binding decisions stay in your hands.
