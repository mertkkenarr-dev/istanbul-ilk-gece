"""Ortak grafik stili (docs/img). Yüzey/mürekkep/ızgara tonları ve kategorik sıra veri görselleştirme rehberinden."""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl

KOK = Path(__file__).resolve().parent.parent
YH = KOK / "data/processed/yer_hareketi"
IMG = KOK / "docs/img"; IMG.mkdir(parents=True, exist_ok=True)
YUZEY, MUREKKEP, IKINCIL, IZGARA = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
MAVI, TURUNCU = "#2a78d6", "#eb6834"
mpl.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": IZGARA, "axes.labelcolor": IKINCIL,
                     "xtick.color": IKINCIL, "ytick.color": IKINCIL, "axes.titlecolor": MUREKKEP, "figure.facecolor": YUZEY,
                     "axes.facecolor": YUZEY, "axes.grid": True, "grid.color": IZGARA, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "savefig.facecolor": YUZEY})
