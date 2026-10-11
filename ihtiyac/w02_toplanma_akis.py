"""Web akış katmanı: medyan depremde Esenyurt ve komşu ilçelerde bina bloklarından açık alanlara kaç kişinin yürüdüğü (i02 ile aynı
çözüm, akışlar dahil) ve her blokta yer bulamayan kişi.
Çıktı: data/processed/web_tiles/toplanma_akis.json
  akis  [[blok lon, lat, alan lon, lat, kişi, yürüme m], ...]  (≥ 20 kişilik akışlar; görselde gürültüyü keser)
  yersiz [[lon, lat, kişi], ...]                                 (yer bulamayan > 0 olan bloklar)
  alan  [[lon, lat, kapasite, dolan kişi], ...]                  (odak bölgesindeki açık alanlar)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from i02_toplanma_atama import alanlar, ata, bloklar
from w01_binalar import ILCELER

KOK = Path(__file__).resolve().parents[1]
P = KOK / "data/processed"; C = P / "ihtiyac"; OUT = P / "web_tiles"

if __name__ == "__main__":
    m = pd.read_parquet(P / "mahalle.parquet", columns=["uavt", "ilce", "nufus_2025"])
    b = bloklar(); a = alanlar(1.5)
    z = np.load(C / "disarida_temel_ist.npz")
    e = int(np.argsort(z["ilk_gece"].sum(1))[len(z["ilk_gece"]) // 2])
    mix = pd.Series(np.arange(len(m)), index=m.uavt)
    talep = z["ilk_gece"][e].astype(float)[mix[b.uavt].values] * b.pay.values
    u, _, (ii, jj, x, d) = ata(b, a, talep, 1000, akis=True)
    odak = b.uavt.isin(m[m.ilce.isin(ILCELER)].uavt).values
    sec = odak[ii] & (x >= 20)
    akis = np.c_[b.lon.values[ii[sec]], b.lat.values[ii[sec]], a.lon.values[jj[sec]], a.lat.values[jj[sec]], x[sec], d[sec]]
    dolan = np.bincount(jj, weights=x, minlength=len(a))
    alan_odak = np.unique(jj[odak[ii]])
    ys = odak & (u > 0.5)
    veri = dict(olay=e, akis=np.round(akis, [5, 5, 5, 5, 0, 0][0]).tolist(),
                yersiz=np.round(np.c_[b.lon.values[ys], b.lat.values[ys], u[ys]], 5).tolist(),
                alan=np.round(np.c_[a.lon.values[alan_odak], a.lat.values[alan_odak], a.kapasite.values[alan_odak], dolan[alan_odak]], 5).tolist())
    (OUT / "toplanma_akis.json").write_text(json.dumps(veri, separators=(",", ":")))
    print(f"akış {sec.sum():,} ({x[sec].sum() / x[odak[ii]].sum():.0%} kişi), yer bulamayan blok {ys.sum():,} ({u[ys].sum():,.0f} kişi), "
          f"alan {len(alan_odak)}; dolu alan (≥%99) {(dolan[alan_odak] >= 0.99 * a.kapasite.values[alan_odak]).mean():.0%}; "
          f"{(OUT / 'toplanma_akis.json').stat().st_size / 1e6:.2f} MB")
