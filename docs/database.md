# Supabase database

`supabase/migrations/202609270001_initial.sql` is the authoritative data and authorization model. The API forwards a verified user's Supabase access token to PostgREST. Membership lookup always uses `auth.uid()`, never a browser role field or an HTTP role header. User metadata does not grant access.

The static browser demo has its own synthetic local state. Running the database setup below does not migrate browser-local data or turn a static demo into a configured enterprise service.

## Start a development project

Install Docker and the Supabase CLI, then run these commands from the repository root:

```sh
supabase start
supabase db reset
supabase status
```

Local ports are API `54321`, PostgreSQL `54322`, Studio `54323`, and local mail inbox `54324`. The checked-in config uses PostgreSQL 17, disables public signup, and permits localhost redirects. Configure actual site URLs and SMTP before deployment. Use `supabase db push` only after linking an intended hosted development project and reviewing the migration.

`supabase/seed.sql` deliberately creates no users and no fixed credentials. Provision Auth first, then run the explicit seed script. In PowerShell:

```powershell
$env:SUPABASE_URL = 'http://127.0.0.1:54321'
# Set SUPABASE_SERVICE_ROLE_KEY from local `supabase status` securely in your shell.
# Set SILICON_DEMO_PASSWORD to a unique development password of at least 16 characters.
python supabase/scripts/bootstrap_demo.py --email your-development-email@example.com
```

The script uses the Auth Admin API to create and confirm the supplied development identity, creates a synthetic tenant and its fab-manager membership, and seeds six projects, eighteen tasks, six fictional resources, allocations (including an intentional overload), three demands, twelve historical observations, and five draft time entries. It prints tenant and user IDs, but never secrets. Remote seeding requires HTTPS and the explicit `--allow-remote` flag; use only a nonproduction project. The service key remains a local operator secret. It must never appear in `NEXT_PUBLIC_*`, a browser bundle, client logs, or a public deployment environment.

If the Auth user already exists, add `--user-id AUTH_UUID`; the script verifies its email before granting membership. To rerun an existing sample tenant, pass both `--user-id` and `--tenant-id`. A rerun resets synthetic records and generates new audited mutations. API requests are separate transactions; a network failure can leave a partial seed. Reuse those IDs to recover instead of making duplicate users or tenants. Do not use the bootstrap script for production provisioning.

## Tables and contracts

All domain entities use UUID `id` and `tenant_id`. Parent references use composite tenant foreign keys. A task cannot point to another tenant's project; a time entry's task must belong to its stated project. Resource/user and assigned-task references must match a membership in that same tenant.

| Table | Principal fields |
| --- | --- |
| `tenants` | `id`, `name`, `created_at` |
| `memberships` | `id`, `tenant_id`, `user_id`, `role`; unique tenant/user |
| `projects` | `code`, `name`, `node`, `stage`, `status`, `progress`, `budget`, `spent`, `roi`, `start_date`, `end_date`, `owner`, optional `owner_id`, `strategic_alignment`, freeze fields |
| `tasks` | `project_id`, `title`, `stage`, `status`, `start_date`, `end_date`, `progress`, optional `assigned_to` |
| `demands` | `title`, `category`, `node`, `estimated_budget`, `strategic_score`, `status` |
| `resources` | `name`, `role` (display profession), `skills text[]`, `fab_nodes text[]`, `weekly_capacity`, optional `user_id` |
| `allocations` | `resource_id`, `project_id`, `hours_per_week`, `start_date`, `end_date` |
| `time_entries` | `user_id`, `project_id`, optional `task_id`, `phase`, `work_date`, `hours`, `billable`, `note`, `status`, server-maintained approval fields |
| `historical_phase_metrics` | optional `project_id`, `node`, `phase`, `planned_days`, `actual_days`, `completed_at` |
| `reports` | `report_type`, `title`, `report_data jsonb`, `status`, `created_by` |
| `audit_logs` | `tenant_id`, `actor_id`, `entity`, `record_id`, `operation`, `previous_data`, `new_data`, `occurred_at` |
| `outbox` | `tenant_id`, `event_type`, `payload`, `status`, lease, retry and publication metadata |

Mutable domain rows also carry `version`, `created_at`, and `updated_at`. Dates use ISO date strings; timestamps use UTC ISO timestamps. Numeric PostgreSQL values may be serialized as numbers or strings by clients; validate and convert deliberately.

