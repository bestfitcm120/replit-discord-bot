import discord
from typing import List, Tuple


class RoleEventHandlers:
    @staticmethod
    async def role_create(role: discord.Role) -> discord.Embed:
        embed = discord.Embed(
            title="Role Created",
            description=f"New role {role.mention} was created.",
            color=role.color if role.color.value else discord.Color.green(),
        )
        embed.add_field(name="Name", value=role.name, inline=True)
        embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No", inline=True)
        embed.add_field(name="Hoisted", value="Yes" if role.hoist else "No", inline=True)
        embed.set_footer(text=f"Role ID: {role.id}")
        embed.timestamp = discord.utils.utcnow()
        return embed

    @staticmethod
    async def role_delete(role: discord.Role) -> discord.Embed:
        embed = discord.Embed(
            title="Role Deleted",
            description=f"Role **{role.name}** was deleted.",
            color=discord.Color.red(),
        )
        embed.add_field(name="Name", value=role.name, inline=True)
        embed.add_field(name="Members had role", value=str(len(role.members)), inline=True)
        embed.set_footer(text=f"Role ID: {role.id}")
        embed.timestamp = discord.utils.utcnow()
        return embed

    @staticmethod
    async def role_update(before: discord.Role, after: discord.Role) -> discord.Embed:
        changes: List[str] = []

        if before.name != after.name:
            changes.append(f"**Name:** {before.name} → {after.name}")
        if before.color != after.color:
            changes.append(f"**Color:** {before.color} → {after.color}")
        if before.hoist != after.hoist:
            changes.append(f"**Hoisted:** {before.hoist} → {after.hoist}")
        if before.mentionable != after.mentionable:
            changes.append(f"**Mentionable:** {before.mentionable} → {after.mentionable}")
        if before.permissions != after.permissions:
            changes.append("**Permissions** were changed.")

        embed = discord.Embed(
            title="Role Updated",
            description=f"Role {after.mention} was updated.",
            color=after.color if after.color.value else discord.Color.blue(),
        )
        if changes:
            embed.add_field(name="Changes", value="\n".join(changes), inline=False)
        embed.set_footer(text=f"Role ID: {after.id}")
        embed.timestamp = discord.utils.utcnow()
        return embed
