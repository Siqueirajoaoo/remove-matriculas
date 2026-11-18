"""Leitura de texto na imagem (OCR) e agrupamento de trechos que formam uma matrícula."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .patterns import is_registration


@dataclass(eq=False)  # eq=False: compara por identidade (o campo `points` é um array)
class TextBox:
    text: str
    points: np.ndarray  # (4, 2): cantos do retângulo do texto, em pixels
    score: float

    @property
    def left(self) -> float:
        return float(self.points[:, 0].min())

    @property
    def right(self) -> float:
        return float(self.points[:, 0].max())

    @property
    def top(self) -> float:
        return float(self.points[:, 1].min())

    @property
    def bottom(self) -> float:
        return float(self.points[:, 1].max())

    @property
    def height(self) -> float:
        return max(self.bottom - self.top, 1.0)

    @property
    def cy(self) -> float:
        return float(self.points[:, 1].mean())


class OcrReader:
    """Lê os textos da imagem com RapidOCR (modelos ONNX, roda na CPU sem PyTorch)."""

    def __init__(self) -> None:
        from rapidocr_onnxruntime import RapidOCR  # import tardio: só quando for usar

        self._engine = RapidOCR()

    def read(self, image_bgr: np.ndarray) -> list[TextBox]:
        result, _elapsed = self._engine(image_bgr)
        boxes = []
        for box, txt, score in result or []:
            boxes.append(
                TextBox(
                    text=str(txt),
                    points=np.asarray(box, dtype=np.float32),
                    score=float(score),
                )
            )
        return boxes


def _next_part(last: TextBox, boxes: list[TextBox], chain: list[TextBox]) -> TextBox | None:
    """Acha o trecho de texto que vem logo à direita de `last`, na mesma linha."""
    in_chain = {id(b) for b in chain}
    best: TextBox | None = None
    for b in boxes:
        if id(b) in in_chain or b.left <= last.left:
            continue
        line_h = max(last.height, b.height)
        same_line = abs(b.cy - last.cy) < 0.5 * line_h
        gap = b.left - last.right
        close = -0.3 * line_h <= gap <= 1.0 * line_h
        if same_line and close and (best is None or b.left < best.left):
            best = b
    return best


def find_registrations(boxes: list[TextBox], max_parts: int = 3) -> list[list[TextBox]]:
    """Retorna grupos de caixas de texto que, lidas em conjunto, formam uma matrícula.

    Um grupo tem 1 caixa na maioria dos casos. Quando o OCR quebra a matrícula em
    pedaços (ex.: "PT" + "ABC"), juntamos até `max_parts` caixas vizinhas na mesma linha.
    """
    groups: list[list[TextBox]] = []
    seen: set[frozenset[int]] = set()

    for start in sorted(boxes, key=lambda b: (b.cy, b.left)):
        # Caso comum: a caixa inteira é a matrícula, ou contém só a matrícula
        # junto de outra palavra (ex.: "MATRICULA PT-ABC" numa única caixa).
        if is_registration(start.text) or any(is_registration(tok) for tok in start.text.split()):
            key = frozenset([id(start)])
            if key not in seen:
                seen.add(key)
                groups.append([start])
            continue

        chain = [start]
        while len(chain) < max_parts:
            nxt = _next_part(chain[-1], boxes, chain)
            if nxt is None:
                break
            chain.append(nxt)
            concat = "".join(b.text for b in chain)
            dashed = "-".join(b.text for b in chain)
            if is_registration(concat) or is_registration(dashed):
                key = frozenset(id(b) for b in chain)
                if key not in seen:
                    seen.add(key)
                    groups.append(list(chain))
                break

    return groups