- NPI phase names: `Ideation`, `Feasibility`, `EVT`, `DVT`, `PVT`, `Ramp/Launch`.
- Project status: `on_track`, `at_risk`, `delayed`.
- Task status: `todo`, `in_progress`, `done`.
- Demand status: `submitted`, `under_review`, `approved`, `rejected`, `converted`.
- Time status: `draft`, `submitted`, `approved`, `rejected`.
- Report status: `pending`, `complete`, `failed`.

## Role permissions

All members can read their tenant's domain records, audit events and reports. Time entries are visible within the tenant, so use a stricter policy if personnel time requires additional privacy controls.

| Action | fab_manager | lead_architect | qa_engineer | exec_sponsor | engineer |
| --- | --- | --- | --- | --- | --- |
| Create/update project plans | Yes | Yes | No | No | No |
| Delete project (when no FK dependents) | Yes | No | No | No | No |
| Approve/revoke EVT design freeze | Yes | No | Yes | No | No |
| Create/plan/delete tasks | Yes | Yes | Yes | No | No |
| Update assigned task status/progress | Yes | Yes | Yes | Assigned only | Assigned only |
| Manage demand funnel | Yes | Yes | No | Yes | No |
| Manage resource records | Yes | No | No | No | No |
| Manage allocations/historical metrics | Yes | Yes | No | No | No |
| Submit own time | Yes | Yes | Yes | Yes | Yes |
| Review another person's submitted time | Yes | Yes | No | No | No |
| Save/read generated reports | Yes | Yes | Yes | Yes | Yes |
| Provision users/tenants or change membership roles | Operator only | Operator only | Operator only | Operator only | Operator only |

Tenant membership and role changes require a trusted operator using Auth Admin and service credentials. No browser or API user, including a fab manager, can create a tenant, join another tenant, promote themselves, or forge roles. Membership changes are audited. Operators should use a separate, reviewed provisioning workflow with identity verification; the development seed is not that workflow.

New user-created projects begin in Ideation and move forward exactly one stage at a time. Entering DVT requires `design_frozen=true`, approved by QA or a fab manager from EVT onward. Approval records the actual caller and timestamp; supplied approver values are ignored. QA can change only freeze state, not budget, stage, dates or ownership. Approved freezes cannot be removed once a project reaches DVT. Service-role provisioning can import historical project states and is therefore an explicit trust boundary.

Time entries must have positive quarter-hour increments, no future UTC work dates, at most 24 hours per entry and per member/day, and fall within project and (when supplied) task dates. An advisory transaction lock serializes mutations to the same member/day; separate-connection race testing is still required in the target Supabase environment. Only the owner can edit draft or rejected time, and only draft entries can be deleted. Submitted time is immutable except for review by a different fab manager/lead architect. An approver cannot change the submitted hours while approving it.

## Optimistic concurrency

The API's normal path is a PostgREST PATCH filtered by `id`, `tenant_id`, and the last-read `version`, with `Prefer: return=representation`. An empty result means stale version, inaccessible record, or missing record and must be handled as a conflict/access failure. The database increments the stored version itself; clients cannot choose a version or change identity/tenant fields.

```text
PATCH /rest/v1/projects?id=eq.PROJECT_UUID&tenant_id=eq.TENANT_UUID&version=eq.3
Authorization: Bearer USER_ACCESS_TOKEN
Prefer: return=representation
{"progress": 45}
```

An optional invoker-security RPC, `patch_record(p_entity text, p_id uuid, p_tenant_id uuid, p_expected_version integer, p_changes jsonb)`, locks the visible row, checks its version, permits only allowlisted fields, then updates through RLS. It returns the updated JSON record. SQLSTATE `40001` means stale version, `42501` denied, `P0002` unavailable record, and `22023` invalid patch. Only the seven mutable business tables in the function's allowlist are supported. Direct database/PostgREST clients must still supply the version filter; the trigger cannot infer whether a caller read a prior version.

## Audit and events

After every successful tenant, membership, or domain insert/update/delete, a security-definer trigger writes one audit record and one outbox event in the same transaction. Rollback removes both. Audit records include the verified `auth.uid()` actor, before/after row data and timestamp. Operator actions without a user JWT have a null actor, so external operator audit logging is also required.

