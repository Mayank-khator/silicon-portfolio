# Verification record — 2026-09-28

Completed on Windows with Node 24.19.0 and Python 3.13.7:

| Check | Result |
| --- | --- |
| Frontend domain and connected-data regression tests | 23 passed |
| FastAPI, domain analysis, outbox and weekly-worker tests | 64 passed |
| Real SQL migration + RLS/trigger regression assertions in PGlite | 58 passed |
| TypeScript strict check | Passed |
| Next.js 16.3.6 static production build | Passed |
| Production JavaScript dependency advisory audit | 0 known vulnerabilities at check time |
| Python runtime dependency advisory audit | 0 known vulnerabilities at check time (services/dependency-audit.json) |
| Compose/Kong YAML parsing and config reference review | Passed static validation |

Original 2026-09-27 browser checks against the built static artifact: desktop dashboard; project creation and persistence after reload; demand advancement; logging and submitting time; Gantt navigation; 18-card Kanban; report preview; resource-overload warning; activity history; cross-tab reset propagation; 390px mobile layout/navigation. No browser console errors were observed during these checks. Synthetic QA edits were reset afterward.

Review fixes included audit schema mapping, account-change cache clearing, stale-result guards, complete paginated reads, visible mutation errors, own-user timesheet submission controls, Ideation-only creation, quarter-hour/future-time SQL enforcement, scrollable sidebar and mobile table containment.

## GitHub Pages update verification (2026-09-28)

The Pages-specific production build and TypeScript compilation pass at `/silicon-portfolio/`. Frontend tests include workspace data isolation, malformed-storage rejection, profile persistence, migration of legacy versionless records, and calendar-based roadmap boundaries. Backend tests include allocation/resource PATCH authorization forwarding, version conflicts, input validation, and date ordering.

Browser checks on the updated static export verified workspace creation with an empty portfolio, switching back to the unchanged six-program sample portfolio, profile editing and persistence across reload/new tab, project creation, task creation and board display, a 2028 roadmap, adding an engineer, allocating 48 hours then editing to 32 hours (overload resolved), and preserving zero budget/ROI/alignment and a 2nm node when reopening a project. The profile dialog fits a 390px viewport without horizontal page overflow. No app console errors were observed in the final preview. A local preview process stopped between user turns and was restarted; this was not a hosted-app failure.

The SQL and dependency audit results above were established on 2026-09-27; this UI/API update did not change the migration or dependency versions. Public-host deployment status is recorded separately in `deployment.md`.

## Not established by these checks

- Docker Engine / Compose runtime, native Supabase Auth, PostgREST and Realtime, actual RabbitMQ publish delivery, external provider calls and full connected-browser flows were not available for end-to-end execution.
- SQL tests use real embedded PostgreSQL with Auth fixtures, not the Supabase network stack. Multiple-connection time-entry races and production revocation behavior still need integration tests.
- No penetration test, independent compliance audit, load test, restore exercise, disaster-recovery test, SSO/MFA rollout or export-control legal assessment was performed.
- Point-in-time dependency checks exclude container OS packages and optional model weights/providers. They do not guarantee absence of security defects.
- Demo browser storage is editable, device-local, and not a production audit or concurrency mechanism.

Run the documented connected setup in a disposable environment, then test two users/tenants, JWT expiry, role revocation, simultaneous edits, broker outages/retries, scheduled-report restart behavior and recovery before any enterprise pilot.
