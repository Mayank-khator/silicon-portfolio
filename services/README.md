# Python services

Run commands from the repository root with Python 3.13. The four HTTP services
have no unauthenticated demo data routes. `/health` is process liveness only;
it does not assert that Supabase, PostgreSQL or RabbitMQ is reachable.

```powershell
python -m venv services/.venv
services/.venv/Scripts/python -m pip install -r services/requirements-dev.txt
services/.venv/Scripts/python -m pytest -q
$env:SUPABASE_URL = 'http://127.0.0.1:54321'
$env:SUPABASE_PUBLISHABLE_KEY = '<local public/anon key>'
services/.venv/Scripts/python -m uvicorn services.project_npi.app:app --port 8002
```

On Linux use `services/.venv/bin/python`. Apply the Supabase migration and
provision an authenticated user's tenant membership before using any domain API.
Use separate terminals and ports for the other services:

| Service | Module | Suggested port |
| --- | --- | --- |
| User | `services.user.app:app` | 8001 |
| Project and NPI | `services.project_npi.app:app` | 8002 |
| Resource and time | `services.resource_time.app:app` | 8003 |
| Analysis and reporting | `services.agentic_ai.app:app` | 8004 |

Every domain request requires `Authorization: Bearer <Supabase user access token>`.
The API validates that token at `/auth/v1/user` and sends the same token to
PostgREST. SQL row policies check live tenant membership and roles. Neither
`X-Role` nor client-provided claims grant authority. API services do not read a
service-role key. Redirect following is disabled so credentials are not forwarded
to another host by an upstream redirect. Deploy the API and Supabase over TLS.

## HTTP contract

GET collection routes require a UUID `tenant_id` query parameter and accept
`limit` (1–200, default 100) and `offset` (default 0). Results are raw JSON arrays
in UUID order. Tasks, allocations and time entries optionally accept `project_id`.
POST accepts a domain record containing `tenant_id` and returns the raw saved
record with HTTP 201. IDs, versions and approval metadata are database-managed.
Tenant IDs select a scope; they do not establish permission to access it.

| Routes | Methods |
| --- | --- |
| `/api/me` | GET; returns `{user, memberships}` |
| `/api/projects`, `/api/tasks`, `/api/demands` | GET, POST |
| `/api/projects/{id}`, `/api/tasks/{id}`, `/api/demands/{id}` | PATCH |
| `/api/resources`, `/api/allocations`, `/api/time-entries` | GET, POST |
| `/api/resources/{id}`, `/api/allocations/{id}` | PATCH |
| `/api/time-entries/{id}` | PATCH |
| `/api/insights?tenant_id=...` | GET; returns `{insights, source, historical_sample_count, human_review_required}` |
| `/api/reports` | POST `{tenant_id, report_type, use_llm}`; returns report JSON |

PATCH bodies contain `tenant_id`, the record's current `version`, and at least
one changed field. For example:

```json
{"tenant_id":"11111111-1111-4111-8111-111111111111","version":3,"status":"at_risk"}
```

The API prechecks validation, then PATCHes using `id`, `tenant_id` and `version`
filters in one database operation. The database increments the version. A stale
version or a write filtered away by concurrent changes returns HTTP 409; refresh
and resolve before retrying. A missing/inaccessible record returns 404; invalid
input or a database invariant returns 422; role denial returns 403. Raw database
errors and tokens are never included in API errors.

Resource PATCH accepts `name`, `role` (job title), `skills`, `fab_nodes` and
`weekly_capacity`. Allocation PATCH accepts `resource_id`, `project_id`,
`hours_per_week`, `start_date` and `end_date`. Weekly capacity and allocated hours
must be positive and at most 168. Empty skill/node arrays clear those values;
explicit nulls and client-written ownership/approval fields are rejected. To end
an allocation, shorten its end date while keeping it on or after its start date.
Past end dates are accepted. Database RLS and relationship constraints still
authorize changes and reject invalid or cross-tenant reassignment.

Projects start at Ideation. Advancing requires the next sequential phase. Entering
DVT, PVT and Ramp/Launch requires design freeze approval. A permitted reviewer
sets `design_frozen: true` via PATCH; database triggers enforce the role and
record the approval actor/time. API prechecks are convenience validation; the
database independently enforces phase rules, roles, relationships, immutable audit
records, aggregate daily time limits and concurrency. Time entries use the caller's
user ID; API input requires positive quarter-hour increments no greater than 24
and rejects future work dates. SQL enforces the user/date total across entries.

