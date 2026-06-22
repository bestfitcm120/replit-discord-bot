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

function ChannelSelect({
  value,
  onChange,
  channels,
  placeholder = "Select channel...",
  prefix = "#",
}: {
  value: string | null;
  onChange: (v: string | null) => void;
  channels: Array<{ id: string; name: string }>;
  placeholder?: string;
  prefix?: string;
}) {
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

export default function ServerVoice() {
  const [, params] = useRoute("/servers/:guildId/voice");
  const guildId = params?.guildId ?? "";
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: user, isLoading: userLoading } = useGetMe({
    query: { queryKey: getGetMeQueryKey(), retry: false },
  });

  const { data: config, isLoading: configLoading } = useGetGuildConfig(guildId, {
    query: { enabled: !!guildId && !!user, queryKey: getGetGuildConfigQueryKey(guildId) },
  });

  const { data: voiceChannels = [] } = useListGuildChannels(guildId, { type: 2 }, {
    query: { enabled: !!guildId && !!user, queryKey: getListGuildChannelsQueryKey(guildId, { type: 2 }) },
  });

  const updateConfig = useUpdateGuildConfig();
  const [creationVoiceChannel, setCreationVoiceChannel] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!userLoading && !user) setLocation("/");
  }, [user, userLoading, setLocation]);

  useEffect(() => {
    if (config) {
      setCreationVoiceChannel(config.creationVoiceChannel ?? null);
      setDirty(false);
    }
  }, [config]);

  function setCreationVoice(value: string | null) {
    setCreationVoiceChannel(value);
    setDirty(true);
  }

  async function handleSave() {
    try {
      await updateConfig.mutateAsync({
        guildId,
        data: {
          defaultLogChannel: config?.defaultLogChannel ?? null,
          logChannels: config?.logChannels ?? {},
          creationVoiceChannel,
        },
      });
      queryClient.invalidateQueries({ queryKey: getGetGuildConfigQueryKey(guildId) });
      setDirty(false);
      toast({ title: "Settings saved", description: "Voice channel configuration updated." });
    } catch {
      toast({ title: "Save failed", description: "Could not save configuration.", variant: "destructive" });
    }
  }

  if (!user) return null;

  return (
    <ServerLayout guildId={guildId} activePage="voice">
      <div className="space-y-6 pb-10">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-foreground">Temporary Voice Channels</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Auto-create and manage private voice channels for members.
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
          <Skeleton className="h-48 rounded-xl" />
        ) : (
          <>
            {/* Main config card */}
            <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/5 overflow-hidden">
              <div className="px-5 py-3 border-b border-indigo-500/20 bg-indigo-500/10 flex items-center gap-2">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-indigo-400">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
                <span className="text-xs font-semibold text-indigo-300 uppercase tracking-wider">
                  Temporary Voice Channel Configuration
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

                <div className={`rounded-lg px-4 py-3 text-xs space-y-1 ${
                  creationVoiceChannel
                    ? "bg-indigo-500/10 border border-indigo-500/20 text-indigo-300"
                    : "bg-secondary/40 border border-border text-muted-foreground"
                }`}>
                  {creationVoiceChannel ? (
                    <>
                      <p className="font-semibold text-indigo-300">✅ Feature is active — How it works</p>
                      <ul className="list-disc list-inside space-y-0.5 text-indigo-300/80">
                        <li>Member joins the selected voice channel</li>
                        <li>Bot creates <code>⌛ {"<"}member name{">"}</code> in the same category, copying all permission overwrites</li>
                        <li>Member is moved to their new channel and gets full control</li>
                        <li>Channel is deleted automatically when the last person leaves</li>
                      </ul>
                      <p className="text-indigo-300/60 pt-1">
                        Tip: Set "Connect" permission on the creation channel in Discord to control which roles can use this feature.
                      </p>
                    </>
                  ) : (
                    <p>Feature is <strong>disabled</strong>. Select a voice channel above to activate it.</p>
                  )}
                </div>
              </div>
            </div>

            {/* Status indicator */}
            <div className="rounded-xl border border-border bg-card p-5">
              <h3 className="text-sm font-semibold text-foreground mb-3">Status</h3>
              <div className="flex items-center gap-3">
                <div className={`w-2.5 h-2.5 rounded-full ${creationVoiceChannel ? "bg-green-400" : "bg-muted-foreground"}`} />
                <span className="text-sm text-muted-foreground">
                  {creationVoiceChannel
                    ? "Temporary voice channels are enabled."
                    : "Temporary voice channels are disabled."}
                </span>
              </div>
            </div>
          </>
        )}
      </div>
      <Toaster />
    </ServerLayout>
  );
}
