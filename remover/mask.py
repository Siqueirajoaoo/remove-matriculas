"""Regiões a apagar e geração da máscara binária usada no preenchimento."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Region:
    text: str  # texto lido pelo OCR (ou "(manual)")
    points: np.ndarray  # (N, 2) pontos do contorno do texto
    height: float  # altura típica do texto, usada para calcular a margem

    def bbox(self) -> tuple[int, int, int, int]:
        x1, y1 = self.points.min(axis=0)
        x2, y2 = self.points.max(axis=0)
        return int(x1), int(y1), int(x2), int(y2)


def region_from_box(x1: float, y1: float, x2: float, y2: float) -> Region:
    """Cria uma região manual a partir de um retângulo (qualquer ordem dos cantos)."""
    left, right = sorted((float(x1), float(x2)))
    top, bottom = sorted((float(y1), float(y2)))
    points = np.array(
        [[left, top], [right, top], [right, bottom], [left, bottom]], dtype=np.float32
    )
    return Region(text="(manual)", points=points, height=max(bottom - top, 1.0))


def build_mask(shape: tuple[int, ...], regions: list[Region], pad_ratio: float = 0.25) -> np.ndarray:
    """Máscara 0/255 (255 = pixel a ser preenchido).

    Cada região é preenchida com o casco convexo dos seus pontos e depois
    expandida em `pad_ratio * altura` pixels, para cobrir bordas e sombras do texto.
    """
    h, w = shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    for region in regions:
        layer = np.zeros_like(mask)
        hull = cv2.convexHull(np.round(region.points).astype(np.int32))
        cv2.fillConvexPoly(layer, hull, 255)
        k = max(2, int(round(region.height * pad_ratio)))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))
        layer = cv2.dilate(layer, kernel)
        mask = cv2.bitwise_or(mask, layer)
    return mask
