import {
  useGetMe,
  useGetGuild,
  useGetGuildStats,
  useGetGuildMemberHistory,
  useGetGuildMessageHistory,
  useListGuildLogs,
  getGetMeQueryKey,
  getGetGuildQueryKey,
  getGetGuildStatsQueryKey,
  getGetGuildMemberHistoryQueryKey,
  getGetGuildMessageHistoryQueryKey,
  getListGuildLogsQueryKey,
} from "@workspace/api-client-react";
import { useRoute, useLocation } from "wouter";
import { useEffect } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { ServerLayout } from "@/components/server-layout";

const EVENT_LABELS: Record<string, string> = {
  member_ban: "Member Banned",
  member_unban: "Member Unbanned",
  member_timeout_add: "Timeout Given",
  member_timeout_remove: "Timeout Removed",
  member_kick: "Member Kicked",
  member_join: "Member Joined",
  member_leave: "Member Left",
  member_nickname_change: "Nickname Changed",
  member_role_add: "Role Given",
  member_role_remove: "Role Removed",
  member_voice_move: "Moved Voice Channel",
  member_voice_disconnect: "Disconnected from Voice",
  message_delete: "Message Deleted",
  message_edit: "Message Edited",
  role_create: "Role Created",
  role_delete: "Role Deleted",
  role_update: "Role Updated",
  channel_update: "Channel Updated",
  channel_permissions_update: "Channel Permissions Updated",
  invite_create: "Invite Created",
  command_used: "Command Used",
  server_update: "Server Updated",
};

