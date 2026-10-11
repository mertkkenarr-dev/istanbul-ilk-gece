"""Ampirik aktarım: "İstanbul, aynı sarsıntıda 6 Şubat bölgesi gibi davransaydı?"

6 Şubat'ın il bazında ölümlerinden (Vikipedi derlemesi, 9–12 Şubat tarihli kaynaklar; toplamı 53.537'ye ölçeklenir, VARSAYIM)
düğüm nüfusu ve gerçek PGA ile bir ölüm-oranı eğrisi ν(PGA) = Φ(ln(PGA/θ)/β) uydurulur (en küçük kareler, log ölçek).
Eğri, İstanbul senaryosunun 1.000 PGA alanına ve TÜİK 2025 mahalle nüfusuna uygulanır. Bu bir üst sınır deneyidir:
İstanbul'un bina stoğunun 6 Şubat bölgesininkiyle aynı kalitede ve sarsıntının aynı uzunlukta (62 sn) olduğunu varsayar.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import norm

KOK = Path(__file__).resolve().parents[1]
OLU = {"Hatay": 21910, "Kahramanmaraş": 12622, "Adıyaman": 8387, "Gaziantep": 3897, "Malatya": 1393, "Osmaniye": 993,
       "Adana": 454, "Diyarbakır": 414, "Şanlıurfa": 340, "Kilis": 74, "Elazığ": 5}
olcek = 53537 / sum(OLU.values())
p = pd.read_parquet(KOK / "data/processed/sinama/maras2023_dugum.parquet")
p = p[p.il.isin(OLU) & (p.il != "Diyarbakır")]
pga = np.exp(p.ln_pga.values); nuf = p.nufus.values; il = p.il.values
gozlem = pd.Series(OLU).drop("Diyarbakır") * olcek


def tahmin(x):
    th, b = np.exp(x)
    return pd.Series(nuf * norm.cdf(np.log(pga / th) / b)).groupby(il).sum()


kayip = lambda x: float(((np.log(tahmin(x).reindex(gozlem.index) + 1) - np.log(gozlem + 1)) ** 2).sum())
r = minimize(kayip, np.log([1.0, 0.4]), method="Nelder-Mead")
th, b = np.exp(r.x)
t = tahmin(r.x)
print(f"6 Şubat eğrisi: θ = {th:.2f} g, β = {b:.2f}; toplam tahmin {t.sum():,.0f} (gözlem {gozlem.sum():,.0f})")
print(pd.DataFrame({"gozlem": gozlem.round(0), "tahmin": t.reindex(gozlem.index).round(0)}).sort_values("gozlem", ascending=False).to_string())
for g in (0.1, 0.2, 0.3, 0.4, 0.5, 0.7):
    print(f"  PGA {g:.1f} g → {1000 * norm.cdf(np.log(g / th) / b):.2f} ölü / 1000 kişi")

m = pd.read_parquet(KOK / "data/processed/mahalle.parquet", columns=["uavt", "ilce", "nufus_2025"])
yh = KOK / "data/processed/yer_hareketi"
z = np.load(yh / "senaryo_alanlar.npz"); s = pd.read_parquet(yh / "sahalar.parquet")
ms = s[s.tip == "mahalle"].set_index(s[s.tip == "mahalle"].kaynak_id.astype(int)).reindex(m.uavt)
sira = pd.Series(np.arange(len(s)), index=s.saha_id)[ms.saha_id].values
P = np.exp(z["ln_sa"][:, 0, sira])
olu = (norm.cdf(np.log(P / th) / b) * m.nufus_2025.values[None]).sum(1)
q = np.percentile(olu, [5, 50, 95, 99])
print(f"\nİstanbul Mw 7,5, '6 Şubat gibi': medyan {q[1]:,.0f}, ortalama {olu.mean():,.0f}, %5–95 {q[0]:,.0f}–{q[2]:,.0f}, %99 {q[3]:,.0f}, en kötü {olu.max():,.0f}")
print(f"500.000 ve üstü olan gerçekleşme: {(olu >= 5e5).mean():.1%};  100.000+: {(olu >= 1e5).mean():.1%}")
pga_med = np.median(P, 0)
print(f"İstanbul'da PGA ≥ 0,3 g yaşayan nüfus (medyan alan): {m.nufus_2025.values[pga_med >= 0.3].sum():,.0f}; Hatay'da {nuf[(il == 'Hatay') & (pga >= 0.3)].sum():,.0f}")
pd.DataFrame({"olu": olu}).to_parquet(KOK / "data/processed/sinama/istanbul_2023gibi.parquet", index=False)