## Reporting and optional language generation

Reports default to deterministic calculations. `report_type` is `executive`,
`resource` or `risk`. Report JSON is returned without being persisted by this API;
the client may explicitly save it to the RLS-protected reports table. Recommendations
never modify project records.

Capacity analysis sweeps inclusive allocation date intervals, compares their
overlapping weekly run rates with resource capacity, and reports each resource's
peak overload and date range. It does not model holidays or individual calendars.
Delay signals compare at least three completed metrics with the same node and EVT
or DVT phase, using median actual minus planned days. Insufficient data produces
no delay forecast. This is descriptive analysis, not a trained or validated ML
model. Synchronous analysis refuses datasets at 10,000 rows per table instead of
quietly truncating results. Reads are live and are not a single database snapshot.

No LLM integration is installed or contacted by default. To enable optional
LangChain output, install `services/requirements-llm.txt` (or build the image with
`ENABLE_LLM=true`). Then configure a provider and a model. The individual request
must also include `use_llm: true`.

| Environment variable | API services | Worker |
| --- | --- | --- |
| `SUPABASE_URL` | Required | Required |
| `SUPABASE_PUBLISHABLE_KEY` | Required; legacy `SUPABASE_ANON_KEY` fallback | Unused |
| `CORS_ORIGINS` | Comma-separated origins; default `http://localhost:3000` | Unused |
| `SUPABASE_SERVICE_ROLE_KEY` | **Do not inject into API containers** | Required, secret |
| `RABBITMQ_URL` | Unused | Required, secret |
| `LLM_PROVIDER` | Agent only: `none` default, `ollama`, or `groq` | Unused |
| `LLM_MODEL` | Agent only: explicit installed/available model name | Unused |
| `OLLAMA_BASE_URL` | Agent only: default `http://ollama:11434` | Unused |
| `ALLOW_EXTERNAL_LLM` | Agent only: must be `true` to use Groq | Unused |
| `GROQ_API_KEY` | Agent only, secret, only for opted-in Groq | Unused |

Optional providers receive aggregate budget/status metrics only, without names,
IDs, notes or user tokens. Even aggregate financial information can be sensitive;
enable external providers only under the organization's data-handling policy.
Language output is a separate unverified narrative. Missing optional libraries,
provider failures and a 25-second timeout return the deterministic report with a
clear `llm_status`; they do not hide a failed database read.

## Transactional outbox

Run the private worker with `python -m services.worker.outbox`. It has no HTTP
listener and must not be exposed through Kong. Disable the image's HTTP
healthcheck for this container; monitor worker logs and pending/dead row counts.
Only this worker receives the legacy Supabase service-role JWT key.

The migration provides service-role-only RPCs:

- `claim_outbox_events(p_limit, p_worker_id)` atomically leases pending rows.
- `acknowledge_outbox_event(p_id, p_worker_id)` accepts only the current lease owner.
- `fail_outbox_event(p_id, p_worker_id, p_error)` schedules retry/backoff and eventually dead-letters.

The worker claims five rows, publishes concurrently to durable topic exchange
`silicon.events`, and acknowledges SQL only after RabbitMQ confirms. It declares
durable queue `silicon.events.audit` bound to `#` so mandatory publishing cannot
silently discard an unbound event. Broker data needs a persistent volume.
Delivery is **at least once**. A crash between publish and acknowledgement can
duplicate an event; future consumers must deduplicate `message_id` (the event UUID).
This queue is a durable event handoff, not a retention-managed analytics consumer;
operators must provide consumption, retention and queue-depth monitoring.

## Verification scope

Tests exercise actual validation, route behavior and the shared REST boundary,
using mock HTTP responses only for the external Supabase service. They also test
outbox acknowledgement order and provider fallback. Database role/RLS tests live
under `supabase/tests`; API tests do not prove deployed PostgreSQL policies.
The local Python suite does not verify live Supabase, an actual RabbitMQ broker,
Docker runtime, provider availability or production infrastructure controls.
The runtime pins and transitive constraints were checked using `pip-audit` on
2026-09-27; `dependency-audit.json` records zero known vulnerabilities at that time.
This point-in-time package check is not a security certification and does not
cover optional LLM extras or container OS packages.

Primary references: [Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys),
[Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security),
[FastAPI bearer security](https://fastapi.tiangolo.com/tutorial/security/),
[RabbitMQ publisher confirms](https://www.rabbitmq.com/docs/confirms).
