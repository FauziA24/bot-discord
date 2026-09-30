from __future__ import annotations

import discord


def is_same_voice_channel(member: discord.Member, voice: discord.VoiceClient | None) -> bool:
    return bool(member.voice and voice and voice.channel == member.voice.channel)


def has_control_permission(
    member: discord.Member,
    requester_id: int | None,
    *,
    allow_requester: bool,
    dj_role_id: int | None = None,
) -> bool:
    privileged = member.guild_permissions.manage_guild or member.guild_permissions.move_members
    has_dj_role = any(
        role.id == dj_role_id if dj_role_id is not None else role.name.casefold() == "dj"
        for role in member.roles
    )
    return privileged or has_dj_role or (allow_requester and requester_id == member.id)
