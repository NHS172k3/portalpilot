# PortalPilot Demo Evidence

Last updated: 2026-06-06

## Current Status

- App code is scaffolded for the PortalPilot PRD MVP: dashboard, filings board, Action Center, Company Profile, Activity, Settings, FastAPI backend, OpenAI Responses flow, OpenAI Agents SDK orchestration, safe computer-use browser harness, and Supabase schema.
- `apps/api/.env` and `apps/web/.env.local` are present locally and ignored by git.
- Backend `/health` reports live env readiness when loaded with the current local env: OpenAI configured, Supabase configured, no missing env.
- Hosted Supabase schema is not applied yet because the Supabase MCP is read-only and the local Supabase CLI needs `supabase login` or `SUPABASE_ACCESS_TOKEN`.
- `/health` now reports persistence status so missing Supabase tables are visible instead of being hidden behind in-memory fallback.

## Checks Run

```bash
cd apps/api && $env:UV_CACHE_DIR='C:\Users\harin\Hackathons\openai-hackathon\apps\api\.uv-cache'; uv run pytest
# 20 passed

pnpm lint
# passed

pnpm build
# passed
```

## Routes Verified

Production Next route smoke on `http://127.0.0.1:3103`:

- `/` -> 200
- `/filings` -> 200
- `/actions` -> 200
- `/activity` -> 200
- `/profile` -> 200
- `/settings` -> 200

FastAPI route smoke:

- `/health` -> 200, `mode: live`
- `OPTIONS /dashboard` from `http://127.0.0.1:3000` -> 200
- `/filings/describe` -> 200
- `/filings/{id}/computer-use` against a sign-in/password HTML page -> 200 with `status: blocked` and a `human_wall_handoff`

## Env Notes

Required local files:

- `apps/api/.env`
- `apps/web/.env.local`

Current env blocker:

- No app env values are missing.
- Supabase CLI migration push needs either `supabase login` or `SUPABASE_ACCESS_TOKEN`.
- Optional local-dev CORS override is now supported with `WEB_ORIGINS`.
- Optional computer-use tuning vars are `COMPUTER_USE_MODEL=computer-use-preview` and `COMPUTER_USE_MAX_STEPS=4`.

Supabase migration push:

```bash
supabase login
supabase link --project-ref etesovwhwiezjpjhzcaq
supabase db push
```

The MCP security advisor also reported an exposed `public.rls_auto_enable()` SECURITY DEFINER function in the hosted project. The migration `20260606020000_revoke_public_rls_auto_enable.sql` revokes public/anon/authenticated execute permission when migrations are pushed.

## Local Dev Recovery

- If Next.js reports `Cannot find module './<chunk>.js'` from `.next/server/webpack-runtime.js`, clear the stale build cache and restart the web dev server:

```bash
pnpm clean:web
pnpm dev
```

- From `apps/web`, the equivalent command is `pnpm dev:clean`.

## Computer Use Verification

- Verified against current OpenAI docs: computer use is a Responses API capability using the `computer-use-preview` model with the `computer_use_preview` tool.
- Installed Playwright Chromium locally and added a live isolated browser harness.
- Backend flow: screenshot page -> request OpenAI CUA action -> enforce PortalPilot guardrails -> execute allowed action with Playwright -> send screenshot back.
- Access-gated portal steps surface as Action Center handoffs; the app must not claim it logs in, solves MFA/CAPTCHA, submits, endorses, or pays.

## Known Risks

- Hosted Supabase migration has not been applied yet.
- Browser desktop/mobile screenshots have not been captured because no callable Browser control tool is currently exposed in this session.
- The CUA endpoint is live, but real official portals may block headless browsers or require user sessions. Those cases should become handoffs, not autonomous submissions.
