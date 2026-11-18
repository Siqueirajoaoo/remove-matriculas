"""Motores de preenchimento: apagam a área da máscara reconstruindo o fundo."""

from __future__ import annotations

import logging

import cv2
import numpy as np

log = logging.getLogger(__name__)


class OpenCVInpainter:
    """Telea (OpenCV). Leve e sem download, mas o resultado é borrado em áreas grandes."""

    name = "opencv"

    def __call__(self, image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        return cv2.inpaint(image_bgr, mask, 7, cv2.INPAINT_TELEA)


class LamaInpainter:
    """LaMa via `simple-lama-inpainting` (PyTorch). Melhor qualidade; baixa ~200 MB de pesos na 1ª vez."""

    name = "lama"

    def __init__(self) -> None:
        from simple_lama_inpainting import SimpleLama  # ImportError se não estiver instalado

        self._model = SimpleLama()

    def __call__(self, image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        from PIL import Image

        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        out = self._model(Image.fromarray(rgb), Image.fromarray(mask).convert("L"))
        result = np.array(out.convert("RGB"))
        if result.shape[:2] != image_bgr.shape[:2]:
            result = cv2.resize(result, (image_bgr.shape[1], image_bgr.shape[0]))
        return cv2.cvtColor(result, cv2.COLOR_RGB2BGR)


def make_inpainter(engine: str = "auto"):
    """engine: 'lama' (obrigatório), 'opencv', ou 'auto' (LaMa se disponível, senão OpenCV)."""
    if engine not in ("auto", "lama", "opencv"):
        raise ValueError(f"engine inválido: {engine!r}")
    if engine in ("auto", "lama"):
        try:
            return LamaInpainter()
        except ImportError:
            if engine == "lama":
                raise
            log.warning(
                "simple-lama-inpainting não instalado; usando OpenCV (qualidade menor). "
                "Para instalar: pip install -r requirements-lama.txt"
            )
    return OpenCVInpainter()
