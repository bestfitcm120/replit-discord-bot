import discord
from typing import List


class ServerEventHandlers:
    @staticmethod
    async def server_update(before: discord.Guild, after: discord.Guild) -> discord.Embed:
        changes: List[str] = []

        if before.name != after.name:
            changes.append(f"**Name:** {before.name} → {after.name}")
        if before.description != after.description:
            changes.append(f"**Description:** {before.description or '*none*'} → {after.description or '*none*'}")
        if before.icon != after.icon:
            changes.append("**Icon** was changed.")
        if before.banner != after.banner:
            changes.append("**Banner** was changed.")
        if before.verification_level != after.verification_level:
            changes.append(f"**Verification Level:** {before.verification_level} → {after.verification_level}")
        if before.explicit_content_filter != after.explicit_content_filter:
            changes.append(f"**Content Filter:** {before.explicit_content_filter} → {after.explicit_content_filter}")
        if before.default_notifications != after.default_notifications:
            changes.append(f"**Default Notifications:** {before.default_notifications} → {after.default_notifications}")
        if before.preferred_locale != after.preferred_locale:
            changes.append(f"**Locale:** {before.preferred_locale} → {after.preferred_locale}")

        embed = discord.Embed(
            title="Server Updated",
            description="Server settings were changed.",
            color=discord.Color.blurple(),
        )
        if changes:
            embed.add_field(name="Changes", value="\n".join(changes), inline=False)
        else:
            embed.description = "Server settings were updated (non-tracked field changed)."
        embed.set_footer(text=f"Guild ID: {after.id}")
        embed.timestamp = discord.utils.utcnow()
        return embed

    @staticmethod
    async def invite_create(invite: discord.Invite) -> discord.Embed:
        embed = discord.Embed(
            title="Invite Created",
            description=f"A new invite was created by {invite.inviter.mention if invite.inviter else 'Unknown'}.",
            color=discord.Color.green(),
        )
        embed.add_field(name="Code", value=invite.code, inline=True)
        embed.add_field(name="Max Uses", value=str(invite.max_uses) if invite.max_uses else "Unlimited", inline=True)
        embed.add_field(
            name="Expires",
            value=f"<t:{int(invite.expires_at.timestamp())}:R>" if invite.expires_at else "Never",
            inline=True,
        )
        if invite.channel:
            embed.add_field(name="Channel", value=invite.channel.mention, inline=True)
        embed.set_footer(text=f"Inviter ID: {invite.inviter.id if invite.inviter else 'Unknown'}")
        embed.timestamp = discord.utils.utcnow()
        return embed
