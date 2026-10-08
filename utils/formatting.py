"""Shared display helpers."""
import re

import discord


def star_bar(avg_rating: float) -> str:
    """Render a 1-10 rating as a five-star bar, e.g. ⭐⭐⭐✨☆."""
    star_rating = avg_rating / 2
    full_stars = int(star_rating)
    half_star = 1 if (star_rating - full_stars) >= 0.5 else 0
    empty_stars = 5 - full_stars - half_star
    return "⭐" * full_stars + ("✨" if half_star else "") + "☆" * empty_stars


def review_stars(rating: int) -> str:
    """Compact stars for a single review (one star per two points)."""
    return "⭐" * (rating // 2) + ("✨" if rating % 2 else "")


def generate_star_rating(avg_rating: float, total_reviews: int) -> str | None:
    if total_reviews == 0:
        return None
    plural = "s" if total_reviews != 1 else ""
    return f"Rating: {star_bar(avg_rating)} ({avg_rating:.1f}/10 from {total_reviews} review{plural})"


def capped_lines(lines: list[str], limit: int = 1024) -> str:
    """
    Join lines for an embed field, stopping before Discord's length limit
    and noting how many entries were left out.
    """
    shown: list[str] = []
    for i, line in enumerate(lines):
        remaining = len(lines) - i
        suffix = f"\n• … and {remaining} more"
        if len("\n".join(shown + [line])) + len(suffix) > limit:
            shown.append(suffix.strip())
            break
        shown.append(line)
    return "\n".join(shown) or "None"


def safe_inline(text: str, limit: int) -> str:
    """
    Make user-written text safe to show inside the bot's embeds: one line,
    shortened to `limit` characters, with markdown and link brackets escaped
    so it can't fake extra review lines or hide a link behind other text.
    """
    text = " ".join(text.split())
    if len(text) > limit:
        text = text[:limit] + "..."
    text = discord.utils.escape_markdown(text)
    # escape_markdown handles some brackets itself; escape any it left alone
    return re.sub(r"(?<!\\)([\[\]])", r"\\\1", text)
