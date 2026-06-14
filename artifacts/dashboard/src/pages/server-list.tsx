import { useGetMe, useListGuilds, useGetBotInvite, getGetMeQueryKey, getListGuildsQueryKey, getGetBotInviteQueryKey } from "@workspace/api-client-react";
import { useLocation } from "wouter";
import { useEffect } from "react";
import { Skeleton } from "@/components/ui/skeleton";

function GuildAvatar({ name, iconUrl }: { name: string; iconUrl?: string | null }) {
  if (iconUrl) {
    return <img src={iconUrl} alt={name} className="w-12 h-12 rounded-xl object-cover" />;
  }
  const initials = name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
  const hue = name.split("").reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360;
  return (
    <div
      className="w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-sm"
      style={{ background: `hsl(${hue}, 60%, 40%)` }}
    >
      {initials}
    </div>
  );
}

function NavBar({ user }: { user: { username: string; avatarUrl: string } }) {
  const [, setLocation] = useLocation();
  return (
    <nav className="border-b border-border sticky top-0 z-10 bg-background/95 backdrop-blur">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <button
          onClick={() => setLocation("/")}
          className="flex items-center gap-3"
        >
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" className="text-primary-foreground">
              <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057c.002.022.013.043.03.055a19.9 19.9 0 0 0 5.993 3.03.077.077 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.030z"/>
            </svg>
          </div>
          <span className="font-semibold text-foreground">ModBot</span>
        </button>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">{user.username}</span>
          <img src={user.avatarUrl} alt={user.username} className="w-8 h-8 rounded-full" />
          <a
            href="/api/auth/logout"
            onClick={async (e) => {
              e.preventDefault();
              await fetch("/api/auth/logout", { method: "POST" });
              window.location.href = "/";
            }}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Logout
          </a>
        </div>
      </div>
    </nav>
  );
}

export default function ServerList() {
  const [, setLocation] = useLocation();
  const { data: user, isLoading: userLoading } = useGetMe({ query: { queryKey: getGetMeQueryKey(), retry: false } });
  const { data: guilds, isLoading: guildsLoading } = useListGuilds({ query: { queryKey: getListGuildsQueryKey(), enabled: !!user } });
  const { data: invite } = useGetBotInvite({ query: { queryKey: getGetBotInviteQueryKey() } });

  useEffect(() => {
    if (!userLoading && !user) {
      setLocation("/");
    }
  }, [user, userLoading, setLocation]);

  if (userLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) return null;

  const botGuilds = guilds?.filter((g) => g.botPresent) ?? [];
  const noBot = guilds?.filter((g) => !g.botPresent) ?? [];

  return (
    <div className="min-h-screen bg-background text-foreground">
      <NavBar user={user} />
      <div className="max-w-4xl mx-auto px-6 py-10">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground">Your Servers</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Manage bot configuration for servers where you have Manage Server permission.
          </p>
        </div>

        {guildsLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-20 w-full rounded-xl" />
            ))}
          </div>
        ) : (
          <>
            {botGuilds.length > 0 && (
              <section className="mb-8">
                <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                  Bot Active
                </h2>
                <div className="space-y-2">
                  {botGuilds.map((guild) => (
                    <button
                      key={guild.id}
                      onClick={() => setLocation(`/servers/${guild.id}`)}
                      className="w-full flex items-center gap-4 p-4 rounded-xl border border-border bg-card hover:border-primary/40 hover:bg-secondary/50 transition-all text-left group"
                    >
                      <GuildAvatar name={guild.name} iconUrl={guild.iconUrl} />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-foreground truncate">{guild.name}</div>
                        <div className="text-sm text-muted-foreground">
                          {guild.memberCount > 0 ? `${guild.memberCount.toLocaleString()} members` : "Active"}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-green-500/10 text-green-400 text-xs font-medium">
                          <div className="w-1.5 h-1.5 rounded-full bg-green-400" />
                          Active
                        </div>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-muted-foreground group-hover:text-foreground transition-colors">
                          <path d="M9 18l6-6-6-6" />
                        </svg>
                      </div>
                    </button>
                  ))}
                </div>
              </section>
            )}

            {noBot.length > 0 && (
              <section>
                <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                  Bot Not Added
                </h2>
                <div className="space-y-2">
                  {noBot.map((guild) => (
                    <div
                      key={guild.id}
                      className="flex items-center gap-4 p-4 rounded-xl border border-border bg-card/50 opacity-60"
                    >
                      <GuildAvatar name={guild.name} iconUrl={guild.iconUrl} />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-foreground truncate">{guild.name}</div>
                        <div className="text-sm text-muted-foreground">
                          {guild.memberCount > 0 ? `${guild.memberCount.toLocaleString()} members` : ""}
                        </div>
                      </div>
                      {invite?.url && (
                        <a
                          href={`${invite.url}&guild_id=${guild.id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity"
                          onClick={(e) => e.stopPropagation()}
                        >
                          Add Bot
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {guilds?.length === 0 && (
              <div className="text-center py-16 text-muted-foreground">
                <div className="text-4xl mb-4">No servers found</div>
                <p className="text-sm">You need Manage Server permission to see servers here.</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
