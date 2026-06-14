# Discord Moderation Bot

A self-hostable Discord moderation bot with a web-based admin dashboard. Written in Python, packaged with Docker, and deployable with a single `docker compose up`.

---

## Features

- **Comprehensive event logging** — 23 event types including bans, kicks, timeouts, message edits/deletes, voice moves, role changes, and more
- **Per-server log channel configuration** — route each event type to its own channel, or use a single fallback channel
- **Web admin dashboard** — log in with Discord, manage multiple servers, view live stats
- **Server overview** — member join/leave charts, message activity graphs, recent audit log feed
- **Slash commands** — ready to be extended with moderation commands
- **Docker-native** — two images (`bot` and `web`) that can be pulled directly from the registry

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/your-username/modbot.git
cd modbot

# 2. Configure environment
cp .env.example .env
# Edit .env with your Discord credentials

# 3. Start
docker compose up -d

# 4. Open the dashboard
open http://localhost:8000
```

See [docs/USAGE.md](docs/USAGE.md) for the full setup guide.

---

## Documentation

| Document | Description |
|---|---|
| [docs/USAGE.md](docs/USAGE.md) | Running the bot from published Docker images |
| [docs/BUILDING.md](docs/BUILDING.md) | Building images locally, project structure |
| [docs/PIPELINE.md](docs/PIPELINE.md) | GitLab CI/CD pipeline reference |

---

## Architecture

```
┌─────────────────────────┐     ┌──────────────────────────┐
│   Discord Moderation    │     │    Admin Dashboard       │
│       Bot (Python)      │     │   Web + API (Python)     │
│                         │     │                          │
│  discord.py + asyncpg   │     │  FastAPI + React/Vite    │
│                         │     │  Discord OAuth2          │
└────────────┬────────────┘     └──────────────┬───────────┘
             │ writes events                   │ reads/writes config
             ▼                                 ▼
      ┌──────────────────────────────────────────┐
      │            PostgreSQL 16                 │
      │                                          │
      │  guild_configs  log_entries              │
      │  member_events  message_stats            │
      └──────────────────────────────────────────┘
```

---

## Supported Log Events

| Event | Description |
|---|---|
| Member ban/unban | Tracks all bans and unbans |
| Timeout add/remove | Timeout given or removed |
| Member kick | Kick events |
| Member join/leave | Server membership changes |
| Nickname change | Nickname edits |
| Role add/remove | Roles given to or removed from members |
| Voice move/disconnect | Voice channel changes |
| Message delete/edit | Message audit trail |
| Role create/delete/update | Server role changes |
| Channel update/permissions | Channel and permission changes |
| Invite create | New invite links |
| Command used | Slash command usage |
| Server update | Server setting changes |

---

## Project Structure

```
modbot/
├── bot/                    # Python Discord bot
│   ├── core/               # Bot client, config, database
│   └── features/
│       └── logging/        # Logging cog + handlers
├── web/                    # Python FastAPI admin API
│   ├── core/               # App, config, database, session
│   └── features/
│       ├── auth/           # Discord OAuth2
│       ├── guilds/         # Guild management
│       ├── config/         # Bot configuration
│       └── stats/          # Statistics
├── artifacts/dashboard/    # React admin dashboard (Vite)
├── Dockerfile.bot          # Bot Docker image
├── Dockerfile.web          # Web Docker image
├── docker-compose.yml      # Local development stack
├── .env.example            # Environment variable template
├── .gitlab-ci.yml          # GitLab CE CI/CD pipeline
└── docs/                   # Documentation
```

---

## Environment Variables

See [.env.example](.env.example) for a complete list with descriptions.

---

## License

MIT
