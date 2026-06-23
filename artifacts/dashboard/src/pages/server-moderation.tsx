import {
  useGetMe,
  useListGuildModeration,
  getGetMeQueryKey,
  getListGuildModerationQueryKey,
} from "@workspace/api-client-react";
import { useRoute, useLocation } from "wouter";
import { useEffect, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { ServerLayout } from "@/components/server-layout";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

type EventType =
  | "member_ban"
  | "member_unban"
  | "member_kick"
  | "member_timeout_add"
  | "member_timeout_remove"
  | "member_warn";

const EVENT_LABELS: Record<EventType, string> = {
  member_ban: "Ban",
  member_unban: "Unban",
  member_kick: "Kick",
  member_timeout_add: "Timeout",
  member_timeout_remove: "Untimeout",
  member_warn: "Warn",
};

const EVENT_COLORS: Record<EventType, string> = {
  member_ban: "bg-red-500/15 text-red-400 border-red-500/20",
  member_unban: "bg-green-500/15 text-green-400 border-green-500/20",
  member_kick: "bg-orange-500/15 text-orange-400 border-orange-500/20",
  member_timeout_add: "bg-yellow-500/15 text-yellow-400 border-yellow-500/20",
  member_timeout_remove: "bg-blue-500/15 text-blue-400 border-blue-500/20",
  member_warn: "bg-amber-500/15 text-amber-400 border-amber-500/20",
};

function Badge({ eventType }: { eventType: string }) {
  const label = EVENT_LABELS[eventType as EventType] ?? eventType;
  const color =
    EVENT_COLORS[eventType as EventType] ??
    "bg-muted/50 text-muted-foreground border-border";
  return (
    <span
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold ${color}`}
    >
      {label}
    </span>
  );
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function truncate(s: string, n: number) {
  return s.length > n ? s.slice(0, n) + "…" : s;
}

export default function ServerModeration() {
  const [, params] = useRoute("/servers/:guildId/moderation");
  const guildId = params?.guildId ?? "";
  const [, setLocation] = useLocation();

  const [filterInput, setFilterInput] = useState("");
  const [activeFilter, setActiveFilter] = useState<string | undefined>(undefined);

  const { data: user, isLoading: userLoading } = useGetMe({
    query: { queryKey: getGetMeQueryKey(), retry: false },
  });

  const { data: actions = [], isLoading } = useListGuildModeration(
    guildId,
    activeFilter ? { userId: activeFilter } : {},
    {
      query: {
        queryKey: getListGuildModerationQueryKey(guildId, activeFilter ? { userId: activeFilter } : {}),
        enabled: !!guildId && !!user,
      },
    }
  );

  useEffect(() => {
    if (!userLoading && !user) setLocation("/");
  }, [user, userLoading, setLocation]);

  function applyFilter() {
    const v = filterInput.trim();
    setActiveFilter(v || undefined);
  }

  function clearFilter() {
    setFilterInput("");
    setActiveFilter(undefined);
  }

  return (
    <ServerLayout guildId={guildId} activePage="moderation">
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Moderation History</h1>
          <p className="text-sm text-muted-foreground mt-1">
            All bans, kicks, timeouts, and warnings issued via slash commands.
          </p>
        </div>

        {/* Commands reference */}
        <div className="rounded-xl border border-border bg-card p-4 space-y-3">
          <h2 className="text-sm font-semibold text-foreground">Available Slash Commands</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {[
              { cmd: "/ban <user> [reason] [delete_days]", desc: "Permanently ban a member" },
              { cmd: "/unban <user_id> [reason]", desc: "Revoke a ban by user ID" },
              { cmd: "/kick <user> [reason]", desc: "Remove a member from the server" },
              { cmd: "/timeout <user> <minutes> [reason]", desc: "Mute a member temporarily (up to 28d)" },
              { cmd: "/untimeout <user> [reason]", desc: "Remove an active timeout" },
              { cmd: "/warn <user> <reason>", desc: "Issue a formal warning (logged + DMs user)" },
              { cmd: "/purge <count> [user]", desc: "Bulk delete up to 100 messages" },
            ].map(({ cmd, desc }) => (
              <div key={cmd} className="flex flex-col gap-0.5 rounded-lg bg-secondary/40 px-3 py-2">
                <code className="text-xs text-primary font-mono">{cmd}</code>
                <span className="text-xs text-muted-foreground">{desc}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Filter bar */}
        <div className="flex gap-2">
          <Input
            placeholder="Filter by target user ID…"
            value={filterInput}
            onChange={(e) => setFilterInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && applyFilter()}
            className="max-w-xs font-mono text-sm"
          />
          <Button size="sm" onClick={applyFilter}>Filter</Button>
          {activeFilter && (
            <Button size="sm" variant="ghost" onClick={clearFilter}>
              Clear
            </Button>
          )}
        </div>

        {activeFilter && (
          <p className="text-xs text-muted-foreground -mt-4">
            Showing actions targeting user <code className="font-mono">{activeFilter}</code>
          </p>
        )}

        {/* Table */}
        <div className="rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-secondary/30">
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Action</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Target User</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide hidden md:table-cell">Reason</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide hidden lg:table-cell">When</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {isLoading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i}>
                    <td className="px-4 py-3"><Skeleton className="h-5 w-16" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-28" /></td>
                    <td className="px-4 py-3 hidden md:table-cell"><Skeleton className="h-4 w-40" /></td>
                    <td className="px-4 py-3 hidden lg:table-cell"><Skeleton className="h-4 w-24" /></td>
                  </tr>
                ))
              ) : actions.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-12 text-center text-muted-foreground text-sm">
                    {activeFilter
                      ? "No moderation actions found for that user."
                      : "No moderation actions recorded yet. Use the slash commands in your server to get started."}
                  </td>
                </tr>
              ) : (
                actions.map((entry) => {
                  const meta = entry.metadata as Record<string, unknown> | null ?? {};
                  const reason = typeof meta["reason"] === "string" ? meta["reason"] : "—";
                  return (
                    <tr key={entry.id} className="hover:bg-secondary/20 transition-colors">
                      <td className="px-4 py-3">
                        <Badge eventType={entry.eventType} />
                      </td>
                      <td className="px-4 py-3">
                        {entry.targetId ? (
                          <div className="flex items-center gap-2">
                            {entry.targetAvatarUrl ? (
                              <img src={entry.targetAvatarUrl} alt="" className="w-7 h-7 rounded-full flex-shrink-0" />
                            ) : (
                              <div className="w-7 h-7 rounded-full bg-secondary border border-border flex-shrink-0 flex items-center justify-center text-xs text-muted-foreground">
                                {(entry.targetDisplayName ?? entry.targetId).slice(0, 1).toUpperCase()}
                              </div>
                            )}
                            <span className="text-sm text-foreground">
                              {entry.targetDisplayName ?? entry.targetId}
                            </span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 hidden md:table-cell text-muted-foreground">
                        {truncate(reason, 60)}
                      </td>
                      <td className="px-4 py-3 hidden lg:table-cell text-muted-foreground whitespace-nowrap">
                        {entry.createdAt ? formatDate(entry.createdAt) : "—"}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>

          {actions.length > 0 && (
            <div className="px-4 py-2 border-t border-border bg-secondary/10 text-xs text-muted-foreground">
              {actions.length} action{actions.length !== 1 ? "s" : ""} shown
              {actions.length === 100 ? " (showing most recent 100)" : ""}
            </div>
          )}
        </div>
      </div>
    </ServerLayout>
  );
}
