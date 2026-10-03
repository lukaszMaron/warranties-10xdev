---
project: warranties-10xdev
researched_at: 2026-10-03
recommended_platform: Fly.io
runner_up: Railway
context_type: mvp
tech_stack:
  language: Python
  framework: FastAPI
  runtime: CPython >=3.11
  package_manager: uv
  database: not selected
---

## Recommendation

**Deploy on Fly.io.** It is the best fit for the stated combination of a continuously running background worker, global users, and cost sensitivity: Fly has no platform fee, supports always-on Machines in multiple regions, and bills compute per second. A small API in three regions plus one 512 MB worker has an illustrative compute floor of about $14.76/month in the cheapest regions, before regional price differences, egress, storage, or a database. This recommendation assumes the database remains undecided; Fly Managed Postgres starts at $38/month and could change the cost comparison.

The platform research used the root `pyproject.toml` as the stack source because the default root `context/foundation/tech-stack.md` and `prd.md` are absent. The root code is still a greeting stub, not a deployable FastAPI application; create an ASGI entrypoint before deployment.

## Platform Comparison

Scores: Pass = 2, Partial = 1, Fail = 0. Runtime compatibility and the always-on worker requirement were applied as hard filters before scoring. Final ordering then considers the interview answers: minimize cost first, while still favoring global routing. Traffic volume is assumed to be 10k–100k requests/month; at that level always-on compute dominates request charges.

| Platform | CLI-first | Managed / serverless | Agent-readable docs | Stable deploy API | MCP / integration | Base score | Shortlist status |
|---|---|---|---|---|---|---:|---|
| Cloudflare Workers + Pages | — | — | — | — | — | — | Excluded: event-driven Workers/Workflows and on-demand Containers do not provide the required continuously running worker process. |
| Vercel | — | — | — | — | — | — | Excluded: Python/FastAPI is supported, but there is no always-on worker service. WebSockets are public beta and bounded by function duration. |
| Netlify | — | — | — | — | — | — | Excluded: functions are ephemeral; Background Functions stop after 15 minutes. |
| Fly.io | Pass | Pass | Pass | Pass | Partial | 9/10 | Eligible; ranked first after cost and global-region preferences. |
| Railway | Pass | Pass | Pass | Partial | Pass | 9/10 | Eligible; ranked second. |
| Render | Pass | Pass | Pass | Pass | Pass | 10/10 | Eligible; ranked third after global-latency weighting. |

### Cloudflare Workers + Pages — filtered out

