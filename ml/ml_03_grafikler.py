"""ML grafikleri: İBB vekil modeli (SHAP, kalıntı haritası) ve simülatör vekili (SHAP). docs/img/ml_*.png"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "model"))
from stil import IKINCIL, IMG, KOK, MAVI, MUREKKEP, TURUNCU, YUZEY  # noqa: E402

ML = KOK / "data/processed/ml"
AD = {"fay_mesafe_km": "Fay mesafesi", "vs30": "Vs30 (zemin)", "eski_bina_oran": "1980 öncesi bina payı",
      "orta_yas_bina_oran": "1980–2000 bina payı", "yuksek_bina_oran": "5+ kat payı", "cok_yuksek_bina_oran": "9+ kat payı",
      "bina_yogunlugu_km2": "Bina yoğunluğu", "nufus_yogunlugu_km2": "Nüfus yoğunluğu", "kisi_per_bina": "Kişi / bina",
      "taban_alan_medyan_m2": "Medyan taban alanı"}


def ibb():
    sk = json.loads((ML / "ibb_vekil_skor.json").read_text())
    shp = pd.read_parquet(ML / "ibb_vekil_shap.parquet")
    m = pd.read_parquet(KOK / "data/processed/mahalle.parquet")
    k = pd.read_parquet(ML / "ibb_vekil_kalinti.parquet")
    g = gpd.read_parquet(KOK / "data/processed/mahalle.parquet", columns=["uavt", "geometry"]).merge(k, on="uavt").to_crs(32635)
    fig = plt.figure(figsize=(13, 5.2)); gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.5])
    ax = fig.add_subplot(gs[0])
    on = pd.Series(sk["shap_A"]).sort_values()
    sira = list(on.index)
    for j, c in enumerate(sira):
        x = shp[c].values; v = m[c].values
        r = (v - np.nanpercentile(v, 2)) / (np.nanpercentile(v, 98) - np.nanpercentile(v, 2))
        yj = j + (np.random.default_rng(j).random(len(x)) - 0.5) * 0.55
        ax.scatter(x, yj, c=np.clip(r, 0, 1), cmap="coolwarm", s=4, lw=0, alpha=0.7)
    ax.axvline(0, color=IKINCIL, lw=0.8)
    ax.set_yticks(range(len(sira)), [AD[c] for c in sira]); ax.grid(axis="y", visible=False)
    ax.set_xlabel("SHAP (logit ağır+ hasar oranına katkı)   ·   renk: düşük → yüksek öznitelik")
    cv = sk["cv"]
    ax.set_title(f"İBB modelini ne belirliyor?\nilçe dışı R² = {cv['A_ilce_grup']['r2_logit']:.2f} (rastgele bölmede {cv['A_rastgele']['r2_logit']:.2f})",
                 loc="left", fontsize=11, fontweight="bold")
    ax = fig.add_subplot(gs[1]); ax.set_axis_off()
    lim = np.nanpercentile(np.abs(g.kalinti_fizik), 97)
    g.plot("kalinti_fizik", ax=ax, cmap="RdBu_r", vmin=-lim, vmax=lim, lw=0.05, edgecolor=YUZEY, legend=True,
           legend_kwds={"shrink": 0.6, "label": "İBB − fizik modeli (logit)"})
    ax.set_title("Fizik modelimizin açıklayamadığı (ilçe dışı tahmin kalıntısı)\nkırmızı: İBB daha fazla hasar görüyor · mavi: daha az · fay uzağında logit farkları büyür",
                 loc="left", fontsize=11, fontweight="bold")
    fig.tight_layout(); fig.savefig(IMG / "ml_ibb_vekil.png", dpi=150); plt.close(fig)


def sim():
    f = ML / "sim_vekil_skor.json"
    if not f.exists():
        return
    sk = json.loads(f.read_text())
    on = pd.Series(sk["onem"]).sort_values().tail(14)
    kol = {"n_ibb_ilk", "n_ibb_cagri", "n_ulusal", "n_uluslararasi", "tahliye_carpan", "pol_fayda", "pol_esitlik"}
    dep = {"log_agir_ustu", "log_cokmus_kisi", "ag_kopru_kapali", "ag_enkaz_kenar", "has_islev_ort"}
    renk = [TURUNCU if c in kol else (MUREKKEP if c in dep else MAVI) for c in on.index]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(range(len(on)), on.values, color=renk, height=0.6)
    ax.set_yticks(range(len(on)), on.index); ax.grid(axis="y", visible=False)
    ax.set_xlabel("ortalama |SHAP| (log önlenebilir ölüm)")
    ax.set_title(f"Önlenebilir ölümü ne belirliyor? (simülatör vekili, R² = {sk['r2_log']:.2f})\nsiyah: depremin kendisi · turuncu: karar · mavi: belirsiz fizik",
                 loc="left", fontsize=11, fontweight="bold")
    fig.tight_layout(); fig.savefig(IMG / "ml_sim_vekil.png", dpi=160); plt.close(fig)


if __name__ == "__main__":
    ibb(); sim(); print("ml grafikleri yazıldı")
