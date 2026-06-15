import { Router, Request, Response } from "express";
import { getSession } from "./auth.js";
import { db } from "@workspace/db";
import { guildConfigs, logEntries, memberEvents, messageStats } from "@workspace/db";
import { eq, desc, and, gte, sql } from "drizzle-orm";

const router = Router();

const DISCORD_API = "https://discord.com/api/v10";

type DiscordGuild = { id: string; name: string; icon: string | null; permissions: string };
type DiscordChannel = { id: string; name: string; type: number };

function getId(req: Request): string {
  return String(req.params["guildId"]);
}

async function fetchUserGuilds(accessToken: string): Promise<DiscordGuild[]> {
  const res = await fetch(`${DISCORD_API}/users/@me/guilds`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) return [];
  return res.json() as Promise<DiscordGuild[]>;
}

async function fetchBotGuildIds(): Promise<Set<string>> {
  const botToken = process.env["DISCORD_BOT_TOKEN"] ?? "";
  const res = await fetch(`${DISCORD_API}/users/@me/guilds`, {
    headers: { Authorization: `Bot ${botToken}` },
  });
  if (!res.ok) return new Set();
  const guilds = await res.json() as Array<{ id: string }>;
  return new Set(guilds.map((g) => g.id));
}

async function fetchGuildChannels(gId: string): Promise<DiscordChannel[]> {
  const botToken = process.env["DISCORD_BOT_TOKEN"] ?? "";
  const res = await fetch(`${DISCORD_API}/guilds/${gId}/channels`, {
    headers: { Authorization: `Bot ${botToken}` },
  });
  if (!res.ok) return [];
  const channels = await res.json() as DiscordChannel[];
  return channels.filter((c) => c.type === 0 || c.type === 5);
}

function iconUrl(gId: string, icon: string | null): string | null {
  return icon ? `https://cdn.discordapp.com/icons/${gId}/${icon}.png` : null;
}

function unauth(res: Response): void {
  res.status(401).json({ error: "Not authenticated" });
}

type LogEntryRow = typeof logEntries.$inferSelect;
function serializeEntry(e: LogEntryRow) {
  return {
    id: e.id,
    guildId: e.guildId,
    eventType: e.eventType,
    userId: e.userId,
    targetId: e.targetId,
    description: e.description,
    metadata: e.metadata,
    createdAt: e.createdAt?.toISOString() ?? null,
  };
}

// GET /api/guilds
router.get("/", async (req: Request, res: Response) => {
  const session = getSession(req);
  if (!session) { unauth(res); return; }

  const accessToken = session["accessToken"] as string;
  const userGuilds = await fetchUserGuilds(accessToken);
  const botIds = await fetchBotGuildIds();

  const MANAGE_GUILD = 0x20;
  const ADMIN = 0x8;
  const managed = userGuilds.filter((g) => {
    const perms = parseInt(g.permissions);
    return (perms & MANAGE_GUILD) || (perms & ADMIN);
  });

  res.json(managed.map((g) => ({
    id: g.id,
    name: g.name,
    icon: g.icon,
    iconUrl: iconUrl(g.id, g.icon),
    memberCount: 0,
    botPresent: botIds.has(g.id),
  })));
});

// GET /api/guilds/:guildId
router.get("/:guildId", async (req: Request, res: Response) => {
  const session = getSession(req);
  if (!session) { unauth(res); return; }

  const gId = getId(req);
  const botToken = process.env["DISCORD_BOT_TOKEN"] ?? "";
  const r = await fetch(`${DISCORD_API}/guilds/${gId}?with_counts=true`, {
    headers: { Authorization: `Bot ${botToken}` },
  });

  if (r.status === 403) { res.status(403).json({ error: "Forbidden" }); return; }
  if (r.status === 404) { res.status(404).json({ error: "Guild not found" }); return; }

  const g = await r.json() as { id: string; name: string; icon: string | null; approximate_member_count?: number; description?: string };
  res.json({
    id: g.id,
    name: g.name,
    icon: g.icon,
    iconUrl: iconUrl(g.id, g.icon),
    memberCount: g.approximate_member_count ?? 0,
    description: g.description ?? null,
  });
});

// GET /api/guilds/:guildId/channels
router.get("/:guildId/channels", async (req: Request, res: Response) => {
  const session = getSession(req);
  if (!session) { unauth(res); return; }
  const channels = await fetchGuildChannels(getId(req));
  res.json(channels);
});

// GET /api/guilds/:guildId/config
router.get("/:guildId/config", async (req: Request, res: Response) => {
  const session = getSession(req);
  if (!session) { unauth(res); return; }

  const gId = getId(req);
  const [config] = await db.select().from(guildConfigs).where(eq(guildConfigs.guildId, gId));
  if (!config) {
    res.json({ guildId: gId, defaultLogChannel: null, logChannels: {}, updatedAt: null });
    return;
  }
  res.json({
    guildId: config.guildId,
    defaultLogChannel: config.defaultLogChannel,
    logChannels: config.logChannels,
    updatedAt: config.updatedAt?.toISOString() ?? null,
  });
});

// PUT /api/guilds/:guildId/config
router.put("/:guildId/config", async (req: Request, res: Response) => {
  const session = getSession(req);
  if (!session) { unauth(res); return; }

  const gId = getId(req);
  const { defaultLogChannel, logChannels } = req.body as { defaultLogChannel?: string | null; logChannels?: Record<string, string | null> };

  const now = new Date();
  await db.insert(guildConfigs).values({
    guildId: gId,
    defaultLogChannel: defaultLogChannel ?? null,
    logChannels: logChannels ?? {},
    updatedAt: now,
  }).onConflictDoUpdate({
    target: guildConfigs.guildId,
    set: {
      defaultLogChannel: defaultLogChannel ?? null,
      logChannels: logChannels ?? {},
      updatedAt: now,
    },
  });

  res.json({ guildId: gId, defaultLogChannel, logChannels, updatedAt: now.toISOString() });
});