Cloudflare Python Workers support FastAPI and offer global execution, Queues, Workflows, and Durable Objects. However, Queues and Workflows are event-driven, and Containers are started on demand and can stop after inactivity or during rollouts; these are not a substitute for the requested always-on worker process. Python packages require WebAssembly-compatible wheels, and the Python package ecosystem is still described as early-stage. Workers Free includes limited daily usage; Workers Paid has a $5/month minimum. Sources: [Python Workers and packages](https://developers.cloudflare.com/workers/languages/python/), [Container lifecycle](https://developers.cloudflare.com/containers/concepts/architecture/), [Workflows](https://developers.cloudflare.com/workflows/), [pricing](https://developers.cloudflare.com/workers/platform/pricing/). Checked 2026-10-03.

### Vercel — filtered out

Vercel supports Python ASGI applications including FastAPI, with Hobby at $0 for personal, non-commercial use and Pro at $20/month. It cannot keep a conventional background worker running between invocations. WebSocket support is **public beta** (launched June 22, 2026; Python support followed July 23, 2026) and each connection closes at the function's maximum duration: 300 seconds on Hobby, 800 seconds on Pro, or up to 1,800 seconds for supported runtimes in an extended-duration **beta**. Sources: [Python runtime](https://vercel.com/docs/functions/runtimes/python), [WebSocket limits and beta status](https://vercel.com/kb/guide/do-vercel-serverless-functions-support-websocket-connections), [pricing](https://vercel.com/pricing), [Vercel MCP](https://vercel.com/docs/agent-resources/vercel-mcp). Checked 2026-10-03.

### Netlify — filtered out

Netlify has CLI deploys, global CDN, managed Database/Blobs, an official MCP server, and a free plan with a 300-credit limit. Its functions are ephemeral; Background Functions run for at most 15 minutes and cannot serve a process that must remain alive between jobs. Sources: [Functions model](https://docs.netlify.com/build/functions/overview/), [Background Functions limit](https://docs.netlify.com/build/functions/background-functions/), [pricing](https://www.netlify.com/pricing/), [CLI docs](https://docs.netlify.com/cli/get-started/). Checked 2026-10-03.

### Fly.io — eligible, score 9/10

`flyctl` covers deploy, status, releases, logs, secrets, and Machines; Fly documents scoped deploy and read-only tokens plus GitHub Actions. The platform manages Machines while allowing persistent processes and region placement. Documentation is Markdown/MDX with `llms.txt`. `fly deploy` is deterministic; a rollback can redeploy a retained prior image, although the current `fly releases` command documents release listing rather than a dedicated rollback command. No first-party Fly infrastructure MCP was found; the GitHub Action focuses on deploy, so MCP/integration scores Partial. Sources: [FastAPI guide](https://docs.fly.io/python/frameworks/fastapi), [pricing](https://docs.fly.io/about/pricing), [autostop/autostart](https://docs.fly.io/apps/autostop-autostart), [CLI automation](https://docs.fly.io/flyctl/integrating), [logs](https://docs.fly.io/flyctl/cmd/fly_logs). Checked 2026-10-03.

Fly has no free tier or monthly platform fee. The smallest always-on `shared-cpu-1x` Machine with 512 MB RAM is $3.69 per 30 days in the lowest-priced regions; a 256 MB Machine is $2.19 but is not a prudent sizing assumption for an API plus background work. Two 512 MB Machines (API and worker) cost about $7.38/month in one low-cost region. Three API Machines plus one worker cost about $14.76 at that same floor; non-US regions, memory needs, egress, and storage raise the bill. Managed Postgres Basic starts at $38/month, making database choice the largest unresolved cost.

### Railway — eligible, score 9/10

Railway supports FastAPI services, persistent containers, managed PostgreSQL, volumes, and S3-compatible buckets. The CLI supports `railway up`, JSON output, log streaming, service variables, and `railway redeploy`; its official MCP server is installable for GitHub Copilot and other agents. Docs are available as Markdown. Multi-region replicas route requests to a nearby region, but Railway does not support sticky sessions; database calls may still cross regions. The deploy API/CLI is deterministic, but `railway redeploy` targets the latest deployment, so the historical rollback path is less direct than Fly's retained-image redeploy or Render's rollback endpoint. Sources: [FastAPI guide](https://docs.railway.com/guides/fastapi), [pricing](https://railway.com/pricing), [multi-region scaling](https://docs.railway.com/reference/scaling), [CLI](https://docs.railway.com/reference/cli-api), [logs](https://docs.railway.com/cli/logs), [MCP](https://docs.railway.com/cli/mcp). Checked 2026-10-03.

Railway Hobby is $5/month and includes $5 of monthly usage credit. Usage is metered per second: CPU is about $20/vCPU-month and memory about $10/GB-month. Two always-on 0.25-vCPU / 0.5-GB services (API and worker) are roughly $20/month in resource usage before a database; additional regional replicas and database usage add cost. The plan fee covers the included credit, and usage above that is billed. This is an illustrative estimate, not a quote.

### Render — eligible, score 10/10

Render provides persistent Python web services and continuously running background workers, plus a CLI with non-interactive JSON/YAML/text modes, deploy commands that can wait for completion, log queries, and a published API rollback endpoint. It has official agent skills and an MCP server; the separate docs-search MCP is explicitly **experimental**. Documentation is available as Markdown and `llms.txt`. The important global constraint is that a dynamic service runs in a selected region; the global CDN does not make FastAPI execution global. Sources: [FastAPI deployment](https://render.com/docs/deploy-fastapi), [background workers](https://render.com/docs/background-workers), [WebSockets](https://render.com/docs/websocket), [pricing](https://render.com/pricing), [CLI](https://render.com/docs/cli), [rollbacks](https://render.com/docs/rollbacks), [agent integration](https://render.com/docs/llm-support). Checked 2026-10-03.

Render's Hobby workspace fee is $0. A 512 MB web service and a 512 MB background worker are each about $7/month; the smallest paid Postgres plan is about $6/month, for an illustrative $20/month before bandwidth, storage, or higher resource needs. Free compute is unsuitable for an always-on worker because free web services can spin down. Render is the clearest low-cost, single-region option, but it does not meet the global-latency preference as well as Fly or Railway.

### Shortlisted Platforms

#### 1. Fly.io (Recommended)

Fly ranks first after applying the stated preferences rather than by raw criteria total: it combines always-on workers, regional Machines, Anycast routing, and a low compute-only floor without a fixed platform fee. It keeps global API latency and cost in view, provided the database is chosen separately and the worker is not accidentally stopped. The $38/month Managed Postgres price is the main caveat; using it changes the total substantially.

#### 2. Railway

Railway is the closest alternative if integrated PostgreSQL/object storage and first-party MCP matter more than the lowest compute bill. Its nearest-region replica routing suits global requests, but each replica consumes the service's full resource plan, there is no sticky-session support, and a central database can remain the latency bottleneck. A $5 Hobby plan includes $5 usage credit, not unlimited always-on compute.

#### 3. Render

Render offers the most straightforward, predictable managed setup and an illustrative $20/month API + worker + smallest paid Postgres combination. Its CLI, published rollback API, MCP, and agent skills are strong. The tradeoff is serving the dynamic API from one selected region, which is a weaker fit for the stated global-latency requirement.

## Anti-Bias Cross-Check: Fly.io

### Devil's Advocate — Weaknesses

1. Managed Postgres starts at $38/month, several times the API/worker compute floor. An external database may reduce cost but adds another vendor, credentials, network path, and backup policy.
2. Regional API Machines do not make a single-region database global. Reads and writes still pay the database round-trip, so the perceived latency gain may be small for data-heavy pages.
3. Fly Volumes are regional, not shared or replicated. Storing receipts/PDFs on them creates a recovery and migration trap; object storage is a better fit.
4. The API and background worker need different lifecycle settings. A worker must remain running, and a duplicated scheduler across regions can execute the same job more than once.
5. Deploys replace Machines and can interrupt active connections or jobs. A retained prior image and graceful shutdown/retry behavior are necessary for practical rollback.

### Pre-Mortem — How This Could Fail

Six months after choosing Fly, the team discovers that “low cost” described only the web process. The warranty data needed a database, and Managed Postgres added $38 per month before storage; an external database would have lowered the bill but introduced separate credentials, monitoring, and backups. The API was deployed in several regions, but all writes still traveled to one primary database, so some users saw little improvement. The team added Machines in more regions and increased compute costs without first measuring a latency target. A background worker was copied into each region, so scheduled work ran more than once; queue ownership and idempotency had never been specified. PDF files were written to regional volumes, which were not shared or replicated, and a regional incident exposed the recovery gap. Finally, a deploy replaced Machines while jobs were in flight, and the team had not tested graceful shutdown or a rollback using a retained image. Each issue was individually fixable, but together they erased the early cost and speed advantage.

### Unknown Unknowns

- `fly launch` defaults HTTP apps to autostop with `min_machines_running = 0`; explicitly check the worker process group's settings and running-machine count.
- `min_machines_running` applies only in the primary region, not every region.
- Fly Volumes are region-local. Snapshot storage became billable in January 2026; Managed Postgres is a separate resource and may remain billable after deleting the app.
- Deploys replace Machines. Treat active jobs as interruptible and use SIGTERM handling, queue acknowledgements/retries, and client reconnect logic.

## Operational Story

- **Preview deploys**: Fly does not provide a turnkey per-PR preview environment. Use a separate staging app and a GitHub Actions staging deploy; keep it private or access-controlled. Production deploys should use a protected GitHub Environment with a required reviewer.
- **Secrets**: Store runtime secrets with `fly secrets set NAME=VALUE`; Fly exposes them to Machines as environment variables. Store a short-lived app-scoped deploy token in GitHub Secrets (`FLY_API_TOKEN`), created with `fly tokens create deploy -a <app> -x 720h`. Never use a personal token in CI.
- **Rollback**: List release image references with `fly releases --image -a <app>`, then redeploy a retained known-good image with `fly deploy --image <image-ref> -a <app>`. This is a new deploy, not an instant deployment-pointer switch; verify the exact image and database migration compatibility before running it.
- **Approval**: Agents may deploy to staging and read status/logs. Require a human approval gate for production deploys, primary secret rotation, deleting databases/volumes, or destructive schema changes. Use GitHub Environment protection for the production job.
- **Logs**: Use `fly logs -a <app> --json` for application logs and `fly status -a <app> --json` / `fly releases -a <app> --json` for machine and release state. Scope read-only automation with `fly tokens create readonly -o <org>`.

## Risk Register

| Risk | Source | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Managed Postgres pushes the MVP bill above the compute estimate | Research finding | High | High | Decide the database before launch; compare external managed Postgres with Fly Managed Postgres and include network, backup, and egress costs. |
| Multi-region API still waits on a single-region database | Devil's advocate | Medium | High | Start with one database primary; benchmark representative read/write flows from target regions before adding replicas. Do not promise global low latency based on edge routing alone. |
| Receipt/PDF data is stored on a regional volume and is not replicated | Unknown unknowns | Medium | High | Use an object-storage service with explicit durability and lifecycle policy; keep database rows separate from binary documents. |
| Worker is stopped, duplicated, or interrupted during a deploy | Pre-mortem | Medium | High | Give the worker its own process group/Machine with autostop disabled; use idempotent jobs, graceful SIGTERM handling, retries, and a single scheduler/leader where required. |
| Prior release image or compatible schema is unavailable during rollback | Devil's advocate | Medium | High | Preserve image references and release metadata; use backward-compatible expand/contract migrations and rehearse rollback in staging. |
| Orphaned database or volume keeps billing after app cleanup | Unknown unknowns | Low | Medium | Inventory resources before deletion; treat DB/volume deletion as a human-only action and configure budget alerts. |

## Getting Started

1. Implement a FastAPI ASGI entrypoint that exports `app`; the current root package only prints a greeting and is not deployable as an API.
2. Add a Dockerfile using the existing `uv.lock` and Python 3.11+; install dependencies with `uv sync --frozen --no-dev`, then start the app with `uv run uvicorn <module>:app --host 0.0.0.0 --port 8080`.
3. Run `fly launch --no-deploy --no-db --no-redis` to generate Fly configuration without provisioning an undecided database. Set the HTTP service port to `8080`; keep the worker as a separate process group or app.
4. Create a staging app first, set its runtime values with `fly secrets set`, and deploy with `fly deploy --remote-only`. Configure health checks and explicitly disable autostop for the worker.
5. Add a GitHub Actions deploy workflow using the `superfly/flyctl-actions/setup-flyctl` action and a short-lived app-scoped token. Protect the production Environment with a required reviewer before production deployment.

## Out of Scope

This research did not build a Docker image or Dockerfile, configure a CI/CD workflow, choose a database/object-storage vendor, or design production-scale multi-region database replication, HA, or DR.
