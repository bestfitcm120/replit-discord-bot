"""
Generates a leaderboard image for the /top command using Pillow.
Returns a discord.File ready to attach to a message.
"""
from __future__ import annotations

import asyncio
import io
from typing import Optional

import aiohttp
import discord
from PIL import Image, ImageDraw, ImageFont

# ── Colour palette (Discord dark theme) ───────────────────────────────────────
BG = (30, 31, 34)
PANEL = (47, 49, 54)
DIVIDER = (60, 63, 70)
WHITE = (220, 221, 222)
MUTED = (148, 155, 164)
ACCENT = (88, 101, 242)   # Discord blurple
GOLD = (255, 193, 7)
SILVER = (192, 192, 192)
BRONZE = (176, 111, 59)

RANK_COLORS = [GOLD, SILVER, BRONZE, MUTED, MUTED]
RANK_LABELS = ["1", "2", "3", "4", "5"]

# ── Layout constants ───────────────────────────────────────────────────────────
PAD = 20
COL_GAP = 14
ROW_H = 64
AVATAR_SIZE = 44
HEADER_H = 52
FOOTER_H = 36


def _load_fonts():
    try:
        title_font = ImageFont.load_default(size=17)
        name_font = ImageFont.load_default(size=15)
        small_font = ImageFont.load_default(size=13)
        rank_font = ImageFont.load_default(size=14)
        return title_font, name_font, small_font, rank_font
    except TypeError:
        # Pillow < 10.1 fallback
        f = ImageFont.load_default()
        return f, f, f, f


async def _fetch_avatar(session: aiohttp.ClientSession, url: Optional[str]) -> Optional[Image.Image]:
    if not url:
        return None
    try:
        async with session.get(url + "?size=64&format=png",
                               timeout=aiohttp.ClientTimeout(total=4)) as resp:
            if resp.status == 200:
                data = await resp.read()
                img = Image.open(io.BytesIO(data)).convert("RGBA")
                return img.resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
    except Exception:
        pass
    return None


def _paste_circle(canvas: Image.Image, avatar: Optional[Image.Image],
                  x: int, y: int, fallback_letter: str, draw: ImageDraw.ImageDraw) -> None:
    size = AVATAR_SIZE
    if avatar:
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
        canvas.paste(avatar, (x, y), mask)
    else:
        draw.ellipse([x, y, x + size - 1, y + size - 1], fill=ACCENT)
        try:
            f = ImageFont.load_default(size=18)
        except TypeError:
            f = ImageFont.load_default()
        draw.text((x + size // 2, y + size // 2), fallback_letter.upper(),
                  font=f, fill=WHITE, anchor="mm")


async def generate_top_image(
    guild: discord.Guild,
    text_rows: list,
    voice_rows: list,
) -> discord.File:
    title_font, name_font, small_font, rank_font = _load_fonts()

    num_rows = max(len(text_rows), len(voice_rows), 1)
    total_h = PAD + HEADER_H + num_rows * ROW_H + PAD + FOOTER_H
    total_w = 760

    col_w = (total_w - PAD * 2 - COL_GAP) // 2

    canvas = Image.new("RGB", (total_w, total_h), BG)
    draw = ImageDraw.Draw(canvas)

    # ── Section panels ─────────────────────────────────────────────────────────
    left_x = PAD
    right_x = PAD + col_w + COL_GAP

    for px in (left_x, right_x):
        draw.rounded_rectangle(
            [px, PAD, px + col_w, PAD + HEADER_H + num_rows * ROW_H],
            radius=10, fill=PANEL,
        )

    # ── Section headers ────────────────────────────────────────────────────────
    draw.text((left_x + col_w // 2, PAD + HEADER_H // 2),
              "TOP TEXT CHATTERS", font=title_font, fill=ACCENT, anchor="mm")
    draw.text((right_x + col_w // 2, PAD + HEADER_H // 2),
              "TOP VOICE MEMBERS", font=title_font, fill=ACCENT, anchor="mm")

    # ── Fetch all avatars concurrently ─────────────────────────────────────────
    def avatar_url(row) -> Optional[str]:
        member = guild.get_member(int(row["user_id"]))
        return member.display_avatar.url if member else None

    def member_name(row) -> str:
        member = guild.get_member(int(row["user_id"]))
        if member:
            name = member.display_name
        else:
            name = f"User {str(row['user_id'])[:6]}"
        return name[:18] + "…" if len(name) > 18 else name

    async with aiohttp.ClientSession() as session:
        text_avatar_tasks = [_fetch_avatar(session, avatar_url(r)) for r in text_rows]
        voice_avatar_tasks = [_fetch_avatar(session, avatar_url(r)) for r in voice_rows]
        text_avatars, voice_avatars = await asyncio.gather(
            asyncio.gather(*text_avatar_tasks),
            asyncio.gather(*voice_avatar_tasks),
        )

    # ── Draw rows ──────────────────────────────────────────────────────────────
    def draw_rows(x: int, rows: list, avatars: list, xp_key: str, level_key: str) -> None:
        for i, row in enumerate(rows):
            y = PAD + HEADER_H + i * ROW_H
            # Divider
            if i > 0:
                draw.line([(x + 10, y), (x + col_w - 10, y)], fill=DIVIDER, width=1)

            rank_color = RANK_COLORS[i] if i < len(RANK_COLORS) else MUTED
            label = RANK_LABELS[i] if i < len(RANK_LABELS) else f"{i+1}"

            # Rank circle
            rc_x, rc_y = x + 14, y + ROW_H // 2 - 12
            draw.ellipse([rc_x, rc_y, rc_x + 24, rc_y + 24], fill=rank_color)
            draw.text((rc_x + 12, rc_y + 12), label, font=rank_font, fill=BG, anchor="mm")

            # Avatar
            av_x = x + 46
            av_y = y + (ROW_H - AVATAR_SIZE) // 2
            avatar = avatars[i] if i < len(avatars) else None
            name = member_name(row)
            _paste_circle(canvas, avatar, av_x, av_y, name[0], draw)

            # Name + stats
            text_x = av_x + AVATAR_SIZE + 10
            text_y_name = y + ROW_H // 2 - 12
            text_y_stat = y + ROW_H // 2 + 4
            draw.text((text_x, text_y_name), name, font=name_font, fill=WHITE)
            draw.text((text_x, text_y_stat),
                      f"Level {row[level_key]}  ·  {row[xp_key]:,} XP",
                      font=small_font, fill=MUTED)

    draw_rows(left_x, text_rows, list(text_avatars), "text_xp", "text_level")
    draw_rows(right_x, voice_rows, list(voice_avatars), "voice_xp", "voice_level")

    # ── Footer ─────────────────────────────────────────────────────────────────
    footer_y = PAD + HEADER_H + num_rows * ROW_H + FOOTER_H // 2 + 4
    draw.text((total_w // 2, footer_y),
              f"{guild.name}  ·  use /rank to see your stats",
              font=small_font, fill=MUTED, anchor="mm")

    # ── Encode and return ──────────────────────────────────────────────────────
    buf = io.BytesIO()
    canvas.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return discord.File(buf, filename="leaderboard.png")
