# Repository map

Generated source/configuration tree. Dependencies, virtual environments, private environment files and build output are excluded.

```text
silicon-ppm/
├── .openai/
│   └── hosting.json
├── apps/
│   └── web/
│       ├── app/
│       │   ├── globals.css
│       │   ├── layout.tsx
│       │   └── page.tsx
│       ├── components/
│       │   ├── ui/
│       │   │   ├── button.tsx
│       │   │   └── dialog.tsx
│       │   ├── connected-insights.tsx
│       │   ├── dashboard.tsx
│       │   ├── gantt.tsx
│       │   └── workspace.tsx
│       ├── lib/
│       │   ├── connected-data.ts
│       │   ├── domain.ts
│       │   ├── seed.ts
│       │   ├── use-portfolio.ts
│       │   └── utils.ts
│       ├── public/
│       │   └── third-party-licenses.txt
│       ├── .env.example
│       ├── Dockerfile
│       ├── components.json
│       ├── next-env.d.ts
│       ├── next.config.ts
│       ├── postcss.config.mjs
│       └── tsconfig.json
├── docs/
│   ├── superpowers/
│   │   ├── plans/
│   │   │   └── 2026-09-27-silicon-ppm.md
│   │   └── specs/
│   │       └── 2026-09-27-silicon-ppm-design.md
│   ├── database.md
│   ├── deployment.md
│   ├── legal-and-hosting.md
│   ├── repository-tree.md
│   ├── security-readiness.md
│   ├── verification.md
│   └── weekly-reports.md
├── infra/
│   ├── kong/
│   │   └── kong.yml
│   └── nginx/
│       └── default.conf
├── scripts/
│   ├── collect-licenses.mjs
│   ├── prepare-hosting.mjs
│   └── preview.mjs
├── services/
│   ├── agentic_ai/
│   │   ├── __init__.py
│   │   ├── analysis.py
│   │   └── app.py
│   ├── project_npi/
│   │   ├── __init__.py
│   │   └── app.py
│   ├── resource_time/
│   │   ├── __init__.py
│   │   └── app.py
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── config.py
│   │   ├── crud.py
│   │   ├── domain.py
│   │   ├── models.py
│   │   └── supabase.py
│   ├── user/
│   │   ├── __init__.py
│   │   └── app.py
│   ├── worker/
│   │   ├── __init__.py
│   │   ├── outbox.py
│   │   └── weekly_reports.py
│   ├── Dockerfile
│   ├── README.md
│   ├── __init__.py
│   ├── dependency-audit.json
│   ├── requirements-dev.txt
│   ├── requirements-llm.txt
│   ├── requirements.lock
│   └── requirements.txt
├── supabase/
│   ├── migrations/
│   │   └── 202609270001_initial.sql
│   ├── scripts/
│   │   └── bootstrap_demo.py
│   ├── tests/
│   │   ├── package.json
│   │   ├── pnpm-lock.yaml
│   │   ├── run.mjs
│   │   └── security.sql
│   ├── .gitignore
│   ├── config.toml
│   └── seed.sql
├── tests/
│   ├── backend/
│   │   ├── test_api.py
│   │   ├── test_domain.py
│   │   ├── test_weekly_reports.py
│   │   └── test_worker.py
│   └── frontend/
│       ├── connected-data.test.ts
│       └── domain.test.ts
├── .dockerignore
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── THIRD_PARTY_NOTICES.md
├── docker-compose.yml
├── package.json
├── pnpm-lock.yaml
└── pnpm-workspace.yaml
```
