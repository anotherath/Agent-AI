"""Expand UI selection chip directives into plain text for the LLM.

Stored message content may keep `:selection[label]{name=id}` so the FE can
render chips; the agent should never see that markup.
"""

from __future__ import annotations

import re

# assistant-ui defaultDirectiveFormatter serialize form
_SELECTION_DIRECTIVE = re.compile(
    r":selection\[(.*?)\]\{name=[^}]*\}",
    re.DOTALL,
)


def expand_selection_directives(text: str) -> str:
    """Turn selection chips into a readable excerpt + remaining question."""
    if not text or ":selection[" not in text:
        return text

    quotes: list[str] = []

    def _collect(match: re.Match[str]) -> str:
        label = " ".join(match.group(1).split()).strip()
        if label:
            quotes.append(label)
        return ""

    remainder = _SELECTION_DIRECTIVE.sub(_collect, text)
    question = " ".join(remainder.split()).strip()
    if not quotes:
        return text

    excerpt = "\n".join(f'"{q}"' for q in quotes)
    if not question:
        return f"Regarding this selected text:\n{excerpt}"
    return f"Regarding this selected text:\n{excerpt}\n\n{question}"


__all__ = ["expand_selection_directives"]
