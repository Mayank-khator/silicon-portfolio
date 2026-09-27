# Silicon Portfolio Implementation Plan

> **For agentic workers:** Use bounded parallel tasks with independent file ownership; root integrates and verifies.

**Goal:** Deliver a working synthetic NPI management demo and documented microservice foundation.
**Architecture:** Next.js demo/connected adapters, four FastAPI services, Supabase RLS and Realtime, Kong and RabbitMQ.
**Tech Stack:** Next.js, React, Tailwind, shadcn-style Radix primitives, FastAPI, Supabase, RabbitMQ, Kong, Docker.
**Spec:** ../specs/2026-09-27-silicon-ppm-design.md

## Global constraints

- No real semiconductor IP, personal data, paid provisioning or external AI calls in the demo.
- No service-role key in frontend. Supabase authenticated user JWT is used for data calls.
- Keep code repository private by default; management demo access requires an explicit audience choice.
- User has authorized building and publishing a reviewable demo. Proceed with reversible implementation without repeated design approvals.

## Review focus

- Cross-tenant references and client-controlled role/tenant escalation.
- Concurrent edits and invalid phase transitions.
- Submitted timesheet edits, duplicate entries and hours outside valid bounds.
- Demo data never accidentally masquerades as shared production data.
- External model failure, unverifiable forecasts and public hosting limits.

## Tasks

1. Database owner: create migrations, synthetic seed and SQL security tests; enforce composite tenant references, role policies, audit triggers and version checks.
2. Backend owner: test domain validation and agent calculations before implementation; create four FastAPI services, shared authenticated Supabase access, outbox worker, Dockerfiles and API instructions. Run complete service test suite.
3. Root frontend: implement Next.js shell and demo state adapter, original polished portfolio UI, all domain views, Supabase Auth/Realtime adapter and mutation error handling. Validate meaningful domain math and browser operations.
4. Root orchestration: wire service ports 8001–8004 behind Kong 8000, RabbitMQ, optional local Ollama, environment templates, healthchecks and README. Document Supabase local CLI prerequisites separately.
5. Research owner: verify free hosting and license/compliance constraints from primary sources; write practical legal and security readiness notes.
6. Root verification and delivery: run build, type check, service tests, SQL checks where feasible, inspect browser, fix critical issues; prepare private GitHub repository when authentication is available, publish demo and record remaining deployment requirements.