Audit INSERT/UPDATE/DELETE/TRUNCATE privileges are revoked from browser roles and service_role. UPDATE/DELETE/TRUNCATE triggers also reject tampering. This prevents ordinary application users and worker credentials changing history; a PostgreSQL owner/superuser can disable triggers, change grants or rewrite data. This is append-only application auditing, not a cryptographic tamper-proof log. For regulated environments, export to separately administered immutable retention storage, record operator activity, and control database-owner access.

Private functions have an empty fixed `search_path`, fully qualified object references and explicit execution grants. The private schema is excluded from PostgREST's exposed schema list. RLS is enabled on every public application table; anon has no application-table access.

Outbox access is service-role only. The queue worker uses:

| RPC | Contract |
| --- | --- |
| `claim_outbox_events(p_limit integer, p_worker_id text)` | Returns `{id,event_type,payload,attempts}` rows; limit 1–100; claims with `FOR UPDATE SKIP LOCKED`; increments attempts; leases for 60 seconds |
| `acknowledge_outbox_event(p_id uuid,p_worker_id text)` | Returns true only for the active lease owner and marks published |
| `fail_outbox_event(p_id uuid,p_worker_id text,p_error text)` | Returns true only for active owner; records a capped error and exponential retry backoff |

Events use `event_type = '<table>.<insert|update|delete>'`. Payload contains `tenant_id`, `entity`, `record_id`, `operation`, `actor_id`, `data`, and `previous`. A maximum of eight delivery attempts marks a message `dead`, including repeated worker crashes. A trusted operator can investigate/requeue a dead event using a separately audited runbook. A publish followed by a lost acknowledgment can be delivered again: consumers must deduplicate using the outbox event UUID. The service role bypasses RLS across all tenants, so keep it only in the worker/operator environment, use a separate secret from user-facing services, and rotate it after exposure.

## Realtime and reports

The `supabase_realtime` publication includes projects, tasks, demands, resources, allocations, time entries, historical metrics, reports and audit logs. It excludes the worker outbox. Subscriptions must use the user access token, filter by tenant and refetch after a notification; browser requests still need RLS. Do not treat a client-side channel filter as authorization. Refresh/reconnect subscriptions after role changes or revocation. The default replica identity exposes no complete old row for deletes; use authorized refetches instead of relying on old-row content.

Reports are JSON records, avoiding an unprotected object-storage bucket. A member can insert a report only for themselves and their tenant, then read it. Ordinary clients cannot rewrite a saved report. The current agent endpoint may return a report without persisting it; this table is available for explicit report-saving behavior. File exports require tenant-scoped Storage policies before enabling uploads.

## Verification and deployment limits

Run the executable PostgreSQL security suite without Docker:

```sh
npm install --prefix supabase/tests --ignore-scripts
node supabase/tests/run.mjs
```

If using pnpm from a parent workspace, install with `pnpm --dir supabase/tests --ignore-workspace install --ignore-scripts`. The embedded PGlite runtime applies the actual migration, supplies minimal Supabase Auth role/identity fixtures, and runs `supabase/tests/security.sql`. The suite covers tenant isolation, composite foreign keys, role self-escalation, RBAC, freeze approval/gates, stale version rejection, time bounds/approvals, report isolation, audit immutability/rollback, outbox transaction coupling and worker lease ownership/retry.

For a disposable local Supabase database, execute the same rollback-only test SQL as the postgres administrator:

```sh
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres -v ON_ERROR_STOP=1 -f supabase/tests/security.sql
```

The local connection password in that command is the Supabase CLI development default; never reuse it for a remote database. The test inserts temporary fixture identities and rolls back the transaction. Do not execute this test in production.

Build-machine verification: migration and 58 database assertions passed in embedded PostgreSQL. Docker, psql and the Supabase CLI were unavailable, so native Supabase Auth HTTP, PostgREST/RLS integration, Realtime authorization, worker-to-RabbitMQ delivery, and multiple-database-connection races were not executed. The bootstrap script was syntax-checked; actual Auth user creation and HTTP seeding need a configured project.

Before production, configure TLS for every network hop, provider disk/backup encryption, secrets rotation, restrictive operator access, external audit retention, backups and tested restore, tenant deprovisioning/retention procedures, database observability, reviewed migrations, Realtime revocation behavior, and load/concurrency testing. These controls are prerequisites, not claims of compliance or certification.
