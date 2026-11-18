"""Linha de comando.

Exemplos:
    python -m remover.cli foto.jpg
    python -m remover.cli fotos/*.jpg -o saida/
    python -m remover.cli foto.jpg --apenas-detectar
    python -m remover.cli foto.jpg --box 100,200,380,260   # região manual (x1,y1,x2,y2)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

from .pipeline import RegistrationRemover


def _parse_box(value: str) -> tuple[float, float, float, float]:
    parts = value.split(",")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("use o formato x1,y1,x2,y2")
    try:
        x1, y1, x2, y2 = (float(p) for p in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("coordenadas precisam ser números") from exc
    return x1, y1, x2, y2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Remove matrículas de aeronaves em imagens.")
    parser.add_argument("imagens", nargs="+", type=Path, help="uma ou mais imagens")
    parser.add_argument("-o", "--saida", type=Path, default=Path("saida"), help="pasta de saída")
    parser.add_argument(
        "--engine",
        choices=["auto", "lama", "opencv"],
        default="auto",
        help="motor de preenchimento (auto = LaMa se instalado, senão OpenCV)",
    )
    parser.add_argument(
        "--box",
        action="append",
        type=_parse_box,
        default=[],
        metavar="x1,y1,x2,y2",
        help="região extra a apagar (pode repetir)",
    )
    parser.add_argument(
        "--apenas-detectar",
        action="store_true",
        help="só lista as matrículas encontradas, sem gerar imagem",
    )
    parser.add_argument(
        "--pad", type=float, default=0.25, help="margem extra, proporcional à altura do texto"
    )
    args = parser.parse_args(argv)

    remover = RegistrationRemover(engine=args.engine, pad_ratio=args.pad)
    if not args.apenas_detectar:
        args.saida.mkdir(parents=True, exist_ok=True)

    status = 0
    for path in args.imagens:
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            print(f"[erro] não consegui abrir {path}", file=sys.stderr)
            status = 1
            continue

        if args.apenas_detectar:
            regions = remover.detect(image)
            if not regions:
                print(f"{path.name}: nenhuma matrícula encontrada")
            for region in regions:
                print(f"{path.name}: {region.text!r} bbox={region.bbox()}")
            continue

        result = remover.remove(image, manual_boxes=args.box)
        out_path = args.saida / f"{path.stem}_sem_matricula.png"
        cv2.imwrite(str(out_path), result.image)
        print(f"{path.name}: {len(result.regions)} região(ões) apagada(s) -> {out_path}")

    return status


if __name__ == "__main__":
    sys.exit(main())
