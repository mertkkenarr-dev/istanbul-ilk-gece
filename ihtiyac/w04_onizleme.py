"""Faz A önizlemesi (siteden bağımsız): bina yükseklikleri, toplanma akışı, ilçe çıkışı. Çıktı: docs/img/faz_a_onizleme.png"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from shapely.geometry import shape

KOK = Path(__file__).resolve().parents[1]
P = KOK / "data/processed"; T = P / "web_tiles"
ZEMIN, MUREKKEP, SOLUK, AMBER, KIRMIZI, MAVI = "#0e1218", "#ebe7df", "#5b6573", "#f3aa40", "#e5534b", "#8fb8de"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "text.color": MUREKKEP, "axes.facecolor": ZEMIN,
                     "figure.facecolor": ZEMIN, "axes.edgecolor": ZEMIN})

s = gpd.read_parquet(P.parent / "interim/mahalle_sinir.parquet").to_crs(4326)
tg = s[s.uavt == 181502].geometry.iloc[0]
cx, cy = tg.centroid.x, tg.centroid.y
fig, ax = plt.subplots(1, 3, figsize=(17, 6))

b = gpd.read_parquet(T / "binalar.parquet")
b = b.cx[cx - 0.016: cx + 0.016, cy - 0.012: cy + 0.012]
b.plot(ax=ax[0], column="h", cmap="magma", vmin=0, vmax=45, linewidth=0, legend=True, legend_kwds={"shrink": 0.6, "label": "yükseklik (m)"})
gpd.GeoSeries([tg]).boundary.plot(ax=ax[0], color=MAVI, linewidth=1.4)
ax[0].set_title(f"1 · Turgut Özal çevresi: {len(b):,} bina; gerçek yükseklik %{100 * (b.kaynak != 'tahmin').mean():.0f}, gerisi tahmin", loc="left")

a = json.loads((T / "toplanma_akis.json").read_text())
ak = np.array(a["akis"]); ys = np.array(a["yersiz"]); al = np.array(a["alan"])
pen = (cx - 0.11, cx + 0.11, cy - 0.07, cy + 0.07)
lc = LineCollection([[(r[0], r[1]), (r[2], r[3])] for r in ak], linewidths=0.3 + 1.5 * np.sqrt(ak[:, 4] / ak[:, 4].max()), colors=AMBER, alpha=0.55)
ax[1].add_collection(lc)
dolu = al[:, 3] >= 0.99 * al[:, 2]
ax[1].scatter(al[:, 0], al[:, 1], s=4 + 60 * np.sqrt(al[:, 2] / al[:, 2].max()), c=np.where(dolu, MUREKKEP, SOLUK), zorder=3, linewidths=0)
ax[1].scatter(ys[:, 0], ys[:, 1], s=2 + 40 * np.sqrt(ys[:, 2] / ys[:, 2].max()), c=KIRMIZI, alpha=0.7, zorder=4, linewidths=0)
gpd.GeoSeries([tg]).boundary.plot(ax=ax[1], color=MAVI, linewidth=1.2)
ax[1].set_xlim(pen[0], pen[1]); ax[1].set_ylim(pen[2], pen[3])
ax[1].set_title("2 · Toplanma akışı (turuncu), yer bulamayan (kırmızı), dolu alan (beyaz)", loc="left")

c = json.loads((T / "ilce_cikis.json").read_text())
gpd.GeoSeries([shape(c["sinir"])]).boundary.plot(ax=ax[2], color=SOLUK, linewidth=1)
for r in c["cikis"]:
    y = np.array(r["yol"]); ax[2].plot(y[:, 0], y[:, 1], color=AMBER, linewidth=0.6 + r["kap"] / 1500)
ax[2].set_title(f"3 · Esenyurt'tan çıkış: {c['toplam_kap']:,} araç/sa kapasite, {c['arac'][0]:,.0f}–{c['arac'][1]:,.0f} araç", loc="left")
for a_ in ax:
    a_.set_xticks([]); a_.set_yticks([]); a_.set_aspect(1 / np.cos(np.radians(41)))
fig.tight_layout(); fig.savefig(KOK / "docs/img/faz_a_onizleme.png", dpi=150)
