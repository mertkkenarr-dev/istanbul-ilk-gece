"""İkinci sınama depremi: 17.08.1999 İzmit (Kocaeli) Mw 7,4 – senaryoyla aynı büyüklük sınıfı, yalnızca PGA.

Girdi : data/raw/literatur/izmit1999_kayitlar_koeri2010_tablo213.csv (KOERI 2010 raporu Tablo 2.1.3'ten aynen aktarıldı)
Çıktı : data/processed/yer_hareketi/izmit_rezidu.parquet, izmit_skor.json

Uyarı: bu kayıtlar NGA-West1/West2 ve ASB14 veri tabanlarında zaten var; yani sınama örneklem İÇİdir. Değeri, büyüklük
ölçeklemesinin (M 7,4) ve İstanbul'a ~40 km mesafedeki sönümün tutarlılığını görmek. Örneklem DIŞI tek sınama 2025'tir.
Kırılma izi Barka vd. (2002) yüzey kırığı ve deniz altındaki Karamürsel uzantısından sadeleştirildi (Hersek batısı ~29,2°D).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import norm
from yh_ortak import CIKTI, GMPE, KOK, kirilma, medyan_sigma, sahalar

ham = pd.read_csv(KOK / "data/raw/literatur/izmit1999_kayitlar_koeri2010_tablo213.csv")
d = ham.copy()
duzeltme = []
# YKP = Yapı Kredi Plaza (Levent). Raporda boylam 28,0112 yazılmış; bu nokta Silivri batısıdır ve fay mesafesi ~110 km olurdu.
# Raporun kendi verdiği 42,1 km mesafe ve Levent'in konumu (41,08 K / 29,01 D) boylamın 29,0112 olduğunu gösteriyor.
d.loc[d.istasyon == "YKP", "boylam"] = 29.0112
duzeltme.append("YKP boylamı 28,0112 → 29,0112 (yazım hatası; raporun kendi fay mesafesiyle tutarlı hale gelir)")
# Sınıftan Vs30: NEHRP aralıklarının geometrik ortası; sınıfı bilinmeyenlere KOERI'nin varsayımı olan C
SINIF_VS30 = {"B": 1000.0, "C": 520.0, "D": 270.0}
d["vs30_kaynagi"] = np.where(d.vs30.notna(), "olcum_mikrobolgeleme", np.where(d.nehrp.notna(), "nehrp_sinifi", "varsayim_C"))
d["vs30"] = d.vs30.fillna(d.nehrp.map(SINIF_VS30)).fillna(SINIF_VS30["C"])
tek = d.pga_h2_gal.isna()
duzeltme.append(f"Tek yatay bileşeni olan {int(tek.sum())} kayıt (SKR, GBZ) tutuldu; geometrik ortalama yerine tek bileşen, bayraklı")
d["pga_g"] = d.pga_gm_gal / 980.665

IZ = [(29.20, 40.70), (29.35, 40.72), (29.60, 40.72), (29.95, 40.73), (30.25, 40.70), (30.60, 40.68), (30.95, 40.73), (31.05, 40.75)]
sonuc, uzun = {}, []
for mw in (7.4, 7.6):  # KOERI 7,4 kullanmış; USGS Mww 7,6
    rup = kirilma(IZ, mw, 0.0, 18.0, hipo=(29.97, 40.76, 17.0))
    mu, sig, tau, phi, ctx = medyan_sigma(list(GMPE), rup, sahalar(d.boylam, d.enlem, d.vs30), ["PGA"])
    d[f"rrup_{mw}"] = ctx.rrup
    for g, k in enumerate(GMPE):
        r = np.log(d.pga_g.values) - mu[g, 0]
        t, p_ = tau[g, 0].mean(), phi[g, 0].mean()
        eta = t**2 * r.sum() / (len(r) * t**2 + p_**2)
        ist = ctx.rrup
        yakin = (ist >= 30) & (ist <= 60)  # İstanbul'un senaryo fayına uzaklık bandı
        sonuc.setdefault(mw, {})[k] = dict(olay_terimi=float(eta), olay_terimi_norm=float(eta / t),
                                           llh=float(-np.mean(np.log2(norm.pdf(r, 0, sig[g, 0])))),
                                           ort_rezidu_30_60km=float(r[yakin].mean()), n_30_60km=int(yakin.sum()))
        if mw == 7.4:
            uzun.append(pd.DataFrame(dict(istasyon=d.istasyon, gmpe=k, rrup=ctx.rrup, vs30=d.vs30, gozlem=d.pga_g,
                                          tahmin=np.exp(mu[g, 0]), rezidu=r)))

fark = (d["rrup_7.4"] - d.fay_mesafesi_km).abs()
print("Mesafe kontrolü (bizim Rrup – KOERI fay mesafesi), en büyük 5:")
print(d.assign(fark=fark).nlargest(5, "fark")[["istasyon", "boylam", "fay_mesafesi_km", "rrup_7.4", "fark"]].round(1).to_string(index=False))
pd.concat(uzun).to_parquet(CIKTI / "izmit_rezidu.parquet", index=False)
d.to_parquet(CIKTI / "izmit_gozlem.parquet", index=False)
(CIKTI / "izmit_skor.json").write_text(json.dumps(dict(duzeltmeler=duzeltme, sonuc={str(k): v for k, v in sonuc.items()}), ensure_ascii=False, indent=1))
tab = pd.DataFrame({f"Mw{mw}": {k: v["olay_terimi"] for k, v in s.items()} for mw, s in sonuc.items()})
tab["LLH_7.4"] = {k: v["llh"] for k, v in sonuc[7.4].items()}
tab["rezidu_30_60km"] = {k: v["ort_rezidu_30_60km"] for k, v in sonuc[7.4].items()}
print("\nİzmit 1999 olay terimi (PGA):"); print(tab.round(2).sort_values("LLH_7.4"))
