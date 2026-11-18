"""Fluxo completo: imagem -> OCR -> matrículas -> máscara -> preenchimento."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np

from .inpaint import make_inpainter
from .mask import Region, build_mask, region_from_box
from .ocr import OcrReader, find_registrations


@dataclass
class RemovalResult:
    image: np.ndarray  # imagem BGR com as matrículas apagadas
    regions: list[Region] = field(default_factory=list)
    mask: np.ndarray | None = None


class RegistrationRemover:
    def __init__(self, engine: str = "auto", pad_ratio: float = 0.25) -> None:
        self.engine = engine
        self.pad_ratio = pad_ratio
        self._ocr: OcrReader | None = None
        self._inpainter = None

    # Carregamento preguiçoso: os modelos só são lidos na primeira chamada.
    def _ocr_reader(self) -> OcrReader:
        if self._ocr is None:
            self._ocr = OcrReader()
        return self._ocr

    def _get_inpainter(self):
        if self._inpainter is None:
            self._inpainter = make_inpainter(self.engine)
        return self._inpainter

    def detect(self, image_bgr: np.ndarray) -> list[Region]:
        """Só encontra as matrículas (não altera a imagem)."""
        boxes = self._ocr_reader().read(image_bgr)
        regions = []
        for group in find_registrations(boxes):
            regions.append(
                Region(
                    text=" ".join(b.text for b in group),
                    points=np.vstack([b.points for b in group]),
                    height=max(b.height for b in group),
                )
            )
        return regions

    def remove(
        self,
        image_bgr: np.ndarray,
        manual_boxes: Iterable[tuple[float, float, float, float]] = (),
    ) -> RemovalResult:
        """Apaga as matrículas detectadas e as regiões manuais `(x1, y1, x2, y2)`."""
        regions = self.detect(image_bgr)
        regions += [region_from_box(*box) for box in manual_boxes]
        if not regions:
            return RemovalResult(image=image_bgr.copy(), regions=[])

        mask = build_mask(image_bgr.shape, regions, self.pad_ratio)
        filled = self._get_inpainter()(image_bgr, mask)

        # Só troca os pixels da máscara: o resto da foto fica exatamente como estava.
        out = image_bgr.copy()
        out[mask > 0] = filled[mask > 0]
        return RemovalResult(image=out, regions=regions, mask=mask)
