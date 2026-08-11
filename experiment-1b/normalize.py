#!/usr/bin/env python3
"""Deterministic word-surface normalization for Experiment 1B."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

NORMALIZATION_VERSION = "q1b-norm-v1"


@dataclass(frozen=True)
class Variant:
    name: str
    lowercase: bool
    strip_punctuation: bool


VARIANTS = {
    "original": Variant("original", lowercase=False, strip_punctuation=False),
    "lower": Variant("lower", lowercase=True, strip_punctuation=False),
    "nopunct": Variant("nopunct", lowercase=False, strip_punctuation=True),
    "lower_nopunct": Variant(
        "lower_nopunct", lowercase=True, strip_punctuation=True
    ),
}


def normalize_word(
    word: str, *, lowercase: bool = False, strip_punctuation: bool = False
) -> str:
    """Normalize one whitespace-delimited source word without changing its index."""
    rendered = word.lower() if lowercase else word
    if strip_punctuation:
        rendered = "".join(
            character
            for character in rendered
            if not unicodedata.category(character).startswith("P")
        )
    return rendered

def normalize_words(words: list[str], variant_name: str) -> list[str]:
    """Render source words for a named variant, failing if stride would collapse."""
    try:
        variant = VARIANTS[variant_name]
    except KeyError as exc:
        raise ValueError(f"unknown normalization variant: {variant_name}") from exc
    rendered = [
        normalize_word(
            word,
            lowercase=variant.lowercase,
            strip_punctuation=variant.strip_punctuation,
        )
        for word in words
    ]
    empty = [index for index, word in enumerate(rendered) if not word]
    if empty:
        raise ValueError(
            "normalization produced empty lexical units at source indices "
            + ", ".join(str(index) for index in empty)
            + "; this experiment fails rather than dropping units and changing stride"
        )
    return rendered
