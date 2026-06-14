# Building the Docker Images

This guide explains how to build the images yourself from source.

---

## Repository Structure

```
.
├── bot/                        # Discord bot (Python)
│   ├── core/                   # Bot client, config, database helpers
│   ├── features/
│   │   └── logging/            # Logging feature (cog + event handlers)
│   │       └── handlers/       # One file per event category
│   ├── main.py                 # Entry point
│   └── requirements.txt
│
├── web/                        # Admin web API (Python FastAPI)
│   ├── core/                   # App factory, config, DB, session
│   ├── features/
│   │   ├── auth/               # Discord OAuth2
│   │   ├── guilds/             # Guild listing + channel listing
│   │   ├── config/             # Bot configuration per guild
│   │   └── stats/              # Server statistics
│   ├── main.py                 # Uvicorn entry point
│   └── requirements.txt
│
├── artifacts/dashboard/        # Admin dashboard (React + Vite)
│   └── src/                    # Frontend source
│
├── lib/                        # Shared TypeScript libraries (codegen)
│
├── Dockerfile.bot              # Bot image
├── Dockerfile.web              # Web image (builds React + bundles FastAPI)
├── docker-compose.yml          # Local development stack
├── .env.example                # Environment variable template
├── .gitlab-ci.yml              # GitLab CI/CD pipeline
└── docs/                       # This documentation
```

---

## Feature-Based Architecture

### Bot (`bot/features/`)

Each moderation feature is a **discord.py Cog** in its own directory:

```
bot/features/
└── logging/
    ├── __init__.py
    ├── cog.py          ← registers all listeners, dispatches logs
    └── handlers/
        ├── members.py  ← ban, unban, kick, join, leave, timeout, nickname, roles
        ├── messages.py ← message delete, message edit
        ├── roles.py    ← role create, delete, update
        ├── channels.py ← channel update, permissions update
        ├── voice.py    ← voice move, disconnect
        └── server.py   ← server update, invite create
```

To add a new feature:
1. Create `bot/features/<name>/cog.py` with a Cog class.
2. Register it in `bot/core/bot.py` by adding to the `extensions` list.

### Web API (`web/features/`)

Each domain is a **FastAPI router** in its own directory:

```
web/features/
├── auth/    ← Discord OAuth2 (login, callback, /me, logout)
├── guilds/  ← Guild list, guild detail, channel list, log list
├── config/  ← GET/PUT guild config (log channel mappings)
└── stats/   ← Guild stats, member history, message history
```

To add a new feature:
1. Create `web/features/<name>/router.py`.
2. Register the router in `web/core/app.py`.

---

## Building Locally

### Prerequisites

- Docker 24+
- Docker Compose v2

### Build the bot image

```bash
docker build -f Dockerfile.bot -t modbot-bot:local .
```

### Build the web image (includes React build)

```bash
docker build -f Dockerfile.web -t modbot-web:local .
```

> The web Dockerfile is a multi-stage build:
> 1. **frontend-build** — installs pnpm, builds the React/Vite app
> 2. **python-deps** — installs Python dependencies
> 3. **final** — copies the static files + Python source, runs uvicorn

### Run the full stack

```bash
cp .env.example .env
# Edit .env with your values
docker compose up -d
```

---

## Image Details

### `Dockerfile.bot`

| Stage | Base | Purpose |
|---|---|---|
| `base` | `python:3.12-slim` | System deps (gcc, libpq-dev) |
| `deps` | `base` | Install Python packages |
| `final` | `python:3.12-slim` | Clean runtime image, non-root user |

**Entry point:** `python -m bot.main`  
**Exposed ports:** None (bot uses outbound WebSocket to Discord only)

### `Dockerfile.web`

| Stage | Base | Purpose |
|---|---|---|
| `frontend-build` | `node:22-slim` | Build React app with pnpm |
| `python-deps` | `python:3.12-slim` | Install Python packages |
| `final` | `python:3.12-slim` | FastAPI + static React files |

**Entry point:** `uvicorn web.main:app --host 0.0.0.0 --port 8000`  
**Exposed port:** `8000`

---

## Adding the Bot Token to Your Image

**Never bake secrets into the image.** Always pass them at runtime via:
- `--env-file .env`
- `-e DISCORD_TOKEN=...`
- Docker secrets (Swarm)
- Kubernetes secrets

---

## Database Migrations

The web server creates all required tables on first startup via `web/core/database.py → _ensure_schema()`. No manual migration step is needed.

Tables created:
- `guild_configs` — per-guild bot configuration
- `log_entries` — audit log history
- `member_events` — member join/leave history
- `message_stats` — message count aggregates by day
