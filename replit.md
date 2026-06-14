# Discord Moderation Bot

A self-hostable Discord moderation bot with a web admin dashboard. Written in Python (bot + FastAPI web API), packaged with Docker for public publishing.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the Node.js API server (port from $PORT, routed at `/api`)
- `pnpm --filter @workspace/dashboard run dev` — run the React dashboard (Vite dev server)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- **Node.js API server**: Express 5, Drizzle ORM (used in Replit dev)
- **Python Discord bot**: discord.py 2.4, asyncpg (Docker production)
- **Python web API**: FastAPI, uvicorn, asyncpg (Docker production)
- **Frontend**: React 18 + Vite, Tailwind CSS, shadcn/ui, Recharts, wouter
- **DB**: PostgreSQL + Drizzle ORM (Node.js) / asyncpg (Python)
- **Auth**: Discord OAuth2 (HMAC-signed cookie sessions)
- **Codegen**: Orval (from OpenAPI spec → React Query hooks + Zod schemas)

## Where things live

```
bot/                    ← Python Discord bot
  core/                 ← BotConfig, ModerationBot, database helpers
  features/logging/     ← LoggingCog (all 23 event types)
    handlers/           ← members, messages, roles, channels, voice, server

web/                    ← Python FastAPI web server (Docker production)
  core/                 ← app factory, config, database, session
  features/             ← auth, guilds, config, stats routers

artifacts/
  api-server/           ← Node.js Express API (Replit dev, talks to PostgreSQL)
    src/routes/         ← health, auth, guilds (+ bot invite)
  dashboard/            ← React admin dashboard
    src/pages/          ← landing, server-list, server-overview, server-settings
    src/components/     ← server-layout sidebar component

lib/
  db/src/schema/        ← Drizzle schema: guild_configs, log_entries, member_events, message_stats
  api-spec/             ← OpenAPI YAML spec (source of truth for codegen)
  api-client-react/     ← Generated React Query hooks (do not edit manually)
  api-zod/              ← Generated Zod schemas (do not edit manually)

Dockerfile.bot          ← Python bot Docker image
Dockerfile.web          ← Python FastAPI + React static files image
docker-compose.yml      ← Full stack: postgres + bot + web
.gitlab-ci.yml          ← GitLab CE pipeline (build + publish on tag push)
docs/                   ← USAGE.md, BUILDING.md, PIPELINE.md
```

Required env: `DATABASE_URL`, `SESSION_SECRET`, `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_TOKEN`

## Architecture decisions

- **Dual backend**: Node.js API server (for Replit dev environment) + Python FastAPI (for Docker production). Both talk to the same PostgreSQL schema.
- **HMAC cookie sessions**: No session table needed — sessions are signed with `SESSION_SECRET` and validated on each request. 7-day expiry.
- **Single-table audit log**: All 23 event types write to `log_entries`. Stats derived from `member_events` and `message_stats` aggregates.
- **Feature-based cog structure**: Each event category (members, messages, roles, channels, voice, server) has its own handler file. Adding a new feature = new `bot/features/<name>/cog.py`.
- **Contract-first API**: OpenAPI spec in `lib/api-spec/openapi.yaml` is the source of truth. React hooks and Zod schemas are generated from it — never written by hand.

## Product

- Landing page with Discord OAuth login + "Add to Server" CTA
- Server list showing which servers have the bot active vs not
- Server overview: member flow chart (30d), messages chart (7d), recent audit log feed
- Server settings: per-event-type log channel selector for all 23 event types, grouped by category

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- **Always run codegen after spec changes**: `pnpm --filter @workspace/api-spec run codegen`. Stale generated files cause TS errors.
- **Push DB schema after schema changes**: `pnpm --filter @workspace/db run push`.
- **queryKey is required** in generated React Query hooks — always pass the `getXxxQueryKey()` function along with other options.
- **GitLab CI requires `CI_REGISTRY_TOKEN`** set manually in GitLab → Settings → CI/CD → Variables (see docs/PIPELINE.md).
- **Python Docker images need `DISCORD_TOKEN`, `DATABASE_URL`, `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `SESSION_SECRET`** — never bake these into images.

## Pointers

- See `docs/USAGE.md` for running from published Docker images
- See `docs/BUILDING.md` for building images locally and project structure detail
- See `docs/PIPELINE.md` for GitLab CI/CD pipeline reference
- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
