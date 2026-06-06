# PortalPilot

PortalPilot is a generic, data-driven workqueue for government filings. A form is data in `form_definitions` and `form_fields`; the engine reads those rows at runtime, maps profile/document facts to fields, fills what it can, and stops at human-only walls.

## Demo Path

1. Open `/queue`.
2. Click `Run worker` on a not-started form task.
3. The worker fills safe fields on the mirror form and parks the task in `Action Required` when information or human access is needed.
4. Supply the missing info or open the live portal for authentication.
5. Resume and mark the task reviewed/completed.
6. Use `Auto-suggest` or `Research add` to create researched queue items with official-source evidence.

## Architecture

- `apps/web`: Next.js App Router, TypeScript, desktop-focused demo UI.
- `apps/api`: FastAPI backend, generic mapper/agent/executor/portal modules.
- `supabase/migrations`: generic schema.
- `supabase/seed`: demo seed data. This is the only place the demo-specific form data lives.

The mirror portal renders from the same `form_definition` rows the agent reads. The live portal path reaches the real `portal_url`, records the auth/CAPTCHA/login wall, and hands control back to the user.

## Safety Posture

- The agent never enters credentials, solves CAPTCHA, approves MFA, accepts declarations, submits, endorses, or pays.
- Human-only fields are controlled by `form_fields.human_only` plus the backend denylist in the action executor.
- Portal pages and uploaded documents are treated as untrusted.
- Logs exclude secrets, credentials, full identifiers, and raw document text.

## Single-User Hackathon Scope

Supabase Auth and RLS are intentionally deferred for the hackathon demo. Do not add `user_id` or `auth.uid()` policies until this moves beyond single-user demo mode.

Documents are short-lived demo artifacts. The extractor stores structured facts and evidence notes, not full raw document text.

## Commands

```bash
pnpm --filter @portalpilot/web dev
pnpm --filter @portalpilot/web build
pnpm --filter @portalpilot/web lint

cd apps/api
uv run uvicorn app.main:app --reload
uv run pytest
uv run python scripts/smoke_generality.py
```

## Environment

Copy `.env.example` into local env files and fill in values:

- `OPENAI_API_KEY`
- `OPENAI_COMPUTER_USE_MODEL`
- `OPENAI_RESEARCH_MODEL`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_DB_URL`
- `WEB_ORIGIN`
- `NEXT_PUBLIC_API_URL`

Keep `.env` and `.env.local` out of git.
