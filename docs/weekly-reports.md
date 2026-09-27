# Weekly portfolio report worker

`services.worker.weekly_reports` automatically drafts a portfolio report every Monday at 08:00 UTC for explicitly configured tenants. It reuses the deterministic capacity/historical analysis and report builder. It makes no LLM calls, sends no messages, and changes no project plans. The saved report always requires human review.

Run this private worker alongside the application services after applying the database migration and provisioning tenant memberships. It uses the same Python service image and dependencies, with its command replaced by:

```sh
python -m services.worker.weekly_reports
```

Configure these environment variables only in the worker container or a protected operator shell:

| Variable | Meaning |
| --- | --- |
| `SUPABASE_URL` | Supabase API URL; HTTPS required except localhost and `host.docker.internal` |
| `SUPABASE_SERVICE_ROLE_KEY` | Privileged worker secret; never expose to browser or user-facing API services |
| `WEEKLY_REPORT_TARGETS` | JSON object mapping each tenant UUID to its designated report owner/reviewer member UUID |
| `WEEKLY_REPORT_HOUR_UTC` | Monday generation hour, 0–23; default 8 |
| `WEEKLY_REPORT_POLL_SECONDS` | Retry/check interval, 15–3600 seconds; default 300 |

Example shape, with placeholders replaced by actual UUIDs:

```text
WEEKLY_REPORT_TARGETS={"TENANT_UUID":"MEMBER_UUID","ANOTHER_TENANT_UUID":"ANOTHER_MEMBER_UUID"}
```

No wildcard tenant enumeration is supported. The configured owner must be a member of the same tenant. The worker validates membership before reading sources and writing a report. `created_by` identifies the designated owning member for the existing database contract; the actual automated author is recorded as `report_data.generated_by = weekly_portfolio_worker`, and its database audit actor is null because a service credential has no end-user identity. Human review is not implied by that owner field.

The worker reads every page of projects, resources, allocations and historical phase metrics for each configured tenant. It fails rather than saving a silently truncated report if a source exceeds 100,000 rows. Keyset pagination avoids offset drift, but separate API requests do not provide one cross-table transaction snapshot; concurrent changes may be represented at different instants. A future warehouse/snapshot job is appropriate for strict accounting cutoffs.

Reports are stored in the RLS-protected `reports` table with `report_type = weekly_portfolio`. `status = complete` means the generation finished; `report_data.draft_status = awaiting_human_review` and `human_review_required = true` identify the unapproved draft. Members can retrieve their tenant reports through Supabase/PostgREST. The worker does not add a public endpoint or notification delivery.

The primary key is a deterministic UUID derived from tenant and ISO year/week. Concurrent replicas race on PostgreSQL's existing primary-key constraint; one inserts, others verify the matching saved report and stop. The worker uses plain INSERT, never overwrite/upsert, so an acknowledged or unacknowledged prior save cannot be silently replaced. No extra migration or external scheduler state is needed. A conflicting record with an unexpected marker causes a visible failure log instead of being treated as a valid scheduled report.

After downtime, the worker catches up the current ISO week once its Monday time has passed. It does not reconstruct missed older weeks from today's data. Every report records scheduled and actual generation times and explicitly describes its snapshot as current records. Source/network failures retry at the configured poll interval; one failing tenant does not block others. Logs include exception classes and tenant IDs, never response bodies or credentials.

For an external scheduler, run the due-week check once:

```sh
python -m services.worker.weekly_reports --once
```

The command returns 1 if any tenant fails, 2 for invalid configuration, and 0 for saved/already-existing/not-yet-due reports. For example, an operator-managed cron job can run `--once` hourly with secrets supplied by its environment. Do not place secrets directly into a crontab command. Container mode should use a restart policy and should disable the inherited HTTP healthcheck because this worker serves no HTTP port; monitor job logs and report freshness instead.

Validation includes Monday/ISO-year scheduling, catch-up behavior, deterministic IDs, pagination, cross-tenant response rejection, duplicate-race handling, human-review metadata, failure isolation and secret-safe logs. Tests mock HTTP; actual scheduled execution against Supabase requires the configured deployment and has not been run on the build machine.
