"""Ham verileri indirir (yalnızca eksik olanları). İBB portalı CKAN API'si üzerinden kaynak adresini kendisi bulur.

Elle konması gerekenler (indirilebilir bağlantısı olmayan): data/raw/external/ altındaki TÜİK mahalle nüfusu (veri portalı
pivot çıktısı), İBB 2018 sosyal görebilirlik ilçe puanları (PDF'ten aktarılmış) ve GEM fay izleri. Bunlar repoda değil,
KAYNAKLAR.md'de nasıl üretildikleri yazılı.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import urllib.request

from ortak import BUYUK, IBB, USGS

IBB_API = "https://data.ibb.gov.tr/api/3/action/package_show?id="
# yerel dosya -> (İBB veri seti, kaynak adında aranacak parça)
IBB_DOSYA = {
    "deprem-senaryosu-analiz-sonuclar.csv": ("deprem-senaryosu-analiz-sonuclari", ""),
    "2017-yl-mahalle-bazl-bina-saylar.csv": ("mahalle-bazli-bina-analiz-verisi", ""),
    "acil_ulasim_yollari.geojson": ("1-derece-acil-ulasim-yollari-verisi", ""),
    "ulasim_sanat_yapilari.geojson": ("ulasim-sanat-yapilari-veri-seti", ""),
    "kentsel_acik_yesil_alanlar.geojson": ("kentsel-acik-ve-yesil-alanlar", ""),
    "itfaiye_istasyon_2025.xlsx": ("itfaiye-istasyonlari-konum-bilgileri", "2025"),
    "saglik_tesisleri.xlsx": ("istanbul-saglik-kurum-ve-kuruluslari-verisi", ""),
    "muhtarlik_lokasyon.geojson": ("muhtarlik-adres-bilgileri", ""),
    "sosyal_yardim_hane_2025.xlsx": ("mahallelere-gore-sosyal-yardim-alan-hane-sayisi", "2025"),
    "sosyal_yardim_hane_2023.xlsx": ("mahallelere-gore-sosyal-yardim-alan-hane-sayisi", "2023"),
    "ilce_hane_buyuklugu.xlsx": ("ilce-bazli-ortalama-hane-halki-buyuklugu", ""),
    "saglik_indeksi_34dk.geojson": ("34-dakika-istanbul-saglik-indeksi", "geojson"),
    "vdym_engelli_hane.xlsx": ("vdym-ilce-bazinda-engelli-birey-bulunan-hane-sayisi", ""),
    "vdym_kronik_hane.xlsx": ("vdym-ilce-bazinda-kronik-hastaligi-olan-hane-sayisi", ""),
    "yapi_ruhsat_bina.xls": ("yapi-ruhsatina-gore-bina-sayisi", ""),
}
USGS_URL = "https://earthquake.usgs.gov/product/shakemap/us7000pufs/us/1750394276366/download/"
GEOFABRIK = "https://download.geofabrik.de/europe/turkey-261008.osm.pbf"
OVERTURE = "s3://overturemaps-us-west-2/release/2026-09-23.1/theme=buildings/type=building/*"
VS30 = "https://apps.usgs.gov/shakemap_geodata/vs30/global_vs30.tif"


def indir(url: str, hedef) -> None:
    if hedef.exists():
        return
    hedef.parent.mkdir(parents=True, exist_ok=True)
    print(f"  indiriliyor: {hedef.name}")
    with urllib.request.urlopen(url, timeout=600) as r, open(hedef, "wb") as f:
        while blok := r.read(1 << 20):
            f.write(blok)


for dosya, (ds, parca) in IBB_DOSYA.items():
    if (IBB / dosya).exists():
        continue
    kaynak = json.load(urllib.request.urlopen(IBB_API + ds, timeout=60))["result"]["resources"]
    aday = [k for k in kaynak if parca.lower() in (k["name"] + k["url"]).lower() and k.get("format", "").upper() != "HTML"]
    indir(aday[-1]["url"], IBB / dosya)

for f in ("stationlist.json", "grid.xml", "info.json", "rupture.json", "uncertainty.xml"):
    indir(USGS_URL + f, USGS / f)

pbf = BUYUK / GEOFABRIK.rsplit("/", 1)[1]
indir(GEOFABRIK, pbf)
beklenen = urllib.request.urlopen(GEOFABRIK + ".md5", timeout=60).read().decode().split()[0]
h = hashlib.md5()
with open(pbf, "rb") as f:
    while blok := f.read(1 << 24):
        h.update(blok)
if h.hexdigest() != beklenen:
    sys.exit(f"MD5 uyuşmuyor: {pbf.name}")

if not (BUYUK / "overture_bina_istanbul_bbox.parquet").exists():
    import duckdb
    print("  Overture binaları (S3, ~5 dk)")
    con = duckdb.connect()
    con.sql("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial; SET s3_region='us-west-2';")
    con.sql(f"""COPY (SELECT id, height, num_floors, class, subtype, list_transform(sources, s -> s.dataset) AS kaynak,
                ST_AsWKB(geometry) AS geom_wkb, (bbox.xmin+bbox.xmax)/2 AS lon, (bbox.ymin+bbox.ymax)/2 AS lat
                FROM read_parquet('{OVERTURE}', hive_partitioning=1)
                WHERE bbox.xmin > 27.95 AND bbox.xmax < 29.95 AND bbox.ymin > 40.78 AND bbox.ymax < 41.60)
             TO '{BUYUK / 'overture_bina_istanbul_bbox.parquet'}' (FORMAT parquet, COMPRESSION zstd)""")

if not (BUYUK / "vs30_mosaic_median_30c.tif").exists():
    print(f"  Vs30 mozaiği elle indirilmeli (~1 GB): {VS30} -> data/raw/buyuk/vs30_mosaic_median_30c.tif")
subprocess.run(["osmium", "--version"], check=True, capture_output=True)
print("00_indir: tamam")
