"""Padrões de matrícula (registration) de aeronaves.

Exemplos aceitos:
  - Brasil:   PT-ABC, PP-XYZ, PR-ABC, PS-ABC, PT-XYZ ...
  - Outros:   G-ABCD (Reino Unido), D-EABC (Alemanha), F-GXYZ (França),
              VH-ABC (Austrália), 9M-ABC (Malásia), EC-MXY (Espanha) ...
  - EUA:      N12345, N123AB, N1A

Para adicionar outros formatos, acrescente um regex em DASHED_PATTERN / US_PATTERN.
"""

import re

# Traços tipográficos que o OCR costuma devolver no lugar do hífen comum.
_DASH_VARIANTS = re.compile(r"[‐-―−﹘﹣－]")
# Espaços e pontuação que aparecem no meio/fim do texto lido.
_NOISE = re.compile(r"[\s.,:;|_'\"`()\[\]]+")

# Prefixo de 1-2 caracteres, hífen, sufixo de 3-5 caracteres (a checagem de
# "pelo menos uma letra no sufixo" é feita em is_registration).
DASHED_PATTERN = re.compile(r"^[A-Z0-9]{1,2}-[A-Z0-9]{3,5}$")

# Matrículas americanas: N seguido de números e até duas letras.
US_PATTERN = re.compile(r"^N[1-9][0-9]{0,4}[A-Z]{0,2}$")


def normalize(text: str) -> str:
    """Coloca o texto em maiúsculas, troca traços exóticos por '-' e remove espaços/pontuação."""
    text = _DASH_VARIANTS.sub("-", text.upper())
    return _NOISE.sub("", text)


def is_registration(text: str) -> bool:
    """True se o texto (já lido por OCR) tem cara de matrícula de aeronave."""
    value = normalize(text)
    if not value:
        return False
    if US_PATTERN.match(value):
        return True
    if not DASHED_PATTERN.match(value):
        return False
    suffix = value.split("-", 1)[1]
    # "F-16", "A-320", "B-52" são modelos de avião, não matrículas.
    return any(ch.isalpha() for ch in suffix)
