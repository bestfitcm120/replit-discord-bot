import {
  useGetMe,
  useGetGuildConfig,
  useUpdateGuildConfig,
  useListGuildChannels,
  getGetMeQueryKey,
  getGetGuildConfigQueryKey,
  getListGuildChannelsQueryKey,
} from "@workspace/api-client-react";
import { useRoute, useLocation } from "wouter";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/skeleton";
import { ServerLayout } from "@/components/server-layout";
import { useToast } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";

const LOG_EVENTS: Array<{ key: string; label: string; category: string }> = [
  { key: "member_ban", label: "Member Banned", category: "Member Events" },
  { key: "member_unban", label: "Member Unbanned", category: "Member Events" },
  { key: "member_timeout_add", label: "Timeout Given", category: "Member Events" },
  { key: "member_timeout_remove", label: "Timeout Removed", category: "Member Events" },
  { key: "member_kick", label: "Member Kicked", category: "Member Events" },
  { key: "member_warn", label: "Member Warned", category: "Member Events" },
  { key: "member_join", label: "Member Joined", category: "Member Events" },
  { key: "member_leave", label: "Member Left", category: "Member Events" },
  { key: "member_nickname_change", label: "Nickname Changed", category: "Member Events" },
  { key: "member_role_add", label: "Role Given to Member", category: "Member Events" },
  { key: "member_role_remove", label: "Role Removed from Member", category: "Member Events" },
  { key: "message_delete", label: "Message Deleted", category: "Message Events" },
  { key: "message_edit", label: "Message Edited", category: "Message Events" },
  { key: "member_voice_move", label: "Moved Voice Channel", category: "Voice Events" },
  { key: "member_voice_disconnect", label: "Disconnected from Voice", category: "Voice Events" },
  { key: "role_create", label: "Role Created", category: "Role Events" },
  { key: "role_delete", label: "Role Deleted", category: "Role Events" },
  { key: "role_update", label: "Role Updated", category: "Role Events" },
  { key: "channel_update", label: "Channel Updated", category: "Channel Events" },
  { key: "channel_permissions_update", label: "Channel Permissions Updated", category: "Channel Events" },
  { key: "invite_create", label: "Invite Created", category: "Server Events" },
  { key: "command_used", label: "Command Used", category: "Server Events" },
  { key: "server_update", label: "Server Updated", category: "Server Events" },
];

const CATEGORIES = ["Member Events", "Message Events", "Voice Events", "Role Events", "Channel Events", "Server Events"];

interface ChannelSelectProps {
  value: string | null;
  onChange: (v: string | null) => void;
  channels: Array<{ id: string; name: string }>;
  placeholder?: string;
  prefix?: string;
}

function ChannelSelect({ value, onChange, channels, placeholder = "Select channel...", prefix = "#" }: ChannelSelectProps) {
  return (
    <select
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value || null)}
      className="text-sm bg-secondary border border-border rounded-lg px-3 py-1.5 text-foreground min-w-[200px] focus:outline-none focus:ring-2 focus:ring-primary/40"
    >
      <option value="">{placeholder}</option>
      {channels.map((c) => (
        <option key={c.id} value={c.id}>{prefix}{c.name}</option>
      ))}
    </select>
  );
}

