export function getBotInviteUrl(): string {
  const clientId = process.env["DISCORD_CLIENT_ID"] ?? "";
  const permissions = process.env["DISCORD_BOT_PERMISSIONS"] ?? "8";
  return (
    `https://discord.com/api/oauth2/authorize` +
    `?client_id=${clientId}` +
    `&permissions=${permissions}` +
    `&scope=bot%20applications.commands`
  );
}