// GET /api/guilds/:guildId/stats
router.get("/:guildId/stats", async (req: Request, res: Response) => {
  const session = getSession(req);
  if (!session) { unauth(res); return; }

  const gId = getId(req);
  const since24h = new Date(Date.now() - 24 * 60 * 60 * 1000);
  const today = new Date().toISOString().split("T")[0] as string;

  const [joins24h] = await db.select({ count: sql<number>`count(*)::int` })
    .from(memberEvents)
    .where(and(eq(memberEvents.guildId, gId), eq(memberEvents.eventType, "join"), gte(memberEvents.createdAt, since24h)));

  const [leaves24h] = await db.select({ count: sql<number>`count(*)::int` })
    .from(memberEvents)
    .where(and(eq(memberEvents.guildId, gId), eq(memberEvents.eventType, "leave"), gte(memberEvents.createdAt, since24h)));

  const [msgs24h] = await db.select({ count: sql<number>`coalesce(sum(count), 0)::int` })
    .from(messageStats)
    .where(and(eq(messageStats.guildId, gId), eq(messageStats.isBot, false), gte(messageStats.statDate, today)));

  const [totalJoins] = await db.select({ count: sql<number>`count(*)::int` })
    .from(memberEvents).where(and(eq(memberEvents.guildId, gId), eq(memberEvents.eventType, "join")));
  const [totalLeaves] = await db.select({ count: sql<number>`count(*)::int` })
    .from(memberEvents).where(and(eq(memberEvents.guildId, gId), eq(memberEvents.eventType, "leave")));

  res.json({
    guildId: gId,
    totalMembers: Math.max(0, (totalJoins?.count ?? 0) - (totalLeaves?.count ?? 0)),
    membersJoinedLast24h: joins24h?.count ?? 0,
    membersLeftLast24h: leaves24h?.count ?? 0,
    messagesLast24h: msgs24h?.count ?? 0,
    onlineMembers: null,
  });
});

// GET /api/guilds/:guildId/stats/members
router.get("/:guildId/stats/members", async (req: Request, res: Response) => {
  const session = getSession(req);
  if (!session) { unauth(res); return; }

  const gId = getId(req);
  const since = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);

  const rows = await db.select({
    date: sql<string>`date(created_at)::text`,
    joins: sql<number>`count(*) filter (where event_type = 'join')::int`,
    leaves: sql<number>`count(*) filter (where event_type = 'leave')::int`,
  })
    .from(memberEvents)
    .where(and(eq(memberEvents.guildId, gId), gte(memberEvents.createdAt, since)))
    .groupBy(sql`date(created_at)`)
    .orderBy(sql`date(created_at)`);

  let running = 0;
  res.json(rows.map((r) => {
    running += r.joins - r.leaves;
    return { date: r.date, joins: r.joins, leaves: r.leaves, total: Math.max(0, running) };
  }));
});

// GET /api/guilds/:guildId/stats/messages
router.get("/:guildId/stats/messages", async (req: Request, res: Response) => {
  const session = getSession(req);
  if (!session) { unauth(res); return; }

  const gId = getId(req);
  const since = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split("T")[0] as string;

  const rows = await db.select({
    date: sql<string>`stat_date::text`,
    count: sql<number>`coalesce(sum(count), 0)::int`,
  })
    .from(messageStats)
    .where(and(eq(messageStats.guildId, gId), eq(messageStats.isBot, false), gte(messageStats.statDate, since)))
    .groupBy(messageStats.statDate)
    .orderBy(messageStats.statDate);

  res.json(rows.map((r) => ({ date: r.date, count: r.count })));
});

// GET /api/guilds/:guildId/logs
router.get("/:guildId/logs", async (req: Request, res: Response) => {
  const session = getSession(req);
  if (!session) { unauth(res); return; }

  const gId = getId(req);
  const entries = await db.select().from(logEntries)
    .where(eq(logEntries.guildId, gId))
    .orderBy(desc(logEntries.createdAt))
    .limit(50);

  res.json(entries.map(serializeEntry));
});

// GET /api/guilds/:guildId/moderation
router.get("/:guildId/moderation", async (req: Request, res: Response) => {
  const session = getSession(req);
  if (!session) { unauth(res); return; }

  const gId = getId(req);
  const filterUserId = typeof req.query["userId"] === "string" ? req.query["userId"] : null;

  const MOD_EVENTS = [
    "member_ban", "member_unban", "member_kick",
    "member_timeout_add", "member_timeout_remove", "member_warn",
  ];

  const conditions = [
    eq(logEntries.guildId, gId),
    sql`${logEntries.eventType} = ANY(${MOD_EVENTS})`,
    ...(filterUserId ? [eq(logEntries.targetId, filterUserId)] : []),
  ];

  const entries = await db.select().from(logEntries)
    .where(and(...conditions))
    .orderBy(desc(logEntries.createdAt))
    .limit(100);

  res.json(entries.map(serializeEntry));
});

// GET /api/guilds/:guildId/warnings/:userId
router.get("/:guildId/warnings/:userId", async (req: Request, res: Response) => {
  const session = getSession(req);
  if (!session) { unauth(res); return; }

  const gId = getId(req);
  const userId = String(req.params["userId"]);

  const entries = await db.select().from(logEntries)
    .where(and(
      eq(logEntries.guildId, gId),
      eq(logEntries.eventType, "member_warn"),
      eq(logEntries.targetId, userId),
    ))
    .orderBy(desc(logEntries.createdAt));

  res.json(entries.map(serializeEntry));
});

export default router;