const EVENT_COLORS: Record<string, string> = {
  member_ban: "#ef4444",
  member_unban: "#22c55e",
  member_timeout_add: "#f97316",
  member_timeout_remove: "#22c55e",
  member_kick: "#f97316",
  member_join: "#22c55e",
  member_leave: "#ef4444",
  member_nickname_change: "#3b82f6",
  member_role_add: "#a855f7",
  member_role_remove: "#6b7280",
  member_voice_move: "#3b82f6",
  member_voice_disconnect: "#6b7280",
  message_delete: "#ef4444",
  message_edit: "#eab308",
  role_create: "#22c55e",
  role_delete: "#ef4444",
  role_update: "#3b82f6",
  channel_update: "#3b82f6",
  channel_permissions_update: "#f97316",
  invite_create: "#a855f7",
  command_used: "#5865f2",
  server_update: "#5865f2",
};

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="p-5 rounded-xl border border-border bg-card">
      <div className="text-sm text-muted-foreground mb-1">{label}</div>
      <div className="text-2xl font-bold text-foreground">{typeof value === "number" ? value.toLocaleString() : value}</div>
      {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
    </div>
  );
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function timeAgo(isoStr: string) {
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function ServerOverview() {
  const [, params] = useRoute("/servers/:guildId");
  const guildId = params?.guildId ?? "";
  const [, setLocation] = useLocation();

  const { data: user, isLoading: userLoading } = useGetMe({ query: { queryKey: getGetMeQueryKey(), retry: false } });
  const { data: guild, isLoading: guildLoading } = useGetGuild(guildId, {
    query: { enabled: !!guildId && !!user, queryKey: getGetGuildQueryKey(guildId) },
  });
  const { data: stats } = useGetGuildStats(guildId, {
    query: { enabled: !!guildId && !!user, queryKey: getGetGuildStatsQueryKey(guildId) },
  });
  const { data: memberHistory } = useGetGuildMemberHistory(guildId, {
    query: { enabled: !!guildId && !!user, queryKey: getGetGuildMemberHistoryQueryKey(guildId) },
  });
  const { data: messageHistory } = useGetGuildMessageHistory(guildId, {
    query: { enabled: !!guildId && !!user, queryKey: getGetGuildMessageHistoryQueryKey(guildId) },
  });
  const { data: logs } = useListGuildLogs(guildId, {
    query: { enabled: !!guildId && !!user, queryKey: getListGuildLogsQueryKey(guildId) },
  });

  useEffect(() => {
    if (!userLoading && !user) {
      setLocation("/");
    }
  }, [user, userLoading, setLocation]);

  if (!user) return null;

  return (
    <ServerLayout guildId={guildId} activePage="overview">
      {guildLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-8 w-48" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Stats row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              label="Total Members"
              value={stats?.totalMembers ?? guild?.memberCount ?? 0}
            />
            <StatCard
              label="Joined (24h)"
              value={stats?.membersJoinedLast24h ?? 0}
              sub="last 24 hours"
            />
            <StatCard
              label="Left (24h)"
              value={stats?.membersLeftLast24h ?? 0}
              sub="last 24 hours"
            />
            <StatCard
              label="Messages (24h)"
              value={stats?.messagesLast24h ?? 0}
              sub="excluding bots"
            />
          </div>

          {/* Member flow chart */}
          <div className="p-5 rounded-xl border border-border bg-card">
            <h3 className="font-semibold text-foreground mb-4">Member Flow (30 days)</h3>
            {memberHistory && memberHistory.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={memberHistory.map((p) => ({ ...p, date: formatDate(p.date) }))}>
                  <defs>
                    <linearGradient id="joinsGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="leavesGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 15% 18%)" />
                  <XAxis dataKey="date" tick={{ fill: "hsl(220 10% 65%)", fontSize: 11 }} />
                  <YAxis tick={{ fill: "hsl(220 10% 65%)", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ background: "hsl(220 15% 13%)", border: "1px solid hsl(220 15% 18%)", borderRadius: 8 }}
                    labelStyle={{ color: "hsl(220 10% 90%)" }}
                  />
                  <Legend />
                  <Area type="monotone" dataKey="joins" stroke="#22c55e" fill="url(#joinsGrad)" strokeWidth={2} name="Joins" />
                  <Area type="monotone" dataKey="leaves" stroke="#ef4444" fill="url(#leavesGrad)" strokeWidth={2} name="Leaves" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[220px] flex items-center justify-center text-muted-foreground text-sm">
                No member data yet — data appears once the bot starts tracking join/leave events.
              </div>
            )}
          </div>

          {/* Messages chart */}
          <div className="p-5 rounded-xl border border-border bg-card">
            <h3 className="font-semibold text-foreground mb-4">Messages (7 days, excluding bots)</h3>
            {messageHistory && messageHistory.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={messageHistory.map((p) => ({ ...p, date: formatDate(p.date) }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 15% 18%)" />
                  <XAxis dataKey="date" tick={{ fill: "hsl(220 10% 65%)", fontSize: 11 }} />
                  <YAxis tick={{ fill: "hsl(220 10% 65%)", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ background: "hsl(220 15% 13%)", border: "1px solid hsl(220 15% 18%)", borderRadius: 8 }}
                    labelStyle={{ color: "hsl(220 10% 90%)" }}
                  />
                  <Bar dataKey="count" fill="#5865f2" radius={[4, 4, 0, 0]} name="Messages" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[200px] flex items-center justify-center text-muted-foreground text-sm">
                No message data yet — data appears as members chat in the server.
              </div>
            )}
          </div>

          {/* Audit log */}
          <div className="p-5 rounded-xl border border-border bg-card">
            <h3 className="font-semibold text-foreground mb-4">Recent Audit Log</h3>
            {logs && logs.length > 0 ? (
              <div className="space-y-1">
                {logs.slice(0, 20).map((entry) => (
                  <div
                    key={entry.id}
                    className="flex items-start gap-3 px-3 py-2.5 rounded-lg hover:bg-secondary/40 transition-colors"
                  >
                    <div
                      className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0"
                      style={{ background: EVENT_COLORS[entry.eventType] ?? "#6b7280" }}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground">
                          {EVENT_LABELS[entry.eventType] ?? entry.eventType}
                        </span>
                        <span className="text-xs text-muted-foreground">{timeAgo(entry.createdAt)}</span>
                      </div>
                      <p className="text-sm text-muted-foreground mt-0.5 truncate">{entry.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-12 text-center text-muted-foreground text-sm">
                No log entries yet. Events will appear here once the bot starts logging.
              </div>
            )}
          </div>
        </div>
      )}
    </ServerLayout>
  );
}
