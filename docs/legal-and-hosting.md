# Legal, licensing, and hosting decisions

Licensing and alternative-hosting sources reviewed on **27 September 2026**; GitHub Pages scope and availability rechecked on **28 September 2026**. Terms and quotas can change; recheck them before each deployment. This is an engineering release checklist, not a legal opinion or a guarantee against claims.

## What can be shared

Silicon Portfolio is an original implementation of common project and portfolio management workflows. It is not affiliated with, endorsed by, or a certified replacement for Sciforma. Do not copy another product's source, screenshots, logos, text, proprietary templates, customer exports, or distinctive interface assets. Describe demonstrated capabilities precisely; do not claim complete feature parity without an independently maintained acceptance matrix.

The demo uses fictional programs, people, costs, schedules, and performance figures. Keep the public build synthetic. Browser storage, downloaded reports, source maps, Git history, screenshots, and build logs are all possible disclosure paths.

The user explicitly approved the **public source repository [Mayank-khator/silicon-portfolio](https://github.com/Mayank-khator/silicon-portfolio)** and public synthetic demonstration. The expected Pages address is [mayank-khator.github.io/silicon-portfolio](https://mayank-khator.github.io/silicon-portfolio/); the first deployment is pending in the [deployment record](deployment.md). Public visibility includes the full backend source, while the hosted artifact contains the static frontend. Source visibility does not expose any permission to use confidential employer/customer data.

Before publishing employer-related work, establish who owns the code and permission to release it: check employment/invention-assignment agreements, use of employer time/equipment, confidentiality obligations, contractor contributions, and internal open-source policy. Use an approved repository owner and account. These facts cannot be determined from this codebase. A private repository reduces exposure but does not settle ownership. Have qualified counsel review unresolved ownership, trademark, patent, customer-contract, or distribution questions.

## Open-source inventory

These are upstream project licenses, not a complete software bill of materials. Verify the **exact locked package versions, container images, transitive dependencies, fonts, icons, plugins, and copied components** in the release. Keep required copyright, license, and NOTICE files with distributions. A license selected for this application's original code does not replace dependency licenses.

| Component | Upstream license | Release consideration |
| --- | --- | --- |
| [Next.js](https://github.com/vercel/next.js/blob/canary/license.md) | MIT | Preserve required notices; Next.js licensing is separate from Vercel hosting terms. |
| [React](https://github.com/react/react/blob/main/LICENSE) | MIT | Preserve required notices. |
| [Tailwind CSS](https://github.com/tailwindlabs/tailwindcss/blob/main/LICENSE) | MIT | Paid templates/assets are separate products and are not included by this license. |
| [shadcn/ui](https://github.com/shadcn-ui/ui/blob/main/LICENSE.md) | MIT | Retain notices for component source actually copied; review underlying primitives separately. |
| [Radix Primitives](https://github.com/radix-ui/primitives/blob/main/LICENSE) | MIT | Preserve notices for the dialog and slot packages used by this frontend. |
| [Lucide icons](https://lucide.dev/license) | ISC, with identified Feather-derived portions under MIT | Retain the full upstream license/attribution for redistributed icons. |
| [FastAPI](https://github.com/fastapi/fastapi/blob/master/LICENSE) | MIT | Dependencies have their own notices. |
| [Kong OSS](https://github.com/Kong/kong/blob/master/LICENSE) | Apache-2.0 | Preserve license/required notices and identify modifications; Enterprise plugins/services require separate review. |
| [RabbitMQ server/core plugins](https://github.com/rabbitmq/rabbitmq-server/blob/main/LICENSE) | MPL-2.0, with some separately licensed files | When distributing covered software, satisfy the applicable source-availability and notice obligations; review modified covered files and plugins. [MPL terms](https://www.mozilla.org/en-US/MPL/2.0/). |
| [Supabase repository](https://github.com/supabase/supabase/blob/master/LICENSE) | Apache-2.0 | Supabase comprises multiple components; review each component and client package. Hosted Supabase also has service terms. |
| [PostgreSQL](https://www.postgresql.org/about/licence/) | PostgreSQL License | Preserve its copyright and license notices. |
| [LangChain](https://github.com/langchain-ai/langchain/blob/master/LICENSE) | MIT | Provider integrations and hosted tracing services have separate terms. |
| [Ollama runtime](https://github.com/ollama/ollama/blob/main/LICENSE) | MIT | The runtime license does not license downloaded model weights. |

Record each model's publisher, exact model/version or digest, license, acceptable-use restrictions, commercial-use terms, and redistribution conditions before enabling it. Do not label every downloadable model “open source.” A local runtime alone does not establish permission to use or redistribute a model. The deterministic demo insights do not require model weights or a paid API.

“Open-source application” and “free hosted service” are different claims. GitHub, Sites, Cloudflare, and Supabase hosted offerings are governed by their applicable service terms; they are not an entitlement to unlimited free infrastructure. Self-hosting still requires hardware, electricity, administration, and backups.

For a fully open-source container runtime path, use Linux Docker Engine and Compose and review their Apache-2.0 licenses. **Docker Desktop has separate subscription terms**: enterprise commercial use may require payment, even though it includes open-source Engine. Do not assume a personal Desktop installation is licensed for employer use. This repository does not require purchasing Desktop. [Engine licensing](https://docs.docker.com/engine/), [Compose license](https://github.com/docker/compose/blob/main/LICENSE), [Docker plan eligibility](https://www.docker.com/pricing/faq/).

## Hosting choice

The selected delivery path is **GitHub Pages from the authorized public repository**. The artifact is an interactive synthetic project showcase: workspace/profile, project/task, resource/allocation and time edits persist in the visitor's browser. It does not offer a shared commercial SaaS or run the backend services. GitHub describes Pages as project-site hosting; treating this bounded demonstration as a project showcase is a scope assessment, not vendor approval or blanket legal clearance. [Pages overview](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages). The earlier Sites preview is superseded; the alternatives below are reference options only, not additional deployments.

| Option | Appropriate use here | Current constraints |
| --- | --- | --- |
| Cloudflare Pages Free | Portable static demonstration option | 500 builds/month, one concurrent build, 20-minute build timeout, 20,000 files, 25 MiB maximum asset. Functions consume separate Workers quotas. [Pages limits](https://developers.cloudflare.com/pages/platform/limits/). |
| Supabase Free | Optional connected prototype with synthetic data | Two free projects; 500 MB database/project, 1 GB file storage, 5 GB egress. Low activity over seven days can cause pausing. No managed automatic backup entitlement on Free; maintain exports. [Billing](https://supabase.com/docs/guides/platform/billing-on-supabase), [pausing](https://supabase.com/docs/guides/platform/free-project-pausing), [backups](https://supabase.com/docs/guides/platform/backups). |
| GitHub Free | Source, issues, and CI | Public/private repositories are supported, with different feature sets and CI quotas. Set spending controls before using billable compute or extra storage. [GitHub plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans). |
| GitHub Pages | Selected synthetic project showcase | Public repositories work with GitHub Free; private-source Pages needs an eligible paid plan. Business/e-commerce and commercial SaaS hosting are restricted. Reassess any move from demonstration to operating a business service. [Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits). |
| Vercel Hobby | Not the default for an employer/business demonstration | Hobby is restricted to personal, noncommercial use in its plan documentation. Use a permitted plan or obtain vendor clarification for the actual use case. No paid plan is provisioned here. [Hobby plan](https://vercel.com/docs/plans/hobby), [terms](https://vercel.com/legal/terms). |

Cloudflare's self-service agreement accommodates entity accounts but does not provide unconditional legal clearance: an account representative needs authority, acceptable-use and service-specific terms apply, and Free Services can end. It also restricts credit-card collection on free properties and PHI transmission without written consent. This synthetic demo does neither. [Cloudflare agreement](https://www.cloudflare.com/terms/). Review data rights, privacy obligations, applicable processing agreements, subprocessors, retention, and regions before connecting real data. [Supabase terms](https://supabase.com/terms).

The [GitHub Actions workflow](../.github/workflows/pages.yml) automatically builds and publishes on `main` pushes, with manual dispatch also available. `pnpm build:pages` forces demo mode, clears API/Supabase settings and exports `apps/web/out` for `/silicon-portfolio`. GitHub Pages does not deploy the Compose stack. Shared authentication/storage, Python services, RabbitMQ and model inference still require a separately configured host; their source is included without claiming those services are running.

Do not purchase domains, subscriptions, or add-ons for this delivery. Keep optional portable services on their documented free plans, retain the local build as a presentation fallback, and confirm successful publication before sharing its URL. No production availability commitment is established. Revalidate account entitlement, usage and terms before enabling accounts, uploads, analytics, database access, or external AI.

## Semiconductor and regulated-work boundaries

Do not put real RTL, netlists, GDS/layouts, process recipes, PDKs, foundry files, test vectors, security vulnerabilities, customer roadmaps, controlled technical data, or employee information into the public demo or cloud AI. Classify actual data and have the organization's export-control owner review jurisdiction, classification, recipients, support access, and hosting location before a connected pilot. US EAR controls can concern releases of controlled technology or source code; applicability depends on facts, not simply whether a repository is private. [BIS EAR Part 734](https://www.bis.gov/regulations/ear/734).

NPI gates, audit history, and traceability fields are workflow aids. They do not establish ISO 26262 qualification, medical-device QMS validation, or compliant electronic signatures. A regulated deployment needs its own intended-use assessment, validated processes, controlled evidence, retention, identity/signature design, and quality approval. [ISO 26262 overview](https://www.iso.org/standard/68383.html), [FDA Part 11 scope guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/part-11-electronic-records-electronic-signatures-scope-and-application).

Release evidence to retain: approved ownership/repository decision; dependency and model license inventory; synthetic-data review; vendor plan/terms record; and the security acceptance evidence in [security-readiness.md](security-readiness.md). None is a promise of legal immunity or certification.
