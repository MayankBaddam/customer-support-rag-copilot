from __future__ import annotations

import re

TOKEN_PATTERN = re.compile(r"\S+")


def tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text)


def count_tokens(text: str) -> int:
    return len(tokenize(text))