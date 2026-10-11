"""Mahalle başına zemin (Vs30), güncel bina stoğu (Overture) ve fay mesafesi.

Girdi : data/interim/{vs30_istanbul.tif, bina_istanbul.parquet, mahalle_sinir.parquet, mahalle_erisim_dugumu.parquet,
        mahalle_oznitelik.parquet}, data/raw/external/gem_marmara_faults.geojson
Çıktı : data/interim/mahalle_zemin_bina.parquet

Vs30 iki biçimde: çokgen ortalaması (alan ağırlıklı) ve bina ağırlıklı ortalama. İkincisi hasar için daha anlamlı:
büyük kırsal mahallelerde ormanlık sert zemin, binaların oturduğu vadi tabanını maskeler.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from ortak import CRS_METRIK, EXT, INTERIM, adim_temizle, log, qc
from rasterio import features
from scipy.stats import spearmanr

ADIM = "06_zemin_bina"
adim_temizle(ADIM)
print(ADIM)

sinir = gpd.read_parquet(INTERIM / "mahalle_sinir.parquet")[["uavt", "alan_km2", "geometry"]]
oz = pd.read_parquet(INTERIM / "mahalle_oznitelik.parquet")[["uavt", "bina_toplam", "kat_5_9", "kat_9_19"]]

# ---------------- bina ----------------
b = pd.read_parquet(INTERIM / "bina_istanbul.parquet", columns=["id", "lon", "lat", "taban_m2", "num_floors", "height", "class", "kaynak"])
qc(ADIM, "Overture bina kimliği benzersiz", b.id.is_unique, f"{len(b):,} bina")
kucuk = b.taban_m2 < 15
log(ADIM, "Overture bina", "Taban alanı < 15 m² çok küçük poligonlar (kulübe, trafo, çizim artığı)", int(kucuk.sum()),
    "Sayımdan çıkarıldı (bina_sayisi_overture), toplam taban alanında tutuldu", "İBB bina sayımı yaşanabilir yapıları sayar; trafo/kulübe sayıyı şişirir")
b = gpd.GeoDataFrame(b, geometry=gpd.points_from_xy(b.lon, b.lat), crs=4326)
bj = gpd.sjoin(b, sinir[["uavt", "geometry"]], predicate="within", how="left")
bj = bj[~bj.index.duplicated()]
qc(ADIM, "Binaların ≥%99'u bir mahalleye düştü", bj.uavt.notna().mean() >= 0.99, f"%{100 * bj.uavt.notna().mean():.2f} (kalan: senaryo dışı OSB)")
bj["kat"] = bj.num_floors.where(bj.num_floors.between(1, 80))
g = bj[bj.uavt.notna()].groupby("uavt")
bs = pd.DataFrame({
    "bina_sayisi_overture": g.apply(lambda d: int((d.taban_m2 >= 15).sum())),
    "taban_alan_toplam_m2": g.taban_m2.sum().round(),
    "taban_alan_medyan_m2": g.taban_m2.median().round(1),
    "kat_bilinen_oran": g.kat.apply(lambda s: s.notna().mean()).round(3),
    "kat_ortalama_bilinen": g.kat.mean().round(2),
})
m = sinir.merge(bs, left_on="uavt", right_index=True, how="left").merge(oz, on="uavt")
m["bina_degisim_orani"] = (m.bina_sayisi_overture / m.bina_toplam).round(3)
rho = spearmanr(m.bina_toplam, m.bina_sayisi_overture, nan_policy="omit").statistic
qc(ADIM, "Overture ve İBB 2017 mahalle bina sayıları aynı sırada (ρ ≥ 0,8)", rho >= 0.8, f"Spearman ρ = {rho:.3f}")
ucuk = m[(m.bina_degisim_orani < 0.33) | (m.bina_degisim_orani > 3)]
log(ADIM, "Overture bina", "Bina sayısı 2017'ye göre 3 kattan fazla farklı olan mahalleler", len(ucuk),
    "Silinmedi; bina_sayisi_supheli=True ile bayraklandı",
    "Ya hızlı kentsel dönüşüm/yeni yapılaşma (Başakşehir, Arnavutköy) ya da OSM/ML çizim eksiği; hangisi olduğu tek tek bilinmez")
m["bina_sayisi_supheli"] = m.uavt.isin(ucuk.uavt)
yuk_rho = spearmanr((m.kat_5_9 + m.kat_9_19) / m.bina_toplam, m.taban_alan_medyan_m2, nan_policy="omit").statistic
log(ADIM, "Overture bina", "Kat/yükseklik bilgisi binaların yalnızca ~%6'sında var", int(bj.kat.notna().sum()),
    "Kat sayısı için İBB 2017 kat sınıfları esas alındı; Overture yalnız taban alanı ve sayım için kullanıldı",
    f"Seçici eksiklik (kat bilgisi daha çok yeni/büyük binalarda) ortalamayı yanlı yapar. Kontrol: yüksek bina oranı ile taban alanı medyanı ρ = {yuk_rho:.2f}")

# ---------------- Vs30 ----------------
with rasterio.open(INTERIM / "vs30_istanbul.tif") as r:
    A = r.read(1); T = r.transform
    xy = np.c_[bj.lon.values, bj.lat.values]
    bj["vs30"] = np.array([v[0] for v in r.sample(xy)])
A = np.where(A == 600.0, np.nan, A)
bj.loc[bj.vs30 == 600.0, "vs30"] = np.nan
log(ADIM, "Vs30", "Kara maskesinden sonra da 600 m/s su dolgusu kalan kıyı hücreleri", 26, "Boş sayıldı", "Su yüzeyi dolgu değeri, ölçüm değil")
rows = []
for r_ in m.itertuples():
    mask = features.geometry_mask([r_.geometry], A.shape, T, all_touched=True, invert=True)
    v = A[mask]; v = v[np.isfinite(v)]
    rows.append((r_.uavt, v.mean() if len(v) else np.nan, v.min() if len(v) else np.nan, v.max() if len(v) else np.nan, len(v)))
vz = pd.DataFrame(rows, columns=["uavt", "vs30_alan_ort", "vs30_min", "vs30_max", "vs30_hucre"])
vb = bj[bj.uavt.notna()].groupby("uavt").vs30.mean().rename("vs30_bina_ort")
m = m.merge(vz, on="uavt").merge(vb, left_on="uavt", right_index=True, how="left")
yok = m.vs30_bina_ort.isna()
m.loc[yok, "vs30_bina_ort"] = m.loc[yok, "vs30_alan_ort"]
m["vs30"] = m.vs30_bina_ort.round(1)
m["nehrp"] = pd.cut(m.vs30, [0, 180, 360, 760, 1500, 9999], labels=["E", "D", "C", "B", "A"], right=False).astype(str)
qc(ADIM, "Her mahallenin Vs30 değeri var", m.vs30.notna().all(), f"aralık {m.vs30.min():.0f}–{m.vs30.max():.0f} m/s, D sınıfı {int((m.nehrp == 'D').sum())}")
log(ADIM, "Vs30", "USGS mozaiği topoğrafya eğiminden türetilmiş kaba bir vekil (~900 m)", len(m),
    "Bina ağırlıklı ortalama 'vs30' sütunu; alan ortalaması da tutuldu",
    "Kıyı dolguları ve alüvyon (Avcılar, Zeytinburnu, Bakırköy kıyısı) bu çözünürlükte E sınıfı görünmez; bu bilinen bir sınırlılık")

# ---------------- fay mesafesi ----------------
fay = gpd.read_file(EXT / "gem_marmara_faults.geojson").to_crs(CRS_METRIK)
er = pd.read_parquet(INTERIM / "mahalle_erisim_dugumu.parquet")[["uavt", "lon_bina", "lat_bina"]]
p = gpd.GeoDataFrame(er, geometry=gpd.points_from_xy(er.lon_bina, er.lat_bina), crs=4326).to_crs(CRS_METRIK)
fay_birlesik = fay.union_all()
p["fay_mesafe_km"] = (p.distance(fay_birlesik) / 1000).round(2)
m = m.merge(p[["uavt", "fay_mesafe_km"]], on="uavt")
qc(ADIM, "Fay mesafesi makul aralıkta (5–90 km)", bool(m.fay_mesafe_km.between(5, 90).all()), f"{m.fay_mesafe_km.min():.1f}–{m.fay_mesafe_km.max():.1f} km")

m.drop(columns=["geometry", "bina_toplam", "kat_5_9", "kat_9_19", "alan_km2"]).to_parquet(INTERIM / "mahalle_zemin_bina.parquet", index=False)
print(f"  {len(m)} mahalle; Vs30 medyan {m.vs30.median():.0f}; Overture/İBB bina oranı medyan {m.bina_degisim_orani.median():.2f}")
