"""Interface web: envie uma foto de avião e receba a mesma foto sem matrícula.

Rodar:
    uvicorn app:app --reload
Depois abra http://127.0.0.1:8000
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import threading
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from starlette.concurrency import run_in_threadpool

from remover import RegistrationRemover

MAX_BYTES = 25 * 1024 * 1024
INDEX_HTML = Path(__file__).parent / "static" / "index.html"
# Se REMOVER_PASSWORD estiver definida, o site pede usuário/senha (qualquer usuário, esta senha).
PASSWORD = os.getenv("REMOVER_PASSWORD", "")

app = FastAPI(title="Remove Matrículas")


@app.middleware("http")
async def require_password(request: Request, call_next):
    if PASSWORD:
        header = request.headers.get("authorization", "")
        ok = False
        if header.startswith("Basic "):
            try:
                decoded = base64.b64decode(header[6:]).decode("utf-8")
                _, _, given = decoded.partition(":")
                ok = secrets.compare_digest(given, PASSWORD)
            except (ValueError, UnicodeDecodeError):
                ok = False
        if not ok:
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="Remove Matriculas"'},
                content="Senha necessária.",
            )
    return await call_next(request)
_remover: RegistrationRemover | None = None
_init_lock = threading.Lock()  # evita carregar os modelos duas vezes
_lock = threading.Lock()  # um processamento por vez (OCR/LaMa não são pensados para paralelo)


def _get_remover() -> RegistrationRemover:
    global _remover
    with _init_lock:
        if _remover is None:
            _remover = RegistrationRemover(engine=os.getenv("REMOVER_ENGINE", "auto"))
        return _remover


async def _read_image(file: UploadFile) -> np.ndarray:
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Imagem maior que 25 MB.")
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="O arquivo enviado não é uma imagem válida.")
    return image


def _parse_boxes(raw: str) -> list[tuple[float, float, float, float]]:
    try:
        items = json.loads(raw or "[]")
        boxes = [tuple(float(v) for v in item) for item in items]
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail='boxes deve ser uma lista JSON: [[x1, y1, x2, y2], ...]',
        ) from exc
    if any(len(b) != 4 for b in boxes):
        raise HTTPException(status_code=400, detail="Cada região precisa de 4 valores.")
    return boxes


@app.get("/")
def index() -> FileResponse:
    return FileResponse(INDEX_HTML)


@app.post("/api/remove")
async def remove(
    file: UploadFile = File(...),
    boxes: str = Form("[]", description="Regiões manuais extras: [[x1,y1,x2,y2], ...]"),
) -> Response:
    image = await _read_image(file)
    manual = _parse_boxes(boxes)

    def process():
        with _lock:
            return _get_remover().remove(image, manual_boxes=manual)

    result = await run_in_threadpool(process)
    ok, buffer = cv2.imencode(".png", result.image)
    if not ok:
        raise HTTPException(status_code=500, detail="Falha ao codificar a imagem de saída.")
    return Response(
        content=buffer.tobytes(),
        media_type="image/png",
        headers={"X-Regions-Removed": str(len(result.regions))},
    )


@app.post("/api/detect")
async def detect(file: UploadFile = File(...)) -> dict:
    """Só lista as matrículas encontradas, sem alterar a imagem."""
    image = await _read_image(file)

    def process():
        with _lock:
            return _get_remover().detect(image)

    regions = await run_in_threadpool(process)
    return {
        "registrations": [{"text": r.text, "box": list(r.bbox())} for r in regions],
    }
