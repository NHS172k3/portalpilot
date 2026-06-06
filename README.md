# PortalPilot

PortalPilot is an AI-native filing dashboard for businesses. It keeps a reusable company profile, tracks filings across a board, lets background agents research and prepare filings, and routes missing information or human-only steps into a first-class Action Center.

The product is intentionally a dashboard, not a wizard or landing page. Demo data may use startup registration as a scenario, but the navigation and data model stay generic for many filing types, agencies, and jurisdictions.

## What It Does

- Shows a Home overview for urgent human actions, in-progress filings, deadlines, and recent agent activity.
- Tracks filings in a board with `Not Started`, `In Progress`, `Needs You`, and `Completed` states.
- Centralizes missing information, confirmations, warnings, and human-only handoffs in the Action Center.
- Maintains a Company Profile with reusable business details, people, uploaded documents, and extracted facts.
- Stores agent-produced values with confidence, source attribution, status, and sensitivity.
- Uses strict guardrails so agents prepare filings without crossing legal, authentication, payment, endorsement, or final submission boundaries.

## Tech Stack

| Area | Tech |
| --- | --- |
| Monorepo | pnpm workspace, `pnpm@9.15.4` |
| Frontend framework | Next.js `15.1.6` App Router |
| Frontend language | TypeScript `5.7`, React `19` |
| UI | Custom dashboard components with `lucide-react` icons |
| Backend framework | FastAPI with Uvicorn |
| Backend language | Python `3.12` |
| Python package/runtime tooling | `uv` |
| API data validation | Pydantic `2`, `pydantic-settings` |
| AI platform | OpenAI API |
| Agent runtime | OpenAI Responses API, OpenAI Agents SDK |
| Browser automation | Playwright plus OpenAI computer-use model flow |
| Database | Supabase Postgres |
| Database security | Versioned SQL migrations, Row Level Security policies |
| Storage/auth target | Supabase Storage and Auth-ready schema |
| Frontend deployment | Vercel |
| Backend deployment | Railway |
| Tests and checks | ESLint, Next build, pytest, pytest-asyncio, httpx |

## Architecture

| Layer | Location | Responsibility |
| --- | --- | --- |
| Web app | `apps/web` | Dashboard UI, filings board, Action Center, profile, activity, settings |
| API | `apps/api` | FastAPI routes, orchestration, guardrails, persistence adapter |
| AI orchestration | `apps/api/app` | Filing research, document extraction, agent requests, guarded computer-use sessions |
| Database | `supabase` | Tables, RLS policies, migrations, persistence schema |
| Evidence | `DEMO_EVIDENCE.md` | Checks run, routes verified, blockers, known risks |

## Repository Layout

```text
apps/
  api/        FastAPI backend, agent orchestration, guardrails, tests
  web/        Next.js dashboard UI
supabase/
  migrations/ Versioned Postgres schema and RLS migrations
PortalPilot_PRD_v2.md
DEMO_EVIDENCE.md
```

## Prerequisites

- Node.js with `pnpm`
- Python 3.12
- `uv`
- Supabase CLI, if applying migrations locally or to a hosted project
- OpenAI API key, if running live agent behavior

## Environment

Copy `.env.example` values into the app-specific local env files:

```bash
# apps/web/.env.local - browser-safe values only
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000

# apps/api/.env - server-only values
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
COMPUTER_USE_MODEL=computer-use-preview
COMPUTER_USE_MAX_STEPS=4
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
WEB_ORIGIN=http://localhost:3000
WEB_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001
PORT=8000
```

Do not expose `OPENAI_API_KEY` or `SUPABASE_SERVICE_ROLE_KEY` to the browser. The frontend should only receive `NEXT_PUBLIC_*` values.

The API can run without OpenAI or Supabase configured. In that mode it uses conservative fallback behavior and/or a process-local demo store. Check `/health` to see the active mode and missing environment values.

## Install

From the repo root:

```bash
pnpm install
```

From `apps/api`, install Python dependencies through uv when first running backend commands:

```bash
cd apps/api
uv sync
```

## Local Development

Run the API:

```bash
cd apps/api
uv run uvicorn app.main:app --reload
```

Run the web app from the repo root:

```bash
pnpm dev
```

Open the dashboard at:

```text
http://localhost:3000
```

Useful routes:

- `/` - Home overview
- `/filings` - Filings board
- `/filings/[id]` - Filing detail and pre-fill review
- `/actions` - Action Center
- `/profile` - Company Profile
- `/activity` - Activity feed
- `/settings` - Autonomy and product settings

If Next.js reports a stale `.next` chunk error, clear the cache and restart:

```bash
pnpm clean:web
pnpm dev
```

or:

```bash
pnpm dev:clean
```

## API

Key endpoints:

- `GET /health` - environment, persistence, CORS, and agent diagnostics
- `GET /dashboard` - dashboard snapshot
- `GET /profile` and `PUT /profile` - company profile
- `POST /documents/extract` - document fact extraction
- `POST /filings/describe` - create a researched filing from a natural-language description
- `GET /filings/{filing_id}` - filing detail
- `POST /agent-requests/{request_id}/answer` - answer an Action Center item
- `POST /filings/{filing_id}/computer-use` - run guarded computer-use preparation
- `POST /filings/{filing_id}/computer-use/access-session` - start a user-handoff access session
- `POST /filings/{filing_id}/computer-use/access-session/{session_id}/resume` - resume after human-cleared access
- `DELETE /filings/{filing_id}/computer-use/access-session/{session_id}` - close an access session

## Supabase

Migrations live in `supabase/migrations`.

Apply local or linked migrations with:

```bash
supabase db reset
supabase db push
```

Generate local TypeScript database types when needed:

```bash
supabase gen types typescript --local > apps/web/lib/db.types.ts
```

The schema includes company profiles, people, documents, extracted facts, filings, agent runs, agent requests, regulatory recommendations, readiness checklist items, field confidence records, activity events, and autonomy policies. RLS policies are scoped around `auth.uid()` for user-owned rows.

## Safety Boundaries

PortalPilot prepares filings; it is not legal, tax, accounting, or corporate-secretarial advice.

Agents must never:

- Enter credentials
- Solve CAPTCHA or MFA
- Accept declarations
- Endorse or sign
- Submit final filings
- Proceed to payment or pay
- Follow instructions embedded inside uploaded documents or portal pages

When the agent reaches one of those boundaries, it should emit a structured Action Center handoff instead of hiding the failure or acting autonomously.

## Verification

Run the smallest relevant checks before shipping changes:

```bash
pnpm lint
pnpm build

cd apps/api
uv run pytest
```

For user-facing UI changes, verify desktop and mobile routes in Browser. Current demo evidence and known risks are tracked in `DEMO_EVIDENCE.md`.

## Deployment Notes

Frontend:

- Deploy `apps/web` to Vercel.
- Set `NEXT_PUBLIC_API_URL` to the Railway API URL.
- Set public Supabase values as `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.

Backend:

- Deploy `apps/api` to Railway.
- Use a start command equivalent to:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

- Keep `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and CORS origins server-side.

Supabase:

- Link the project and push migrations.
- Add local, preview, and production callback URLs if Supabase Auth is enabled.

## Project References

- `PortalPilot_PRD_v2.md` is the source of truth for product, UX, agent, data-model, and safety requirements.
- `DEMO_EVIDENCE.md` records checks run, routes verified, current blockers, and demo risks.
- `AGENTS.md` records Codex workflow and project-specific operating rules.
