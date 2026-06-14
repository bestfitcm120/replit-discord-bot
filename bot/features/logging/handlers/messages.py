import discord


class MessageEventHandlers:
    @staticmethod
    async def message_delete(message: discord.Message) -> discord.Embed:
        embed = discord.Embed(
            title="Message Deleted",
            description=f"A message by {message.author.mention} was deleted in {message.channel.mention}.",
            color=discord.Color.red(),
        )
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        if message.content:
            content = message.content[:1000] + ("..." if len(message.content) > 1000 else "")
            embed.add_field(name="Content", value=content, inline=False)
        if message.attachments:
            embed.add_field(
                name="Attachments",
                value="\n".join(a.filename for a in message.attachments),
                inline=False,
            )
        embed.set_footer(text=f"Author ID: {message.author.id} | Channel: #{message.channel.name}")
        embed.timestamp = discord.utils.utcnow()
        return embed

    @staticmethod
    async def message_edit(before: discord.Message, after: discord.Message) -> discord.Embed:
        embed = discord.Embed(
            title="Message Edited",
            description=f"{after.author.mention} edited a message in {after.channel.mention}. [Jump to message]({after.jump_url})",
            color=discord.Color.yellow(),
        )
        embed.set_author(name=str(after.author), icon_url=after.author.display_avatar.url)
        before_content = before.content[:500] + ("..." if len(before.content) > 500 else "") if before.content else "*empty*"
        after_content = after.content[:500] + ("..." if len(after.content) > 500 else "") if after.content else "*empty*"
        embed.add_field(name="Before", value=before_content, inline=False)
        embed.add_field(name="After", value=after_content, inline=False)
        embed.set_footer(text=f"Author ID: {after.author.id} | Channel: #{after.channel.name}")
        embed.timestamp = discord.utils.utcnow()
        return embed
