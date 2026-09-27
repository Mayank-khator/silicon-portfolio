# Deployment record — 2026-09-27

**Public management demo:** [Silicon Portfolio](https://silicon-portfolio-npi-2026.khatormayank94.chatgpt.site)

Sites reported deployment `appgdep_6ab90e7aa04c819185c5d5aac4e728b7` succeeded at 12:40 UTC. The user explicitly approved access for anyone with the link. The published static artifact was packaged from source commit `b6c5189123c664848daed8163eee3f01b650a503`; later documentation-only commits record this deployment.

The public site includes only synthetic data. Each browser has independent local storage; this is not a shared or authenticated enterprise deployment. No real IP, employee timesheets, service-role key, cloud LLM key or backend service is included in the hosted artifact. No paid infrastructure was provisioned. Hosting remains subject to the account's Sites availability/terms; Cloudflare Pages is documented as a portable free-tier option.

## GitHub status

Authenticated account: `Mayank-khator`. Target: a **private** repository named `silicon-portfolio`.

Both GitHub GraphQL and REST rejected creation with `Resource not accessible by personal access token` / HTTP 403. No GitHub repository was created or pushed. The local repository is committed and ready. Create an empty private repository without a README, grant the CLI token access to it with Contents read/write, then run:

```sh
git remote add origin https://github.com/Mayank-khator/silicon-portfolio.git
git push -u origin main
```

If `origin` already exists, inspect it rather than adding or replacing it blindly. A private repository link is only accessible to authorized collaborators. Do not make the code public without reviewing employer/IP ownership.

## Rebuild and republish

`pnpm build` creates `apps/web/out`. The Sites adapter `node scripts/prepare-hosting.mjs` copies that verified export into root `out/`, an allowed Sites static root. Both directories are generated and Git-ignored. `.openai/hosting.json` retains the existing Site identity; reuse it instead of creating a second Site.

On this Windows machine, the Sites packaging helper requires Git Bash on PATH and GNU tar's `TAR_OPTIONS=--force-local` when the archive uses a drive-letter path. Source credentials are temporary and must be passed through stdin; never store them in this repository. Publishing uploads only the static archive, not the service code or environment files.
