"""Bağımsız çapraz kontrol: USGS PAGER ampirik ölüm modeli (Jaiswal vd. 2009, OFR 2009-1136, Türkiye).

Ölüm oranı ν(S) = Φ(ln(S/θ)/β), S = MMI. Raporun Türkiye için verdiği iki nokta: MMI IX'da 1/38, MMI VIII'de ~1/1.000
⇒ β = ln(9/8)/(Φ⁻¹(1/38) − Φ⁻¹(1/1000)) ≈ 0,10, θ ≈ 11,0. Model, 1973–2007 Türkiye depremlerinin toplam ölümlerine uydurulmuştur
(1999 dahil, 2023 hariç) ⇒ 2023 için gerçek bir örneklem dışı sınamadır.
İstanbul: MMI, PGA'dan Worden vd. (2012) GMICE ile (ShakeMap'in kullandığı bağıntı); nüfus TÜİK 2025, senaryo alanları hs_02 ile aynı.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

KOK = Path(__file__).resolve().parents[1]
z1, z2 = norm.ppf(1 / 38), norm.ppf(1 / 1000)
BETA = np.log(9 / 8) / (z1 - z2)
THETA = 9 / np.exp(z1 * BETA)
oran = lambda mmi: norm.cdf(np.log(np.clip(mmi, 1, 12) / THETA) / BETA)


def gmice_worden12(pga_g: np.ndarray) -> np.ndarray:
    lp = np.log10(np.maximum(pga_g * 981.0, 1e-6))
    return np.clip(np.where(lp <= 1.57, 1.78 + 1.55 * lp, -1.60 + 3.70 * lp), 1, 10)


if __name__ == "__main__":
    print(f"PAGER Türkiye: θ = {THETA:.2f}, β = {BETA:.3f}")
    import sys
    sys.path.insert(0, str(KOK / "ders2023"))
    import sarsinti
    p = pd.read_parquet(KOK / "data/processed/sinama/maras2023_dugum.parquet")
    il11 = ["Adana", "Adıyaman", "Diyarbakır", "Elazığ", "Gaziantep", "Hatay", "Kahramanmaraş", "Kilis", "Malatya", "Osmaniye", "Şanlıurfa"]
    p = p[p.il.isin(il11)]
    a = [sarsinti.ornekle(sarsinti.oku(KOK / f"data/raw/external/usgs_2023/{f}_grid.xml"), p.lon.values, p.lat.values)["mmi"] for f in ("jllz", "jlqa")]
    mmi = np.fmax(np.nan_to_num(a[0]), np.nan_to_num(a[1]))
    olu = p.nufus.values * oran(mmi)
    print(f"6 Şubat 2023, 11 il: PAGER-Türkiye {olu.sum():,.0f} ölü (gözlem 53.537); MMI ≥ IX altında {p.nufus.values[mmi >= 9].sum():,.0f} kişi")
    print(pd.DataFrame({"il": p.il.values, "olu": olu, "nufus": p.nufus.values}).groupby("il").sum().sort_values("olu", ascending=False).round(0).head(8))

    m = pd.read_parquet(KOK / "data/processed/mahalle.parquet", columns=["uavt", "nufus_2025"])
    yh = KOK / "data/processed/yer_hareketi"
    z = np.load(yh / "senaryo_alanlar.npz")
    s = pd.read_parquet(yh / "sahalar.parquet")
    ms = s[s.tip == "mahalle"].set_index(s[s.tip == "mahalle"].kaynak_id.astype(int)).reindex(m.uavt)
    sira = pd.Series(np.arange(len(s)), index=s.saha_id)[ms.saha_id].values
    pga = np.exp(z["ln_sa"][:, 0, sira])                                   # (E, N)
    olu_e = (oran(gmice_worden12(pga)) * m.nufus_2025.values[None]).sum(1)
    q = np.percentile(olu_e, [5, 50, 95])
    print(f"İstanbul Mw 7,5 (1.000 alan): PAGER-Türkiye ölü medyan {q[1]:,.0f} (%5–95: {q[0]:,.0f}–{q[2]:,.0f}), ortalama {olu_e.mean():,.0f}")
    pd.DataFrame({"olu": olu_e}).to_parquet(KOK / "data/processed/sinama/istanbul_pager.parquet", index=False)
