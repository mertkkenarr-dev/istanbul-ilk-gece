"""Mahalle bina envanterini KOERI'nin 54 hasar sınıfına ayırır (yapı tipi × kat × yaş).

Girdi : data/processed/mahalle.parquet (İBB 2017 yaş ve kat marjinalleri), data/raw/literatur/koeri2010_tablo411_envanter.csv
Çıktı : data/processed/hasar/envanter.parquet (uavt × sınıf → bina sayısı, kişi)

1) Yaş × kat ortak dağılımı: İBB yalnızca marjinal verir (3 yaş, 3 kat sınıfı). Tohum = KOERI'nin şehir geneli yaş × kat
   tablosu, iteratif oransal uydurma (IPF, Deming & Stephan 1940) ile her mahallenin marjinallerine uydurulur. Tohum,
   marjinallerin söylemediği bağımlılığı taşır (ör. 2000 sonrası binaların büyük kısmı 5+ kat).
2) Yapı tipi: P(tip | yaş, kat) KOERI tablosundan, şehir geneli. Mahalleye özgü tip bilgisi yok; bu bir varsayım.
3) Kişi: TÜİK 2025 nüfusu, KOERI Tablo 4.4.6 kat ağırlıklarıyla (1–4 kat: 6, 5–8: 24, 9+: 60 kişi/bina) binalara dağıtılır;
   mahalle toplamı nüfusa eşitlenir (gece senaryosu: herkes evde).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
CIKTI = KOK / "data/processed/hasar"; CIKTI.mkdir(parents=True, exist_ok=True)
YAS = ["-1979", "1980-2000", "2000-"]
KAT = ["1-4", "5-8", "9-"]
KISI_AGIRLIK = {"1-4": 6.0, "5-8": 24.0, "9-": 60.0}

e = pd.read_csv(KOK / "data/raw/literatur/koeri2010_tablo411_envanter.csv")
e["kat"] = e.kat.replace({"9-19": "9-", "20-": "9-"})
e["tip"] = e.kod.str[1]
# perde duvarda 9-19 ve 20+ ayrı; tek '9-' sınıfında birleşir, hasar parametresi için 9-19 kodu (B63x) temsilci
e["kod"] = e.kod.where(~e.kod.str.match(r"B64\d"), e.kod.str.replace("B64", "B63", regex=False))
e = e.groupby(["kod", "tip", "yapi_tipi", "kat", "yas"], as_index=False).bina_sayisi.sum()
tohum = e.pivot_table(index="yas", columns="kat", values="bina_sayisi", aggfunc="sum").reindex(index=YAS, columns=KAT).values
pay = e.assign(hucre=e.groupby(["yas", "kat"]).bina_sayisi.transform("sum"))
pay["p_tip"] = pay.bina_sayisi / pay.hucre.replace(0, np.nan)
pay = pay[pay.p_tip > 0]


def ipf(tohum: np.ndarray, satir: np.ndarray, sutun: np.ndarray, iter_maks: int = 200, tol: float = 1e-9) -> np.ndarray:
    x = tohum.astype(float) + 1e-9
    for _ in range(iter_maks):
        x *= (satir / x.sum(1).clip(1e-12))[:, None]
        x *= (sutun / x.sum(0).clip(1e-12))[None, :]
        if np.abs(x.sum(1) - satir).max() < tol * max(satir.sum(), 1):
            break
    return x


m = pd.read_parquet(KOK / "data/processed/mahalle.parquet",
                    columns=["uavt", "bina_1980_oncesi", "bina_1980_2000", "bina_2000_sonrasi", "kat_1_4", "kat_5_9", "kat_9_19", "nufus_2025"])
satirlar = []
maks_hata = 0.0
for r in m.itertuples():
    yas_m = np.array([r.bina_1980_oncesi, r.bina_1980_2000, r.bina_2000_sonrasi], float)
    kat_m = np.array([r.kat_1_4, r.kat_5_9, r.kat_9_19], float)
    if yas_m.sum() == 0:
        continue
    x = ipf(tohum, yas_m, kat_m)
    maks_hata = max(maks_hata, np.abs(x.sum(1) - yas_m).max(), np.abs(x.sum(0) - kat_m).max())
    for i, y in enumerate(YAS):
        for j, k in enumerate(KAT):
            if x[i, j] <= 0:
                continue
            for p in pay[(pay.yas == y) & (pay.kat == k)].itertuples():
                satirlar.append((r.uavt, p.kod, p.tip, p.yapi_tipi, k, y, x[i, j] * p.p_tip))
env = pd.DataFrame(satirlar, columns=["uavt", "sinif", "tip", "yapi_tipi", "kat", "yas", "bina"])
env = env[env.bina > 1e-6]
env["kisi_agirlik"] = env.bina * env.kat.map(KISI_AGIRLIK)
env["kisi"] = env.kisi_agirlik / env.groupby("uavt").kisi_agirlik.transform("sum") * env.uavt.map(m.set_index("uavt").nufus_2025)
env = env.drop(columns="kisi_agirlik")
env.to_parquet(CIKTI / "envanter.parquet", index=False)

# --- kontroller ---
top = env.groupby("uavt").bina.sum()
print(f"IPF en büyük marjinal hata: {maks_hata:.2e} bina")
print(f"bina toplamı {env.bina.sum():,.0f} (İBB {m[['kat_1_4', 'kat_5_9', 'kat_9_19']].sum().sum():,}); kişi {env.kisi.sum():,.0f} (TÜİK {m.nufus_2025.sum():,})")
print("yapı tipi payları (şehir):"); print((env.groupby("yapi_tipi").bina.sum() / env.bina.sum()).round(4).sort_values(ascending=False))
print("kat sınıfına göre kişi/bina:"); print((env.groupby("kat").kisi.sum() / env.groupby("kat").bina.sum()).round(1))
