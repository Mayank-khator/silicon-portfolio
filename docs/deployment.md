# GitHub deployment record — 2026-09-28

**Public repository:** [Mayank-khator/silicon-portfolio](https://github.com/Mayank-khator/silicon-portfolio). Public visibility of the full source, including services and database migrations, was explicitly authorized by the user.

**Verified live Pages URL:** [Silicon Portfolio](https://mayank-khator.github.io/silicon-portfolio/). Public access and HTTPS are enabled; no GitHub login is required to view the app. [GitHub Pages overview](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).

The [first deployment run](https://github.com/Mayank-khator/silicon-portfolio/actions/runs/36403749690) completed successfully at 09:29 UTC on 28 September 2026. It deployed application commit `5bb222373bc78d69ffc8c49647688b3fe895e087`. A subsequent documentation-only commit records this result. Browser verification loaded the public dashboard and opened both the workspace selector and profile dialog without console errors.

## What the Pages artifact runs

The static frontend is interactive: visitors can switch workspaces, create sample or empty workspaces, edit their local display profile, create/edit projects and tasks, edit engineering resources and allocations, record time, and generate deterministic draft reports. Each workspace is saved in that browser's local storage; changes synchronize between its tabs. Other visitors and devices have separate data. Clearing browser storage removes those local records.

Pages serves HTML, CSS and JavaScript. The public repository also contains the full FastAPI, Supabase, Kong, RabbitMQ and optional AI/worker source, but **Pages does not run those services**. Shared persistence, real sign-in/authorization, backend audit enforcement, live historical analysis, weekly report scheduling and model inference still need a separately provisioned connected environment. No backend, database or AI deployment is provisioned by this Pages workflow.

Use fictional data only. Profile editing is a local demo preference, not identity verification. Creating a demo workspace does not provision a tenant or invite collaborators. No paid service or subscription change is part of this delivery.

## Automatic publishing

The repository's [Pages workflow](../.github/workflows/pages.yml) runs on pushes to `main` and manual dispatch on `main`. Repository Settings → Pages uses **GitHub Actions** as the publishing source. The workflow:

1. Uses Node.js 24 and pnpm 11.19.0, installs from the frozen lockfile and runs the frontend tests.
2. Runs `pnpm build:pages`, which forces synthetic demo mode and clears API/Supabase environment settings.
3. Exports `apps/web/out` for `/silicon-portfolio` and adds `.nojekyll`.
4. Uploads only that static export and deploys it through the `github-pages` environment.

Use the [workflow runs](https://github.com/Mayank-khator/silicon-portfolio/actions/workflows/pages.yml) to inspect publishing results. Future application changes pushed to `main` use the same deployment workflow. Documentation-only commits may use `[skip ci]` to retain the currently verified artifact.

## Reproduce the project-path build

From the repository root:

```sh
pnpm install --frozen-lockfile
pnpm build:pages
```

PowerShell preview:

```powershell
$env:BASE_PATH = '/silicon-portfolio'
pnpm preview
```

Open [localhost project preview](http://127.0.0.1:3000/silicon-portfolio/). On POSIX shells use `BASE_PATH=/silicon-portfolio pnpm preview`. `BASE_PATH` can be overridden for another project path; it must match the deployed URL. `pnpm build` uses `/` unless explicitly run in Pages mode, so unset `BASE_PATH` for its local preview.

GitHub Free supports Pages from public repositories; private-source Pages requires an eligible paid plan. The authorized public repository avoids a paid-plan change. The current artifact is a synthetic project showcase; GitHub's commercial/SaaS restrictions still apply. [Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits). See [legal and hosting notes](legal-and-hosting.md) and [verification](verification.md) for scope and remaining checks.

## Superseded preview

The [27 September Sites preview](https://silicon-portfolio-npi-2026.khatormayank94.chatgpt.site) is historical and is no longer the primary delivery or publishing target. It may contain an older build. Current work is directed to GitHub Pages; this record does not claim the previous host was deleted or disabled.
