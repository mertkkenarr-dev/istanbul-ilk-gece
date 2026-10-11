"""Hasar fazı grafikleri: kalibrasyon uyumu ve senaryo kayıp dağılımları (docs/img/hs_*.png)."""
from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from stil import IMG, KOK, MAVI, MUREKKEP, TURUNCU, YUZEY

HS = KOK / "data/processed/hasar"
k = pd.read_parquet(HS / "kalibrasyon.parquet")
w = k.agirlik.values
YESIL = "#1baf7a"

# ---------- 1) kalibrasyon: gözlem vs KOERI vs kalibre ----------
koeri = json.loads((HS / "kalibrasyon.json").read_text())
GOZ = [("2025 İstanbul · orta hasar", "s25_orta", 200, False), ("2025 İstanbul · ağır+ hasar", "s25_agir_ustu", 2, False),
       ("1999 İstanbul · ağır+ hasar", "i99_agir_ustu", 3300, False), ("1999 İstanbul · can kaybı", "i99_olu", 454, True),
       ("1999 fay bölgesi · çok ağır", "b99_cokagir", 22000, False), ("1999 fay bölgesi · can kaybı", "b99_olu", 16142, True)]
# KOERI satırı (s_β = θ = 1) kalibrasyon ızgarasında yok; hs_02'deki ilk sürümden: aynı fonksiyonla yeniden hesaplanır
from hs_03_kalibrasyon import tahmin  # noqa: E402  (ızgarayı yeniden koşmaz; yalnızca fonksiyon ve maruziyet yüklenir)

kr = {x: tahmin(x, 1.0, 1.0) for x in ("silivri2025", "izmit1999", "bolge1999")}
kmap = {"s25": "silivri2025", "i99": "izmit1999", "b99": "bolge1999"}
fig, ax = plt.subplots(figsize=(8.5, 4.4))
for j, (_et, sut, obs, olu) in enumerate(GOZ):
    deg = k[sut].values * (k.kappa.values if olu else 1)
    ort = np.exp(np.sum(w * np.log(np.maximum(deg, 1e-3))))
    lo, hi = (np.interp(q, np.cumsum(w[np.argsort(deg)]), np.sort(deg)) for q in (0.05, 0.95))
    kv = kr[kmap[sut[:3]]][sut[4:]]
    ax.plot([lo, hi], [j, j], color=MAVI, lw=3, alpha=0.35, solid_capstyle="round")
    ax.plot(ort, j, "o", color=MAVI, ms=8, mec=YUZEY, mew=2, label="kalibre (posterior, %90)" if j == 0 else None)
    ax.plot(kv, j, "s", color=TURUNCU, ms=7, mec=YUZEY, mew=2, label="KOERI eğrileri" if j == 0 else None)
    ax.plot(obs, j, "D", mfc="none", mec=MUREKKEP, ms=10, mew=1.8, label="gözlem" if j == 0 else None)
ax.set_xscale("log"); ax.set_yticks(range(len(GOZ)), [g[0] for g in GOZ]); ax.invert_yaxis(); ax.grid(axis="y", visible=False)
ax.set_xlabel("bina ya da kişi sayısı (log)")
ax.set_title("Kırılganlık eğrileri İstanbul'un iki gerçek depremine karşı", loc="left", fontsize=12, fontweight="bold")
ax.legend(loc="upper left", bbox_to_anchor=(0, -0.14), ncol=3, frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(IMG / "hs_kalibrasyon.png", dpi=160); plt.close(fig)

# ---------- 2) senaryo dağılımları ----------
t = pd.read_parquet(HS / "olay_toplamlari.parquet")
mah = pd.read_parquet(KOK / "data/processed/mahalle.parquet")
ibb = {"agir_ustu": int(mah.bina_cok_agir.sum() + mah.bina_agir.sum()), "can_kaybi": int(mah.can_kaybi.sum())}
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
for ax, (sut, bas) in zip(axs, (("agir_ustu", "Ağır + çok ağır hasarlı bina"), ("can_kaybi", "Can kaybı (bina hasarından)"))):
    bins = np.logspace(0, 6, 61)
    for katman, renk, et in (("ana", MAVI, "ana model (kalibre)"), ("koeri_mc", TURUNCU, "KOERI eğrileri + GM belirsizliği")):
        x = t[t.katman == katman][sut].clip(lower=1)
        ax.hist(x, bins=bins, color=renk, alpha=0.75 if katman == "ana" else 0.45, edgecolor=YUZEY, lw=0.4, label=et)
        ax.axvline(np.median(x), color=renk, lw=1.2, ls="--")
    ax.axvline(ibb[sut], color=MUREKKEP, lw=1.5)
    ax.text(ibb[sut], ax.get_ylim()[1] * 0.95, f" İBB {ibb[sut]:,}".replace(",", "."), fontsize=8, color=MUREKKEP, va="top")
    ax.set_xscale("log"); ax.set_title(bas, loc="left", fontsize=11, fontweight="bold"); ax.set_xlabel("1.000 olası depremde (log)")
axs[0].set_ylabel("olay sayısı"); axs[0].legend(frameon=False, fontsize=8, loc="upper left")
fig.suptitle("Aynı Mw 7,5 senaryosu: tek sayı yerine dağılım (kesikli çizgi = medyan)", x=0.01, ha="left", fontsize=12, fontweight="bold")
fig.tight_layout(); fig.savefig(IMG / "hs_senaryo_dagilim.png", dpi=160); plt.close(fig)
print("grafikler: hs_kalibrasyon.png, hs_senaryo_dagilim.png")
