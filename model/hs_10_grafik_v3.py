"""Kalibrasyon v1 → v3 doğrulama grafiği: dört gerçek deprem, gözlem ve üç model sürümünün tahmini (ölü, log ölçek).
v1 2023'ü hiç görmedi (örneklem dışı sınama, sinama/s02); v2 ve v3 onu kalibrasyonda kullanır. Çıktı: docs/img/hs_kalibrasyon_v3.png
"""
from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from stil import IKINCIL, IMG, KOK, MAVI, MUREKKEP, TURUNCU

HS = KOK / "data/processed/hasar"
k1 = pd.read_parquet(HS / "kalibrasyon.parquet"); w1 = k1.agirlik / k1.agirlik.sum()
v1 = {"s25": (k1.s25_olu_k * w1).sum(), "i99": (k1.i99_olu_k * w1).sum(), "b99": (k1.b99_olu_k * w1).sum(),
      "m23": json.loads((KOK / "data/processed/sinama/maras2023_sonuc.json").read_text())["temel/posterior"]["olu_ort"]}
v2 = {k: v[0] for k, v in json.loads((HS / "kalibrasyon_v2.json").read_text())["tahmin_vs_gozlem"].items()}
v3 = {k: v[0] for k, v in json.loads((HS / "kalibrasyon_v3.json").read_text())["tahmin_vs_gozlem"].items()}
goz = {"s25": 0, "i99": 454, "b99": 16142, "m23": 53537}
ad = {"s25": "2025 Silivri\nİstanbul, ~0,05 g", "i99": "1999 İzmit\nİstanbul, ~0,15 g", "b99": "1999 İzmit\nfay bölgesi, ~0,35 g",
      "m23": "6 Şubat 2023\n11 il, 62 sn sarsıntı"}
fig, ax = plt.subplots(figsize=(7.6, 4.4))
y = np.arange(4)[::-1]
for i, (s, renk, et) in enumerate(((v1, "#b9b7b0", "v1: İstanbul'a kalibre"), (v2, MAVI, "v2: + 2023, süre, göçme eğrisi"),
                                   (v3, TURUNCU, "v3: + kat ölümcüllüğü, bölge stoğu"))):
    ax.scatter([max(s[k], 0.5) for k in goz], y + (i - 1) * 0.18, s=46, color=renk, label=et, zorder=3, edgecolor="white", linewidth=1.5)
ax.scatter([max(goz[k], 0.5) for k in goz], y, marker="D", s=70, color=MUREKKEP, label="gözlem", zorder=4)
ax.set_xscale("log"); ax.set_xlim(0.3, 2e5); ax.set_yticks(y, [ad[k] for k in goz]); ax.set_xlabel("ölü (log ölçek; 0 → 0,5'te gösterilir)")
ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.45, 1.13), ncol=2); ax.grid(axis="y", visible=False)
fig.suptitle("Dört gerçek depremde model: v1 6 Şubat'ı 24 kat eksik tahmin ediyordu", x=0.02, ha="left", fontsize=10.5, color=MUREKKEP)
fig.text(0.02, 0.01, "Kaynak: AFAD (2023), Bakanlık tespitleri (2025), resmî 1999 sayıları; model: model/hs_03, hs_06, hs_08", fontsize=7, color=IKINCIL)
fig.tight_layout(rect=(0, 0.03, 1, 0.97)); fig.savefig(IMG / "hs_kalibrasyon_v3.png", dpi=170)
print({k: (round(v1[k]), round(v2[k]), round(v3[k]), goz[k]) for k in goz})
