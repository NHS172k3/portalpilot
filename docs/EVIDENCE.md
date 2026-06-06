# PortalPilot Evidence Packet

Generated on 2026-06-06.

## Screenshots

- Phase 9 Action Required: `/private/tmp/portalpilot-evidence/phase9-action-required-desktop.png`
- Phase 10 Research Evidence: `/private/tmp/portalpilot-evidence/phase10-research-desktop.png`
- Phase 11 Live Handoff: `/private/tmp/portalpilot-evidence/phase11-live-handoff-desktop.png`
- OpenAI palette queue: `/private/tmp/portalpilot-evidence/openai-queue-desktop.png`

Mobile screenshots from earlier phases exist, but the current demo is desktop-focused.

## Verified Commands

```bash
uv run pytest                                  # 27 passed, 1 warning
pnpm lint                                     # passed
pnpm build                                    # passed
uv run python scripts/smoke_phase9.py         # action_required -> in_progress -> completed
uv run python scripts/smoke_generality.py     # different form -> action_required -> action_required -> completed
uv run --script apps/api/scripts/smoke_openai.py # Responses + web_search + computer passed
grep -rniE "bizfile|acra|ssic|corppass|share capital|constitution" \
  apps/api/app apps/web --include='*.py' --include='*.ts' --include='*.tsx' # empty
```

## Demo Routes

- Web queue: `http://localhost:3000/queue`
- API health: `http://127.0.0.1:8000/health`
- Mirror form route: `http://localhost:3000/mirror/<form_definition_id>`

## Phase Gate Notes

- Phase 9: a missing required field parks a task in `Action Required`; user-supplied info resumes the generic agent; review completion moves the task to `Completed`.
- Phase 10: manual-add and auto-suggest use OpenAI Responses API with `web_search`; backend filters stored source links to official-looking government/regulator domains.
- Phase 11: live portal path reaches the real `portal_url`, records `live_portal_reached`, sets `auth_required`, and shows `Open portal` plus `I authenticated` handoff controls.
- Generality: `smoke_generality.py` inserts a different form definition, runs the same mapper/agent/wall/resume/completion flow, and deletes the temporary rows.

## Known Risks

- Live portal filling after authentication is still handoff-based; the backend does not solve CAPTCHA or enter credentials.
- Deployment to Vercel/Railway was not performed in this local run.
- Source-domain filtering is conservative and may reject valid regulators on unusual non-government domains.