export default function ServerSettings() {
  const [, params] = useRoute("/servers/:guildId/settings");
  const guildId = params?.guildId ?? "";
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: user, isLoading: userLoading } = useGetMe({ query: { queryKey: getGetMeQueryKey(), retry: false } });
  const { data: config, isLoading: configLoading } = useGetGuildConfig(guildId, {
    query: { enabled: !!guildId && !!user, queryKey: getGetGuildConfigQueryKey(guildId) },
  });

  // Text channels for log channel selectors
  const { data: textChannels = [] } = useListGuildChannels(guildId, {}, {
    query: { enabled: !!guildId && !!user, queryKey: getListGuildChannelsQueryKey(guildId, {}) },
  });

  // Voice channels for the creation voice channel selector
  const { data: voiceChannels = [] } = useListGuildChannels(guildId, { type: 2 }, {
    query: { enabled: !!guildId && !!user, queryKey: getListGuildChannelsQueryKey(guildId, { type: 2 }) },
  });

  const updateConfig = useUpdateGuildConfig();

  const [defaultChannel, setDefaultChannel] = useState<string | null>(null);
  const [logChannels, setLogChannels] = useState<Record<string, string | null>>({});
  const [creationVoiceChannel, setCreationVoiceChannel] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!userLoading && !user) setLocation("/");
  }, [user, userLoading, setLocation]);

  useEffect(() => {
    if (config) {
      setDefaultChannel(config.defaultLogChannel ?? null);
      setLogChannels(config.logChannels as Record<string, string | null>);
      setCreationVoiceChannel(config.creationVoiceChannel ?? null);
      setDirty(false);
    }
  }, [config]);

  function setChannel(key: string, value: string | null) {
    setLogChannels((prev) => ({ ...prev, [key]: value }));
    setDirty(true);
  }

  function setDefault(value: string | null) {
    setDefaultChannel(value);
    setDirty(true);
  }

  function setCreationVoice(value: string | null) {
    setCreationVoiceChannel(value);
    setDirty(true);
  }

  async function handleSave() {
    try {
      await updateConfig.mutateAsync({
        guildId,
        data: { defaultLogChannel: defaultChannel, logChannels, creationVoiceChannel },
      });
      queryClient.invalidateQueries({ queryKey: getGetGuildConfigQueryKey(guildId) });
      setDirty(false);
      toast({ title: "Settings saved", description: "Configuration has been updated." });
    } catch {
      toast({ title: "Save failed", description: "Could not save configuration.", variant: "destructive" });
    }
  }

  if (!user) return null;

  const filteredText = textChannels.filter((c) => c.type === 0 || c.type === 5);

  return (
    <ServerLayout guildId={guildId} activePage="settings">
      <div className="space-y-6 pb-10">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-foreground">Server Settings</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Configure log channels and bot features for this server.
            </p>
          </div>
          <button
            onClick={handleSave}
            disabled={!dirty || updateConfig.isPending}
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {updateConfig.isPending ? "Saving..." : "Save Changes"}
          </button>
        </div>

        {configLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
          </div>
        ) : (
          <>
            {/* ── Temporary Voice Channels ─────────────────────────────────── */}
            <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/5 overflow-hidden">
              <div className="px-5 py-3 border-b border-indigo-500/20 bg-indigo-500/10 flex items-center gap-2">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-indigo-400">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
                <span className="text-xs font-semibold text-indigo-300 uppercase tracking-wider">
                  Temporary Voice Channels
                </span>
              </div>

              <div className="p-5 space-y-4">
                <p className="text-sm text-muted-foreground">
                  When a member joins the creation channel, the bot instantly creates a private
                  voice channel for them (inheriting all Discord permissions you've set), grants
                  the member full control over it, then auto-deletes it when everyone leaves.
                </p>

                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <div>
                    <div className="font-medium text-sm text-foreground">Creation Voice Channel</div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      Joining this channel triggers temp channel creation.
                      Set permissions on it in Discord to control who can use the feature.
                    </div>
                  </div>
                  <ChannelSelect
                    value={creationVoiceChannel}
                    onChange={setCreationVoice}
                    channels={voiceChannels}
                    placeholder="Disabled — pick a voice channel"
                    prefix="🔊 "
                  />
                </div>

                {creationVoiceChannel && (
                  <div className="rounded-lg bg-indigo-500/10 border border-indigo-500/20 px-4 py-3 text-xs text-indigo-300 space-y-1">
                    <p className="font-semibold">How it works</p>
                    <ul className="list-disc list-inside space-y-0.5 text-indigo-300/80">
                      <li>Member joins the selected voice channel</li>
                      <li>Bot creates <code>⌛ {"<"}member name{">"}</code> in the same category, copying all permission overwrites</li>
                      <li>Member is moved to their new channel and gets full control</li>
                      <li>Channel is deleted automatically when the last person leaves</li>
                    </ul>
                    <p className="text-indigo-300/60 pt-1">
                      Tip: Set "Connect" permission on the creation channel in Discord to control which roles can use this feature.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* ── Default log channel ──────────────────────────────────────── */}
            <div className="p-5 rounded-xl border border-primary/30 bg-primary/5">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="font-medium text-foreground">Default Log Channel</div>
                  <div className="text-sm text-muted-foreground mt-0.5">
                    Fallback channel for any event type without a specific channel assigned.
                  </div>
                </div>
                <ChannelSelect
                  value={defaultChannel}
                  onChange={setDefault}
                  channels={filteredText}
                  placeholder="No default (disabled)"
                />
              </div>
            </div>

            {/* ── Per-category log channel groups ─────────────────────────── */}
            {CATEGORIES.map((category) => {
              const events = LOG_EVENTS.filter((e) => e.category === category);
              return (
                <div key={category} className="rounded-xl border border-border bg-card overflow-hidden">
                  <div className="px-5 py-3 border-b border-border bg-secondary/30">
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      {category}
                    </span>
                  </div>
                  <div className="divide-y divide-border">
                    {events.map((event) => (
                      <div
                        key={event.key}
                        className="flex items-center justify-between gap-4 px-5 py-3 hover:bg-secondary/20 transition-colors"
                      >
                        <div>
                          <span className="text-sm text-foreground">{event.label}</span>
                          {logChannels[event.key] && (
                            <span className="ml-2 text-xs text-primary">configured</span>
                          )}
                        </div>
                        <ChannelSelect
                          value={logChannels[event.key] ?? null}
                          onChange={(v) => setChannel(event.key, v)}
                          channels={filteredText}
                          placeholder={defaultChannel ? "Use default" : "Disabled"}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </>
        )}
      </div>
      <Toaster />
    </ServerLayout>
  );
}
