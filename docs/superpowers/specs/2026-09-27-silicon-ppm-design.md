# Silicon Portfolio — design brief

Build an independently implemented semiconductor NPI portfolio application for a management demonstration and further enterprise development. This is an original product inspired by common PPM capabilities, not a Sciforma clone, integration, or certification claim. All shipped sample names, budgets, schedules and people are fictional.

## Delivery modes

1. A Next.js App Router static-export demo with interactive portfolio, demand funnel, Gantt and Kanban, resource allocation, time tracking, agent insights and audit views. Changes persist on this browser and synchronize between its tabs. Clearly label this a synthetic, device-local demo, not shared enterprise storage.
2. The same frontend can use Supabase Auth, PostgreSQL RLS and Realtime with FastAPI services behind Kong. This requires a configured Supabase project and operator provisioning. No privileged database/service keys in the browser. Docker Compose runs Kong, four Python services and RabbitMQ locally, against Supabase CLI local infrastructure or a hosted Supabase project. Docker is not presently installed on the build machine; do not claim container runtime verification unless it becomes available.

## Domain contracts

Every domain record carries UUID id and tenant_id. NPI stages: Ideation, Feasibility, EVT, DVT, PVT, Ramp/Launch. Projects contain name, code, node, stage, status (on_track/at_risk/delayed), progress, budget, spent, roi, start_date, end_date, owner, strategic_alignment, version. Tasks: project_id, title, stage, status (todo/in_progress/done), start_date, end_date, progress, version. Demands: title, category, node, estimated_budget, strategic_score, status. Resources: name, role, skills, fab_nodes, weekly_capacity. Allocations: resource_id, project_id, hours_per_week, start_date, end_date. Time entries: user_id, project_id, task_id, phase, work_date, hours, billable, note, status. Audit events record actor, tenant, entity, operation, previous/new data and timestamp; database privileges and triggers prevent ordinary users changing logs, but administrators remain a trust boundary.

## APIs and trust boundaries

Use GET /api/projects, POST /api/projects, PATCH /api/projects/{id}; equivalent tasks and demands endpoints. User service GET /api/me. Resource service GET/POST /api/resources, /api/allocations, /api/time-entries. Agent GET /api/insights and POST /api/reports. Services forward the authenticated Supabase bearer token to PostgREST so RLS remains authoritative. Tenant membership comes from database policies, never a trusted client role header. Mutations require appropriate roles and audit triggers. Protect phase transitions and freeze approval; concurrency uses version matching. RabbitMQ events use a transactional outbox for reliable delivery. AI uses deterministic, explainable capacity and historical-delay analysis, optionally LangChain+Ollama; no external LLM calls by default. Agent recommendations do not mutate projects.

## Verification and honest limits

Validate domain math, forbidden access, invalid time entries, concurrent changes, report failure fallbacks, build/type checks and browser flows. SQL tests must check cross-tenant RLS, audit immutability, and role changes. Document any tests that could not run. Encryption in transit and at rest needs infrastructure configuration; include operational prerequisites and a control matrix, not claims of certification. Free hosting is for demonstration; production reliability and compliance cannot be guaranteed at zero cost.
