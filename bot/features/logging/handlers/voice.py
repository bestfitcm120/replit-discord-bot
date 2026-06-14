import discord
from typing import List, Tuple


class VoiceEventHandlers:
    @staticmethod
    async def voice_state_update(
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> List[Tuple[discord.Embed, str]]:
        results: List[Tuple[discord.Embed, str]] = []

        # Member moved from one channel to another
        if before.channel and after.channel and before.channel != after.channel:
            embed = discord.Embed(
                title="Member Moved Voice Channel",
                description=f"{member.mention} was moved from **{before.channel.name}** to **{after.channel.name}**.",
                color=discord.Color.blue(),
            )
            embed.set_author(name=str(member), icon_url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            embed.timestamp = discord.utils.utcnow()
            results.append((embed, "member_voice_move"))

        # Member disconnected from voice
        elif before.channel and not after.channel:
            embed = discord.Embed(
                title="Member Disconnected from Voice",
                description=f"{member.mention} disconnected from **{before.channel.name}**.",
                color=discord.Color.dark_red(),
            )
            embed.set_author(name=str(member), icon_url=member.display_avatar.url)
            embed.set_footer(text=f"User ID: {member.id}")
            embed.timestamp = discord.utils.utcnow()
            results.append((embed, "member_voice_disconnect"))

        return results
