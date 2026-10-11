"""İhtiyaç analizi, adım 3: ilk 72 saatin kaynak ihtiyacı ve eldeki kapasite (senaryo × stok, 1.000 gerçekleşmenin medyanı ve %90'ı).

Standartlar (Sphere 2018 İnsani Yardım El Kitabı, aksi belirtilmedikçe)
  su        ilk 72 saat: dışarıdaki herkese 3 L/gün içme (hayatta kalma alt sınırı); evsizlere 15 L/gün (temel standart)
  gıda      2.100 kcal/kişi/gün ≈ 0,6 kg kuru tayın (VARSAYIM: karışık tayın enerji yoğunluğu ~3.500 kcal/kg)
  tuvalet   ilk evrede 50 kişiye 1 (orta vadede 20'ye 1)
  barınma   3,5 m² kapalı alan/kişi; kamp yerleşiminde 45 m²/kişi (ortak hizmetlerle); aile çadırı = hane (TÜİK hane büyüklüğü)
  battaniye ilk gece dışarıdakilere kişi başı 1 (mevsim bilinmiyor; kış gecesi 2)
Kapasite
  hastane   45.969 yatak (tahmini) × gece boş payı 0,30 × tahliye genişlemesi 1,5 × deprem sonrası işlevsellik (sim/girdi, kalibre B522)
  kurtarma  ekip-saat (sim/optimizasyon.ekip_saat, %25 yol payı düşülmüş) / 3 ekip-saat kişi başı; talep = enkaz altında canlı
            kalanların komşu elinin yetmediği yarısı (p_hafif_sikisma = 0,5)
  kamp alanı ≥ 10.000 m² açık alanlar, kullanılabilir pay i02 ile aynı
Çıktı: data/processed/ihtiyac/kaynak_ozet.parquet, kaynak_ozet.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[1]
P = KOK / "data/processed"; C = P / "ihtiyac"
sys.path.insert(0, str(KOK / "sim")); sys.path.insert(0, str(KOK / "ihtiyac"))
from girdi import Senaryo  # noqa: E402
from i02_toplanma_atama import PAY  # noqa: E402
from optimizasyon import ekip_saat  # noqa: E402
from parametreler import Parametre  # noqa: E402

KOMBI = [("temel", "ist"), ("temel", "maras_gibi"), ("dogu", "ist"), ("buyuk", "ist"), ("buyuk", "maras_gibi")]
q = lambda x: (float(np.median(x)), float(np.percentile(x, 90)))

if __name__ == "__main__":
    m = pd.read_parquet(P / "mahalle.parquet", columns=["uavt", "hane_buyuklugu"])
    hb = m.hane_buyuklugu.fillna(m.hane_buyuklugu.median()).values
    t = gpd.read_parquet(P / "toplanma_alani.parquet")
    t = t[t.toplanma_uygun & (t.alan_m2 >= 10_000)]
    kamp_m2 = float((t.alan_m2 * t.tur.map(PAY).fillna(0.5)).sum())
    par = Parametre()
    pro_kap = float(ekip_saat(par).sum() / par.kurtarma_sure_sa)
    satir = []
    for sen, stok in KOMBI:
        d = np.load(C / f"disarida_{sen}_{stok}.npz"); k = np.load(P / f"hasar/v3/{sen}_{stok}_kisi.npz")
        S = Senaryo(sen, stok)
        islev = np.array([S.gerceklesme(e)["has_islev"] for e in range(0, 1000, 10)])
        yatak = S.has.yatak_tahmini.values * par.bos_yatak_payi * par.tahliye_carpan
        yatak_kap = (islev * yatak[None]).sum(1)
        ilk, uzun = d["ilk_gece"].sum(1), d["uzun_sureli"].sum(1)
        agir_yarali = k["yarali_agir"].sum(1) + 0.5 * k["sikisan_canli"].sum(1) * 0.5
        pro_talep = 0.5 * k["sikisan_canli"].sum(1)
        r = dict(senaryo=sen, stok=stok,
                 ilk_gece=q(ilk), evsiz=q(uzun), aile_cadiri=q((d["uzun_sureli"] / hb[None]).sum(1)),
                 kamp_alani_ha=q(uzun * 45 / 1e4), kamp_alani_mevcut_ha=kamp_m2 / 1e4,
                 su_ton_gun=q((ilk - uzun) * 3 / 1000 + uzun * 15 / 1000), gida_ton_gun=q(ilk * 0.6 / 1000),
                 tuvalet=q(ilk / 50), battaniye=q(ilk),
                 agir_yarali=q(agir_yarali), yatak_kapasite=q(yatak_kap),
                 enkaz_pro_talep=q(pro_talep), enkaz_pro_kapasite_72sa=pro_kap)
        satir.append(r)
        print(f"{sen}/{stok}: evsiz {r['evsiz'][0]:,.0f} (%90 {r['evsiz'][1]:,.0f}); kamp {r['kamp_alani_ha'][0]:,.0f} ha / mevcut {kamp_m2 / 1e4:,.0f} ha; "
              f"su {r['su_ton_gun'][0]:,.0f} t/gün; ağır yaralı {r['agir_yarali'][0]:,.0f} / yatak {r['yatak_kapasite'][0]:,.0f}; "
              f"profesyonel kurtarma talebi {r['enkaz_pro_talep'][0]:,.0f} / 72 sa kapasite {pro_kap:,.0f}", flush=True)
    (C / "kaynak_ozet.json").write_text(json.dumps(satir, ensure_ascii=False, indent=1))
    pd.json_normalize(satir).to_parquet(C / "kaynak_ozet.parquet", index=False)
