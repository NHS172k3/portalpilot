# Project Instructions

Copy this file to your hackathon repo root before running Codex.

Project: AI-native hackathon app — Next.js + FastAPI + Supabase + OpenAI

## Monorepo Layout

```
apps/
  web/       # Next.js (App Router, TypeScript) → deploy to Vercel
  api/       # FastAPI (Python 3.12, uv) → deploy to Railway
supabase/    # migrations, seed, RLS, Storage
.env.example # variable names only — never commit values
```

## Stack

| Layer     | Technology                                     | Deploy   |
|-----------|------------------------------------------------|----------|
| Frontend  | Next.js (App Router, TS), pnpm                 | Vercel   |
| Backend   | FastAPI, Python 3.12, uv                       | Railway  |
| AI        | OpenAI Responses API + Agents SDK              | —        |
| DB        | Supabase Postgres (migrations + RLS)           | Supabase |
| Storage   | Supabase Storage (buckets + policies)          | Supabase |

## Commands

```bash
# Frontend (apps/web)
pnpm dev              # local dev server
pnpm build            # production build check
pnpm lint             # lint

# Backend (apps/api)
uv run uvicorn app.main:app --reload   # local dev
uv run pytest                          # tests

# Supabase
supabase start                         # local Supabase
supabase db reset                      # apply migrations + seed
supabase db push                       # push to hosted project
supabase gen types typescript --local > apps/web/lib/db.types.ts

# Deploy
vercel deploy                          # Vercel preview
railway up                             # Railway deploy (from apps/api)
```

## Secrets — Where They Live

| Var | Location |
|-----|----------|
| `OPENAI_API_KEY` | apps/api only (server) |
| `SUPABASE_SERVICE_ROLE_KEY` | apps/api only (server) |
| `SUPABASE_URL` | apps/api only |
| `WEB_ORIGIN` | apps/api (CORS allowlist) |
| `NEXT_PUBLIC_SUPABASE_URL` | apps/web (public) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | apps/web (public) |
| `NEXT_PUBLIC_API_URL` | apps/web (Railway backend URL) |

**Never** put `OPENAI_API_KEY` or `SUPABASE_SERVICE_ROLE_KEY` in apps/web or client-side code.

## Rules

- Verify OpenAI, Supabase, and Vercel/Railway usage against current official docs before implementing.
- Store all schema changes as versioned migrations (`supabase/migrations/YYYYMMDDHHmmss_name.sql`).
- Enable RLS on every user-owned table; scope policies to `auth.uid() = user_id`.
- FastAPI must bind to `$PORT` for Railway. Include a `/health` route.
- FastAPI CORS must allow `WEB_ORIGIN` env var (Vercel preview URL + localhost).
- Commit `.env.example` with variable names only. Keep `.env.local` and `.env` git-ignored.
- Verify UI in Browser at desktop (1280px) and mobile (375px) before claiming feature complete.
- Final responses must include: checks run, routes/screenshots verified, known risks.

## Named Subagents (via ~/.codex/agents/)

Spawn these in parallel for independent work:

| Agent | Scope | Mode |
|-------|-------|------|
| `web-worker` | apps/web/ only | workspace-write |
| `api-worker` | apps/api/ only | workspace-write |
| `supabase-worker` | supabase/ only | workspace-write |
| `explorer` | whole repo | read-only |
| `api-reviewer` | whole repo | read-only |
| `demo-risk` | whole repo | read-only |

Fan-out pattern: "Spawn web-worker and api-worker in parallel. Explorer can run simultaneously."
Workers own disjoint directories — safe to run concurrently.
No parallel writers in the last 30 minutes before demo.

## Done When

- [ ] Web → API → OpenAI → Supabase round trip works end-to-end.
- [ ] One error state and one empty/loading state are handled.
- [ ] `pnpm build` passes; `uv run pytest` passes (or failures documented).
- [ ] Vercel preview URL is live and verified in Browser.
- [ ] Railway backend is live with /health returning 200.
- [ ] Demo evidence packet is complete (see `~/.codex/hackathon/PROMPTS.md`).
