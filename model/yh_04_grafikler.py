"""Yer hareketi doğrulama ve senaryo grafikleri (docs/img/yh_*.png). Ana ortamda (.venv) çalışır."""
from __future__ import annotations

import json

import geopandas as gpd
import matplotlib as mpl  # noqa: F401
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from stil import IKINCIL, IMG, KOK, MAVI, MUREKKEP, TURUNCU, YH, YUZEY  # noqa: E402

SIRA = ["ASB14", "KAA15", "CEA14", "ASK14", "CY14", "BSSA14", "CB14", "AS08"]

# ---------- 1) olay terimleri: örneklem dışı 2025 vs örneklem içi 1999 ----------
s25 = pd.DataFrame(json.loads((YH / "gmpe_skor.json").read_text())["skor"])
s25 = s25[s25.imt == "PGA"].set_index("gmpe")
s99 = json.loads((YH / "izmit_skor.json").read_text())["sonuc"]["7.4"]
fig, ax = plt.subplots(figsize=(8, 4.6))
y = np.arange(len(SIRA))
tau = (s25.olay_terimi / s25.olay_terimi_norm).reindex(SIRA)
ax.axvspan(-0.3, 0.3, color="#f1f0ec", zorder=0, lw=0)
ax.axvline(0, color=IKINCIL, lw=1)
ax.errorbar(s25.olay_terimi.reindex(SIRA), y + 0.12, xerr=tau, fmt="o", ms=7, color=MAVI, ecolor=MAVI, elinewidth=1.5, capsize=0,
            label="2025 Silivri Mw 6,2 · örneklem dışı · 47 kayıt", mec=YUZEY, mew=2)
ax.plot([s99[k]["olay_terimi"] for k in SIRA], y - 0.12, "s", ms=7, color=TURUNCU, mec=YUZEY, mew=2,
        label="1999 İzmit Mw 7,4 · örneklem içi · 25 kayıt")
ax.set_yticks(y, [k + ("  ← İBB/KOERI" if k == "AS08" else "") for k in SIRA]); ax.invert_yaxis()
ax.set_xlabel("Olay terimi η (ln birim, PGA)   ·   negatif = model fazla tahmin ediyor   ·   çubuk ±τ")
ax.set_xlim(-1.3, 0.7); ax.grid(axis="y", visible=False)
ax.set_title("Yer hareketi modelleri gerçek kayıtlara karşı", loc="left", fontsize=12, fontweight="bold")
ax.legend(loc="upper left", bbox_to_anchor=(0, -0.13), ncol=2, frameon=False, fontsize=8)
ax.annotate("AS08 2025'i ~2,3× fazla tahmin ediyor,\nama Mw 7,4'te yanlılıksız", xy=(-0.83, 7.12), xytext=(-1.27, 5.5), fontsize=8, va="center",
            color=IKINCIL, arrowprops=dict(arrowstyle="-", color=IKINCIL, lw=0.8))
fig.tight_layout(); fig.savefig(IMG / "yh_olay_terimleri.png", dpi=160); plt.close(fig)

# ---------- 2) olay içi rezidü – mesafe (2025, PGA) ----------
r = pd.read_parquet(YH / "silivri_rezidu.parquet"); r = r[r.imt == "PGA"]
fig, axs = plt.subplots(2, 4, figsize=(11, 5), sharex=True, sharey=True)
kutu = np.array([15, 30, 60, 100, 200])
for ax, k in zip(axs.flat, SIRA):
    d = r[r.gmpe == k]
    ax.axhline(0, color=IKINCIL, lw=1)
    ax.scatter(d.rjb, d.olay_ici, s=14, color=MAVI, alpha=0.55, lw=0)
    b = pd.cut(d.rjb, kutu); mm = d.groupby(b, observed=True).olay_ici.agg(["mean", "sem"])
    xc = np.sqrt(kutu[:-1] * kutu[1:])[: len(mm)]
    ax.errorbar(xc, mm["mean"], yerr=1.96 * mm["sem"], fmt="-o", color=MUREKKEP, ms=4, lw=1.5, capsize=0)
    sk = s25.loc[k]
    ax.set_title(f"{k}   eğim {sk.egim_lnrjb:+.2f} (p={sk.p_lnrjb:.2f})", loc="left", fontsize=9)
    ax.set_xscale("log"); ax.set_ylim(-2, 2)
    ax.set_xticks([20, 50, 100, 200], ["20", "50", "100", "200"]); ax.xaxis.set_minor_formatter(mpl.ticker.NullFormatter())
for ax in axs[1]: ax.set_xlabel("Rjb (km)")
for ax in axs[:, 0]: ax.set_ylabel("olay içi rezidü δW")
fig.suptitle("2025 Silivri: olay içi rezidüler mesafeyle eğilim göstermiyor (PGA)", x=0.01, ha="left", fontsize=12, fontweight="bold")
fig.tight_layout(); fig.savefig(IMG / "yh_rezidu_mesafe.png", dpi=160); plt.close(fig)

# ---------- 3) senaryo: ağırlıklı medyan, belirsizlik, şehir ortalaması dağılımı ----------
s = pd.read_parquet(YH / "sahalar.parquet")
z = np.load(YH / "senaryo_alanlar.npz")
mah = (s.tip == "mahalle").values
pga = np.exp(z["ln_sa"][:, 0, :][:, mah])
mg = gpd.read_parquet(KOK / "data/processed/mahalle.parquet", columns=["uavt", "geometry"])
mg["p50"] = np.median(pga, 0); mg["p05"] = np.percentile(pga, 5, 0); mg["p95"] = np.percentile(pga, 95, 0)
mg = mg.to_crs(32635)
fig = plt.figure(figsize=(12, 7.2))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.8])
for i, (sut, bas) in enumerate((("p50", "Medyan PGA (g)"), ("p95", "%95 gerçekleşme PGA (g)"))):
    ax = fig.add_subplot(gs[0, i]); ax.set_axis_off()
    mg.plot(sut, ax=ax, cmap="Blues", vmin=0, vmax=0.6, lw=0.05, edgecolor=YUZEY, legend=True,
            legend_kwds={"shrink": 0.55, "label": "g"})
    ax.set_title(bas, loc="left", fontsize=11, fontweight="bold")
ax = fig.add_subplot(gs[1, :])
ort = pga.mean(1)
gidx = z["gmpe_idx"]; gad = list(z["gmpe"])
ax.hist(ort, bins=50, color=MAVI, edgecolor=YUZEY, lw=0.5)
for q, et in ((5, "%5"), (50, "medyan"), (95, "%95")):
    v = np.percentile(ort, q); ax.axvline(v, color=MUREKKEP, lw=1, ls="--" if q != 50 else "-")
    ax.text(v, ax.get_ylim()[1] * 0.92, f" {et} {v:.2f} g", fontsize=8, color=MUREKKEP)
ax.set_xlabel("Şehir geneli ortalama PGA (g) – 1.000 gerçekleşme"); ax.set_ylabel("gerçekleşme")
ax.set_title("Aynı Mw 7,5 depremi, 1.000 olası yer hareketi alanı: şehir ortalaması 4 kat değişebiliyor", loc="left", fontsize=11, fontweight="bold")
fig.tight_layout(); fig.savefig(IMG / "yh_senaryo.png", dpi=150); plt.close(fig)
print("grafikler: yh_olay_terimleri.png, yh_rezidu_mesafe.png, yh_senaryo.png")
