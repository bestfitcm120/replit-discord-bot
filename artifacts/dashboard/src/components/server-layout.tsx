import { useGetGuild, getGetGuildQueryKey } from "@workspace/api-client-react";
import { useLocation } from "wouter";
import { Skeleton } from "@/components/ui/skeleton";

interface ServerLayoutProps {
  guildId: string;
  activePage: "overview" | "settings";
  children: React.ReactNode;
}

function GuildIcon({ name, iconUrl }: { name: string; iconUrl?: string | null }) {
  if (iconUrl) {
    return <img src={iconUrl} alt={name} className="w-9 h-9 rounded-lg object-cover" />;
  }
  const initials = name.split(" ").slice(0, 2).map((w) => w[0]).join("").toUpperCase();
  const hue = name.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360;
  return (
    <div
      className="w-9 h-9 rounded-lg flex items-center justify-center text-white font-bold text-xs"
      style={{ background: `hsl(${hue}, 60%, 40%)` }}
    >
      {initials}
    </div>
  );
}

export function ServerLayout({ guildId, activePage, children }: ServerLayoutProps) {
  const [, setLocation] = useLocation();
  const { data: guild } = useGetGuild(guildId, {
    query: { enabled: !!guildId, queryKey: getGetGuildQueryKey(guildId) },
  });

  return (
    <div className="min-h-screen bg-background text-foreground flex">
      {/* Sidebar */}
      <aside className="w-60 border-r border-border flex flex-col flex-shrink-0">
        {/* Back button */}
        <div className="p-4 border-b border-border">
          <button
            onClick={() => setLocation("/servers")}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 18l-6-6 6-6" />
            </svg>
            All Servers
          </button>
        </div>

        {/* Guild info */}
        <div className="p-4 border-b border-border">
          {guild ? (
            <div className="flex items-center gap-3">
              <GuildIcon name={guild.name} iconUrl={guild.iconUrl} />
              <div className="min-w-0">
                <div className="font-medium text-foreground text-sm truncate">{guild.name}</div>
                {guild.memberCount > 0 && (
                  <div className="text-xs text-muted-foreground">{guild.memberCount.toLocaleString()} members</div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <Skeleton className="w-9 h-9 rounded-lg" />
              <div className="flex-1">
                <Skeleton className="h-4 w-24 mb-1" />
                <Skeleton className="h-3 w-16" />
              </div>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-1">
          <button
            onClick={() => setLocation(`/servers/${guildId}`)}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              activePage === "overview"
                ? "bg-primary/15 text-primary"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary"
            }`}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7" rx="1" />
              <rect x="14" y="3" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" />
              <rect x="14" y="14" width="7" height="7" rx="1" />
            </svg>
            Overview
          </button>

          <button
            onClick={() => setLocation(`/servers/${guildId}/settings`)}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              activePage === "settings"
                ? "bg-primary/15 text-primary"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary"
            }`}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
            Log Settings
          </button>
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="p-6 max-w-4xl">
          {children}
        </div>
      </main>
    </div>
  );
}
