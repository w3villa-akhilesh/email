import re
from typing import Literal


Mode = Literal["web", "slack", "whatsapp"]


def _compress(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text or "").strip()


def _basic_markdown_to_channel(text: str) -> str:
    """Minimal, readable conversion for Slack/WhatsApp."""
    if not text:
        return ""

    # Links: [text](url) -> text (url)
    text = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r"\1 (\2)", text)

    # Italic first: single *...* or _..._ -> _..._
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"_\1_", text)
    text = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"_\1_", text)

    # Bold after italics: **bold** -> *bold* (so it won't be re-italicized)
    text = re.sub(r"\*\*([^*]+)\*\*", r"*\1*", text)

    # Remove code fences, keep content; inline code -> content
    text = re.sub(r"```[a-zA-Z0-9_+-]*\n([\s\S]*?)```", lambda m: "\n" + m.group(1).strip("\n") + "\n", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Strip heading markers; keep title, add simple emphasis
    text = re.sub(r"^\s*#{1,6}\s*(.+)$", r"*\1*", text, flags=re.MULTILINE)

    return text


def format_response_for_mode(text: str, mode: Mode) -> str:
    mode = (mode or "web").lower()
    if mode == "web":
        return _compress(text)
    if mode in ("slack", "whatsapp"):
        return _compress(_basic_markdown_to_channel(text))
    return _compress(text)


__all__ = ["format_response_for_mode"]
