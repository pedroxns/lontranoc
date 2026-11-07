"""Filtro de linguagem das personas "família" (`family_friendly: true`).

O prompt pede à persona para não xingar, mas modelo de linguagem não obedece
sempre. Este filtro é a rede de segurança determinística: palavrões e
interjeições grosseiras são trocados por palavras neutras antes de a resposta
ser mostrada ou falada. É um melhor esforço, não uma garantia absoluta, e só
vale para personas que ligam a opção.

Casa palavras inteiras, sem diferenciar maiúsculas de minúsculas ("Porra!" e
"PORRA" caem; "porrada" e "sacola" não).
"""

from __future__ import annotations

import re

# Frases antes das palavras soltas.
_PHRASES: tuple[tuple[str, str], ...] = (
    ("que saco", "que chato"),
    ("seu saco", "seu chato"),
    ("puta merda", "nossa"),
)

_WORDS: dict[str, str] = {
    "droga": "poxa",
    "drogas": "poxas",
    "merda": "bagunça",
    "merdas": "bagunças",
    "porra": "poxa",
    "caralho": "nossa",
    "caralhos": "nossa",
    "bosta": "bagunça",
    "cacete": "poxa",
    "puta": "tremenda",
    "putas": "tremendas",
    "foda": "complicado",
    "foder": "complicar",
    "fodido": "complicado",
    "fodida": "complicada",
    "fdp": "chato",
    "diabos": "nossa",
    "inferno": "nossa",
}

_EDGE = r"(?<![\wÀ-ÿ])", r"(?![\wÀ-ÿ])"
_PATTERN = re.compile(
    _EDGE[0]
    + "("
    + "|".join(re.escape(item) for item in sorted([*dict(_PHRASES), *_WORDS], key=len, reverse=True))
    + ")"
    + _EDGE[1],
    re.IGNORECASE,
)
_REPLACEMENTS = {**dict(_PHRASES), **_WORDS}


def _swap(match: re.Match[str]) -> str:
    original = match.group(1)
    replacement = _REPLACEMENTS[original.lower()]

    if original.isupper() and len(original) > 1:
        return replacement.upper()

    if original[0].isupper():
        return replacement[0].upper() + replacement[1:]

    return replacement


def soften(text: str) -> str:
    """Troca palavrões por palavras neutras, mantendo a pontuação e as maiúsculas."""

    return _PATTERN.sub(_swap, text)
