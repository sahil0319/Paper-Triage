"""Keyword tags from a search topic (FR-021, R17): lowercase tokens, no stop words, no dupes."""

import string

_WORDS = (
    """a about above after again against all also am an and any are as at be because been before
    being below between both but by can could did do does doing down during each few for from
    further had has have having he her here hers him his how i if in into is it its just me more
    most my no nor not of off on once only or other our ours out over own same she should so some
    such than that the their theirs them then there these they this those through to too under
    until up very was we were what when where which while who whom why will with would you your
    yours via using use based"""
)
STOP_WORDS = frozenset(_WORDS.split())

_PUNCT = string.punctuation


def keywords(topic: str) -> list[str]:
    """Split on whitespace, strip surrounding punctuation, drop 1-char tokens and stop words."""
    out: list[str] = []
    for raw in topic.split():
        tok = raw.strip(_PUNCT + "‘’“”").lower()
        if len(tok) < 2 or tok in STOP_WORDS or tok in out:
            continue
        out.append(tok)
    return out
