"""Mahalle ana tablosu: tüm katmanlar tek satırda, türetilmiş oranlar ve uçtan uca değişmezlik kontrolleri.

Girdi : data/interim/{mahalle_oznitelik, mahalle_sinir, mahalle_erisim_dugumu, mahalle_zemin_bina, mahalle_silivri2025,
        hastane, itfaiye, toplanma_alani}.parquet
Çıktı : data/processed/mahalle.parquet (GeoParquet, 959 satır), data/interim/veri_sozlugu.parquet

Değişmezlik: birleştirmeler satır kaybettirmemeli ve senaryo toplamları kaynak CSV'deki toplamla aynı kalmalı.
Bu kontrol, bir join'in sessizce satır çoğaltmasını veya düşürmesini yakalar.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from ortak import IBB, INTERIM, PROCESSED, adim_temizle, log, qc
from sozluk import SOZLUK

ADIM = "08_birlestir"
adim_temizle(ADIM)
print(ADIM)

oz = pd.read_parquet(INTERIM / "mahalle_oznitelik.parquet")
sn = gpd.read_parquet(INTERIM / "mahalle_sinir.parquet").drop(columns=["ilce_k"])
oz_anahtar = ["ilce_k", "mahalle_k"]  # yalnızca eşleştirme için; çıktıya girmez
er = pd.read_parquet(INTERIM / "mahalle_erisim_dugumu.parquet")
zb = pd.read_parquet(INTERIM / "mahalle_zemin_bina.parquet")
sv = pd.read_parquet(INTERIM / "mahalle_silivri2025.parquet")

m = sn.merge(oz.drop(columns=oz_anahtar), on="uavt", how="inner", validate="1:1")
for t in (er, zb, sv):
    m = m.merge(t, on="uavt", how="left", validate="1:1")
qc(ADIM, "Birleştirme sonrası 959 satır, UAVT benzersiz", len(m) == 959 and m.uavt.is_unique, f"{len(m)} satır")

# ---- tesis sayıları (mahalle içinde) ----
h = pd.read_parquet(INTERIM / "hastane.parquet")
f = pd.read_parquet(INTERIM / "itfaiye.parquet")
a = pd.read_parquet(INTERIM / "toplanma_alani.parquet")
m["hastane_sayisi"] = m.uavt.map(h.groupby("uavt").size()).fillna(0).astype(int)
m["hastane_yatak_tahmini"] = m.uavt.map(h.groupby("uavt").yatak_tahmini.sum()).fillna(0)
m["itfaiye_sayisi"] = m.uavt.map(f[f.sar_ekip_kaynagi].groupby("uavt").size()).fillna(0).astype(int)
m["toplanma_alani_m2"] = m.uavt.map(a[a.toplanma_uygun].groupby("uavt").alan_m2.sum()).fillna(0)

# ---- türetilmiş oranlar ----
bt = m.bina_toplam
m["eski_bina_oran"] = (m.bina_1980_oncesi / bt).round(4)
m["orta_yas_bina_oran"] = (m.bina_1980_2000 / bt).round(4)
m["yuksek_bina_oran"] = ((m.kat_5_9 + m.kat_9_19) / bt).round(4)
m["cok_yuksek_bina_oran"] = (m.kat_9_19 / bt).round(4)
m["bina_yogunlugu_km2"] = (bt / m.alan_km2).round(1)
m["nufus_yogunlugu_km2"] = (m.nufus_2025 / m.alan_km2).round(1)
m["kisi_per_bina"] = (m.nufus_2025 / bt).round(2)
m["hasar_agir_ustu"] = m.bina_cok_agir + m.bina_agir
m["hasar_agir_ustu_oran"] = (m.hasar_agir_ustu / bt).round(4)
m["hasar_orta_ustu_oran"] = ((m.hasar_agir_ustu + m.bina_orta) / bt).round(4)
m["can_kaybi_binde"] = (1000 * m.can_kaybi / m.nufus_2025).round(3)
m["toplanma_m2_kisi"] = (m.toplanma_alani_m2 / m.barinma_kisi.replace(0, np.nan)).round(2)
log(ADIM, "Türetme", "Mutlak sayılar büyük mahalleyi riskli gösterir (ölçek etkisi)", len(m),
    "Oranlar üretildi: hasar_agir_ustu_oran (hedef değişken adayı), eski/yüksek bina oranı, yoğunluklar, can_kaybi_binde",
    "Model ve haritalar oran üzerinden kurulur; can_kaybi_binde paydası 2025 nüfusu, İBB'nin kullandığı nüfus yayımlanmadı (yaklaşık)")

# ---- uçtan uca değişmezlik ----
ham = pd.read_csv(IBB / "deprem-senaryosu-analiz-sonuclar.csv", sep=";", encoding="cp1254")
for kaynak, hedef in (("cok_agir_hasarli_bina_sayisi", "bina_cok_agir"), ("can_kaybi_sayisi", "can_kaybi"), ("gecici_barinma", "barinma_hane"),
                      ("hastanede_tedavi_sayisi", "hastanede_tedavi")):
    qc(ADIM, f"Toplam korunuyor: {hedef}", int(ham[kaynak].sum()) == int(m[hedef].sum()), f"{int(m[hedef].sum()):,}")
qc(ADIM, "Hasarlı bina oranı [0,1]", bool(m.hasar_orta_ustu_oran.between(0, 1).all()), f"maks {m.hasar_orta_ustu_oran.max():.2f}")
qc(ADIM, "Hastane yatak toplamı korunuyor", abs(m.hastane_yatak_tahmini.sum() - h.yatak_tahmini.sum()) < 1, f"{m.hastane_yatak_tahmini.sum():,.0f}")

# ---- sözlük ile sütun uyumu ----
eksik = [c for c in m.columns if c not in SOZLUK and c != "geometry"]
fazla = [c for c in SOZLUK if c not in m.columns]
qc(ADIM, "Her sütunun sözlük tanımı var", not eksik, f"tanımsız: {eksik}" if eksik else f"{len(SOZLUK)} sütun")
if fazla:
    print("  sözlükte olup tabloda olmayan:", fazla)
m = m[[c for c in SOZLUK if c in m.columns] + eksik + ["geometry"]]
m.to_parquet(PROCESSED / "mahalle.parquet", index=False)
pd.DataFrame([dict(sutun=k, aciklama=v[0], birim=v[1], kaynak=v[2], veri_turu=v[3]) for k, v in SOZLUK.items() if k in m.columns]
             ).to_parquet(INTERIM / "veri_sozlugu.parquet", index=False)
print(f"  -> data/processed/mahalle.parquet: {len(m)} satır, {m.shape[1]} sütun")
print("  boş hücre olan sütunlar:", {c: int(n) for c, n in m.isna().sum().items() if n})
