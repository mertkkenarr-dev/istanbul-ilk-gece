"""6 Şubat 2023 Copernicus EMSR648 bina hasar sınıflandırmasını tek, temiz etiket tablosuna çevirir.

Karar kuralları (her biri temizleme_logu'na yazılır):
  * Her AOI için en güncel ürün kullanılır (MONIT02 > MONIT01 > PRODUCT); izleme ürünleri sonraki görüntüyle üretilmiştir.
  * Yalnızca "tam sınıflandırılmış" AOI'ler: içinde 'No visible damage' etiketli bina olmayan AOI yalnızca hasarlıları işaretlemiştir,
    negatif sınıf yoktur; bu AOI'ler eğitime giremez (aksi halde yıkım oranı %100'e yakın görünür).
  * Poligonlar (builtUpA) temsil noktasına indirgenir, taban alanı saklanır; noktalarda (builtUpP) alan bilinmez.
  * Hedef: yikik = 'Destroyed' (çökme), hasarli_ust = Destroyed + Damaged. 'Possibly damaged' belirsiz sınıftır, ikisinde de 0 sayılır
    ve ayrı bir duyarlılık sütununda tutulur.
Çıktı: data/processed/ders2023/etiket.parquet
"""
from __future__ import annotations

import glob
import re

import geopandas as gpd
import pandas as pd
from ortak_ders import CIKTI, HAM, log, qc

ADIM = "d01_etiketler"
sira = {"MONIT02": 3, "MONIT01": 2, "PRODUCT": 1}
urun = {}
for f in glob.glob(str(HAM / "copernicus_emsr648/acik/*/*builtUp[AP]_*.shp")):
    m = re.search(r"(AOI\d+)_GRA_(PRODUCT|MONIT\d+)_builtUp([AP])", f)
    aoi, tur, geo = m.groups()
    urun.setdefault(aoi, []).append((sira[tur], tur, geo, f))

parca, ozet = [], []
for aoi, liste in sorted(urun.items()):
    _, tur, _, _ = max(liste)
    secilen = [x for x in liste if x[1] == tur]
    g = pd.concat([gpd.read_file(f).to_crs(4326).assign(geo=geo) for _, _, geo, f in secilen], ignore_index=True)
    g = gpd.GeoDataFrame(g, crs=4326)
    sinif = g.damage_gra.value_counts()
    tam = sinif.get("No visible damage", 0) > 0
    ozet.append(dict(aoi=aoi, urun=tur, bina=len(g), tam=tam, **{k: int(v) for k, v in sinif.items()}))
    if not tam:
        continue
    alan = g.to_crs(32637).area.where(g.geom_type.str.contains("Polygon"))
    nokta = g.representative_point()
    parca.append(pd.DataFrame(dict(aoi=aoi, urun=tur, lon=nokta.x, lat=nokta.y, taban_m2=alan.values, sinif=g.damage_gra,
                                   konut=g.obj_type.str.startswith("11"))))

oz = pd.DataFrame(ozet).fillna(0)
print(oz.to_string(index=False))
dis = oz[~oz.tam]
log(ADIM, "Copernicus EMSR648", f"{len(dis)} AOI'de 'No visible damage' sınıfı yok (yalnızca hasarlılar işaretlenmiş): {', '.join(dis.aoi)}",
    int(dis.bina.sum()), "Bu AOI'ler eğitim setinden çıkarıldı",
    "Negatif sınıfı olmayan bölge yıkım oranını yapay olarak %100'e çeker; model şiddet-hasar ilişkisini yanlış öğrenir")
log(ADIM, "Copernicus EMSR648", "Aynı AOI için birden çok ürün (ilk değerlendirme + izleme güncellemeleri) var", int(len(urun)),
    "Her AOI için en güncel ürün seçildi", "İzleme ürünleri daha yeni/daha net görüntüyle üretilir; ürünleri birleştirmek binayı çift sayar")
e = pd.concat(parca, ignore_index=True)
e["yikik"] = (e.sinif == "Destroyed").astype(int)
e["hasarli_ust"] = e.sinif.isin(["Destroyed", "Damaged"]).astype(int)
e["olasi_hasar"] = (e.sinif == "Possibly damaged").astype(int)
qc(ADIM, "Eğitim etiketlerinde iki sınıf da var ve yıkık sayısı ≥ 300", e.yikik.sum() >= 300, f"{len(e)} bina, {e.yikik.sum()} yıkık, {e.hasarli_ust.sum()} hasarlı+")
qc(ADIM, "Koordinatlar deprem bölgesinde", bool(e.lon.between(35.5, 41).all() and e.lat.between(35.8, 38.6).all()), "")
e.to_parquet(CIKTI / "etiket.parquet", index=False)
oz.to_csv(CIKTI / "aoi_ozet.csv", index=False)
print(e.groupby("aoi")[["yikik", "hasarli_ust"]].agg(["sum", "mean"]).round(3).to_string())
