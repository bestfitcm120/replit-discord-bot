# Usage Guide

This guide explains how to self-host the Discord Moderation Bot using the published Docker images.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Docker 24+ & Docker Compose v2 | `docker compose version` to verify |
| PostgreSQL 14+ | Provided automatically by docker-compose |
| A Discord Application | Created at https://discord.com/developers/applications |

---

## 1 — Create a Discord Application

1. Go to https://discord.com/developers/applications and click **New Application**.
2. Give it a name (e.g. *ModBot*), then open the **Bot** tab:
   - Click **Add Bot**.
   - Under *Privileged Gateway Intents*, enable all three: **Presence Intent**, **Server Members Intent**, **Message Content Intent**.
   - Copy the **Bot Token** — this is your `DISCORD_TOKEN`.
3. Open the **OAuth2 → General** tab:
   - Copy the **Client ID** and **Client Secret**.
   - Add a **Redirect URI**: `https://yourdomain.com/api/auth/discord/callback`
     (use `http://localhost:8000/api/auth/discord/callback` for local testing).
4. Open **OAuth2 → URL Generator** and generate an invite URL with the `bot` and `applications.commands` scopes, plus the permissions you want.

---

## 2 — Set Up Environment Variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `DISCORD_TOKEN` | Your bot token from the Bot tab |
| `DISCORD_CLIENT_ID` | OAuth2 client ID |
| `DISCORD_CLIENT_SECRET` | OAuth2 client secret |
| `DISCORD_BOT_PERMISSIONS` | Permissions integer (default: `8` = Administrator) |
| `BASE_URL` | Public URL of the dashboard, e.g. `https://dashboard.yourdomain.com` — must match the redirect URI you registered |
| `SESSION_SECRET` | A random secret: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `SECURE_COOKIES` | Set to `true` if serving over HTTPS |
| `POSTGRES_PASSWORD` | Secure password for the database |

---

## 3 — Using Published Docker Images

Instead of building locally, you can pull the images directly from the GitLab Container Registry:

```bash
# Pull the latest versions
docker pull ghcr.io/bestfitcm120/discord-moderation-bot/bot:latest
docker pull ghcr.io/bestfitcm120/discord-moderation-bot/web:latest
```

Then update `docker-compose.yml` to reference the registry images instead of building:

```yaml
bot:
  image: hcr.io/bestfitcm120/discord-moderation-bot/bot:latest
  # remove: build: ...

web:
  image: ghcr.io/bestfitcm120/discord-moderation-bot/web:latest
  # remove: build: ...
```

---

## 4 — Start the Stack

```bash
docker compose up -d
```

This starts three containers:
- **postgres** — PostgreSQL 16 database
- **bot** — Discord bot (starts listening for events immediately)
- **web** — Admin dashboard at http://localhost:8000

To follow logs:

```bash
docker compose logs -f bot
docker compose logs -f web
```

---

## 5 — Add the Bot to Your Server

1. Open the dashboard at `http://localhost:8000` (or your `BASE_URL`).
2. Click **Login with Discord**.
3. On the server list, click **Add Bot** next to any server where you have *Manage Server* permissions.

---

## 6 — Configure Log Channels

1. After adding the bot, click **Manage** on the server.
2. Open **Settings**.
3. Optionally set a **Default Log Channel** — this is the fallback for any event type without a specific channel assigned.
4. For each of the 23 event types, pick a channel from the dropdown, or leave it blank to use the default.
5. Click **Save**.

The bot will start posting logs to the configured channels immediately.

---

## Supported Log Events

| Event Key | Description |
|---|---|
| `member_ban` | Member banned |
| `member_unban` | Member unbanned |
| `member_timeout_add` | Timeout given |
| `member_timeout_remove` | Timeout removed |
| `member_kick` | Member kicked |
| `member_join` | Member joined |
| `member_leave` | Member left |
| `member_nickname_change` | Nickname changed |
| `member_role_add` | Role given to member |
| `member_role_remove` | Role removed from member |
| `member_voice_move` | Moved to a different voice channel |
| `member_voice_disconnect` | Disconnected from voice |
| `message_delete` | Message deleted |
| `message_edit` | Message edited |
| `role_create` | Role created |
| `role_delete` | Role deleted |
| `role_update` | Role updated |
| `channel_update` | Channel settings updated |
| `channel_permissions_update` | Channel permissions changed |
| `invite_create` | Server invite created |
| `command_used` | Slash command used |
| `server_update` | Server settings changed |

---

## Updating

```bash
docker compose pull   # pull new images
docker compose up -d  # restart with new images
```

---

## Data Persistence

All data is stored in the `postgres_data` Docker volume. Removing this volume will erase all log history and configurations. To back up:

```bash
docker compose exec postgres pg_dump -U modbot modbot > backup.sql
```
