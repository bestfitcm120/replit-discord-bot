import { pgTable, text, jsonb, timestamp, bigserial, boolean, date, integer, primaryKey } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod/v4";

export const guildConfigs = pgTable("guild_configs", {
  guildId: text("guild_id").primaryKey(),
  defaultLogChannel: text("default_log_channel"),
  logChannels: jsonb("log_channels").notNull().default({}),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull().defaultNow(),
});

export const insertGuildConfigSchema = createInsertSchema(guildConfigs).omit({ updatedAt: true });
export type InsertGuildConfig = z.infer<typeof insertGuildConfigSchema>;
export type GuildConfig = typeof guildConfigs.$inferSelect;

export const logEntries = pgTable("log_entries", {
  id: bigserial("id", { mode: "number" }).primaryKey(),
  guildId: text("guild_id").notNull(),
  eventType: text("event_type").notNull(),
  userId: text("user_id"),
  targetId: text("target_id"),
  description: text("description").notNull(),
  metadata: jsonb("metadata").notNull().default({}),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export type LogEntry = typeof logEntries.$inferSelect;

export const memberEvents = pgTable("member_events", {
  id: bigserial("id", { mode: "number" }).primaryKey(),
  guildId: text("guild_id").notNull(),
  userId: text("user_id").notNull(),
  eventType: text("event_type").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull().defaultNow(),
});

export type MemberEvent = typeof memberEvents.$inferSelect;

export const messageStats = pgTable("message_stats", {
  guildId: text("guild_id").notNull(),
  channelId: text("channel_id").notNull(),
  userId: text("user_id").notNull(),
  isBot: boolean("is_bot").notNull().default(false),
  statDate: date("stat_date").notNull(),
  count: integer("count").notNull().default(0),
}, (table) => ({
  pk: primaryKey({ columns: [table.guildId, table.channelId, table.userId, table.statDate] }),
}));

export type MessageStat = typeof messageStats.$inferSelect;
