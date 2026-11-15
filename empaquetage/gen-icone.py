#!/usr/bin/env python3
"""Icône de l'Observatoire : une courbe de cours en cercles, comme dans l'application.

Usage : python3 gen-icone.py DOSSIER   → DOSSIER/icon-256.png et icon-512.png
Rendu suréchantillonné puis réduit (LANCZOS) ; déterministe, sans police ni réseau.
Couleurs reprises des jetons de la page (--green #24735e, --paper, --ink).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

PAPER, INK, GREEN, GOLD, LINE = (255, 255, 255), (32, 46, 42), (36, 115, 94), (196, 154, 46), (227, 232, 226)
# Monthly-like path, rising with two drawdowns: the app's subject, not a logo.
PATH = [0.22, 0.30, 0.26, 0.38, 0.45, 0.40, 0.52, 0.47, 0.60, 0.72, 0.66, 0.80]


def render(size, ss=4):
    n = size * ss
    img = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = n * 0.18
    d.rounded_rectangle([n * .04, n * .04, n * .96, n * .96], radius=r, fill=GREEN)
    # White plot frame, closed on four sides (convention of the app's figures).
    x0, y0, x1, y1 = n * .17, n * .19, n * .83, n * .81
    d.rounded_rectangle([x0, y0, x1, y1], radius=n * .03, fill=PAPER)
    for k in range(1, 4):
        y = y0 + (y1 - y0) * k / 4
        d.line([x0 + n * .02, y, x1 - n * .02, y], fill=LINE, width=max(1, n // 160))
    pts = [(x0 + n * .06 + (x1 - x0 - n * .12) * i / (len(PATH) - 1),
            y1 - n * .06 - (y1 - y0 - n * .12) * v) for i, v in enumerate(PATH)]
    d.line(pts, fill=INK, width=max(2, n // 70), joint='curve')
    rad = n * .022
    for i, (x, y) in enumerate(pts):
        fill = GOLD if i == len(pts) - 1 else PAPER
        d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=fill, outline=INK, width=max(2, n // 110))
    return img.resize((size, size), Image.LANCZOS)


if __name__ == '__main__':
    out = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
    out.mkdir(parents=True, exist_ok=True)
    for size in (256, 512):
        render(size).save(out / f'icon-{size}.png', optimize=True)
    print(out / 'icon-256.png')
