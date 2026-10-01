"""Parse the single user input into (topic, items) per contracts/api.md."""

import re
from typing import NamedTuple
from urllib.parse import urlparse

_NEW_ID = r"\d{4}\.\d{4,5}"
_OLD_ID = r"[a-z\-]+(?:\.[A-Z]{2})?/\d{7}"
_ID = re.compile(rf"^(?:arxiv:)?({_NEW_ID}|{_OLD_ID})(?:v\d+)?$", re.IGNORECASE)
_ARXIV_URL = re.compile(rf"^/(?:abs|pdf)/({_NEW_ID}|{_OLD_ID})(?:v\d+)?(?:\.pdf)?$")
_ARXIV_HOSTS = {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}


class Item(NamedTuple):
    kind: str  # "arxiv" (normalized id, no version) | "pdf" (direct URL)
    value: str


def _item(token: str) -> Item | None:
    if re.match(r"^https?://", token, re.IGNORECASE):
        u = urlparse(token)
        if u.hostname and u.hostname.lower() in _ARXIV_HOSTS:
            m = _ARXIV_URL.match(u.path)
            if m:
                return Item("arxiv", m.group(1))
        return Item("pdf", token)
    m = _ID.match(token)
    return Item("arxiv", m.group(1)) if m else None


def parse_query(q: str) -> tuple[str, list[Item]]:
    tokens = [t for t in re.split(r"[\s,]+", q) if t]
    if not tokens:
        raise ValueError("empty query")
    words: list[str] = []
    items: list[Item] = []
    for t in tokens:
        it = _item(t)
        if it is None:
            words.append(t)
        elif it not in items:
            items.append(it)
    return " ".join(words), items
