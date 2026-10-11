"""Büyük kaynaklardan İstanbul'u kesip çıkarır.

Girdi : data/raw/buyuk/turkey-*.osm.pbf (Geofabrik, ~650 MB), overture_bina_istanbul_bbox.parquet (Overture 2026-09-23.1,
        bbox sorgusu, 1,3 M bina), vs30_mosaic_median_30c.tif (USGS küresel, ~1 GB)
Çıktı : data/interim/istanbul_sinir.geojson, istanbul.osm.pbf, idari_sinirlar.geojson, bina_istanbul.parquet, vs30_istanbul.tif

Kesme sınırı OSM'deki İstanbul il ilişkisi (admin_level=4). Önceki sürümdeki ilçe birleşimi + 200 m tampon yerine resmî
il sınırı kullanılır; tampon Kocaeli/Tekirdağ kıyısından kayıt sızdırıyordu.
"""
from __future__ import annotations

import subprocess

import duckdb
import geopandas as gpd
import numpy as np
import rasterio
from ortak import BUYUK, CRS_METRIK, INTERIM, adim_temizle, log, qc
from rasterio.mask import mask

ADIM = "01_istanbul_kirp"
adim_temizle(ADIM)
print(ADIM)
PBF = sorted(BUYUK.glob("turkey-*.osm.pbf"))[-1]


def osmium(*args: str) -> None:
    subprocess.run(["osmium", *args, "--overwrite"], check=True, capture_output=True)


# --- 1) idari sınırlar ve il poligonu ---
bbox_pbf = INTERIM / "marmara_bbox.osm.pbf"
osmium("extract", "-b", "27.9,40.7,30.0,41.7", "-s", "smart", str(PBF), "-o", str(bbox_pbf))
osmium("tags-filter", str(bbox_pbf), "r/boundary=administrative", "-o", str(INTERIM / "admin.osm.pbf"))
osmium("export", str(INTERIM / "admin.osm.pbf"), "-o", str(INTERIM / "admin.geojson"), "-f", "geojson", "--geometry-types=polygon", "-a", "id")
adm = gpd.read_file(INTERIM / "admin.geojson")
il = adm[(adm.admin_level == "4") & (adm["name"] == "İstanbul")]
qc(ADIM, "OSM'de tek İstanbul il poligonu", len(il) == 1, f"{len(il)} kayıt")
il = il[["name", "geometry"]].reset_index(drop=True)
il_poly = il.geometry.iloc[0]
il_alan = il.to_crs(CRS_METRIK).area.iloc[0] / 1e6
log(ADIM, "OSM sınır", f"OSM il ilişkisi karasularını da kapsıyor ({il_alan:,.0f} km²)", 1,
    "Kesim için iki sınır tutuldu: il (deniz dahil; köprü, ada, kıyı yolu kaybolmasın) ve kara (mahalle poligonlarının birleşimi)",
    "Bina, zemin ve nüfus gibi kara katmanları deniz alanıyla bölünürse yoğunluklar yarıya düşer")
il.to_file(INTERIM / "istanbul_sinir.geojson", driver="GeoJSON")

ic = adm[adm.representative_point().within(il_poly)]
ilce = ic[(ic.admin_level == "6") & ic["name"].notna() & (ic["name"] != "Ocaklı Ada")][["@id", "name", "geometry"]]
mah = ic[ic.admin_level == "8"][["@id", "name", "geometry"] + [c for c in ("addr:district", "addr:city", "alt_name", "old_name") if c in ic.columns]]
qc(ADIM, "İl içinde 39 ilçe poligonu", len(ilce) == 39, f"{len(ilce)} ilçe")
kara = gpd.GeoDataFrame(geometry=[mah.union_all()], crs=4326)
kara_alan = kara.to_crs(CRS_METRIK).area.iloc[0] / 1e6
# TÜİK karasal yüzölçümü 5.343 km² (iç sular hariç); mahalle poligonları göl/baraj alanını da kapsar, %3 tolerans
qc(ADIM, "Kara alanı TÜİK yüzölçümüyle uyumlu", abs(kara_alan - 5343) / 5343 < 0.03, f"{kara_alan:,.0f} km² (TÜİK 5.343)")
kara.to_file(INTERIM / "istanbul_kara.geojson", driver="GeoJSON")
ilce.to_file(INTERIM / "osm_ilce.geojson", driver="GeoJSON")
mah.to_file(INTERIM / "osm_mahalle.geojson", driver="GeoJSON")
print(f"  mahalle poligonu (admin_level=8): {len(mah)}")
kara_poly = kara.geometry.iloc[0]

# --- 2) OSM'yi il sınırına kes ---
osmium("extract", "-p", str(INTERIM / "istanbul_sinir.geojson"), "-s", "complete_ways", str(bbox_pbf), "-o", str(INTERIM / "istanbul.osm.pbf"))
log(ADIM, "OSM", f"Türkiye dosyası ({PBF.stat().st_size / 1e6:,.0f} MB) analiz için gereğinden büyük", 1,
    "osmium ile önce Marmara kutusu, sonra il poligonu (complete_ways) ile kesildi",
    "complete_ways sınırı kesen yolların tamamını tutar; il sınırında yol ağı kopmaz")

# Tesis etiketleri (hastane, itfaiye, park/saha, toplanma noktası); 04_tesisler girdisi
tesis_pbf = INTERIM / "_tesis.osm.pbf"
osmium("tags-filter", str(INTERIM / "istanbul.osm.pbf"), "nwr/amenity=hospital,fire_station,clinic", "nwr/healthcare=hospital",
       "nwr/emergency=assembly_point,ambulance_station", "nwr/leisure=park,pitch,stadium,sports_centre,garden,playground",
       "nwr/landuse=recreation_ground,grass,cemetery", "-o", str(tesis_pbf))
osmium("export", str(tesis_pbf), "-o", str(INTERIM / "osm_tesis.geojsonseq"), "-f", "geojsonseq", "-a", "type,id")
tesis_pbf.unlink()

# --- 3) Overture binaları ---
con = duckdb.connect()
con.sql("INSTALL spatial; LOAD spatial;")
con.sql(f"CREATE TABLE il AS SELECT ST_GeomFromText('{kara_poly.wkt}') AS g")
ham = con.sql(f"SELECT count(*) FROM '{BUYUK / 'overture_bina_istanbul_bbox.parquet'}'").fetchone()[0]
con.sql(f"""
COPY (
  SELECT b.id, b.height, b.num_floors, b.class, b.subtype, b.kaynak, b.lon, b.lat,
         ST_Area_Spheroid(ST_FlipCoordinates(ST_GeomFromWKB(b.geom_wkb))) AS taban_m2,
         b.geom_wkb
  FROM '{BUYUK / 'overture_bina_istanbul_bbox.parquet'}' b, il
  WHERE ST_Contains(il.g, ST_Point(b.lon, b.lat))
) TO '{INTERIM / 'bina_istanbul.parquet'}' (FORMAT parquet, COMPRESSION zstd)""")
n, n_h, n_k = con.sql(f"SELECT count(*), count(height), count(num_floors) FROM '{INTERIM / 'bina_istanbul.parquet'}'").fetchone()
log(ADIM, "Overture bina", "Kutu sorgusu Kocaeli/Tekirdağ binalarını da içeriyor", ham - n,
    "Bina merkezi kara poligonunun içinde olanlar tutuldu", "Bina merkez noktası tek bir ile düşer; sınırdaki bina çift sayılmaz")
qc(ADIM, "Overture İstanbul bina sayısı İBB 2017 (1,17 M) ile aynı mertebede", 0.8e6 < n < 2.0e6, f"{n:,} bina")
print(f"  bina: {n:,}; yükseklik dolu {n_h:,} (%{100 * n_h / n:.1f}), kat dolu {n_k:,} (%{100 * n_k / n:.1f})")

# --- 4) Vs30 ---
with rasterio.open(BUYUK / "vs30_mosaic_median_30c.tif") as r:
    out, tr = mask(r, [kara_poly.__geo_interface__], crop=True, nodata=np.nan, filled=True, all_touched=True)
    prof = r.profile | dict(height=out.shape[1], width=out.shape[2], transform=tr, nodata=np.nan, compress="deflate")
a = out[0]
n600 = int(np.nansum(a == 600.0))
with rasterio.open(INTERIM / "vs30_istanbul.tif", "w", **prof) as w:
    w.write(out)
gec = np.isfinite(a)
log(ADIM, "Vs30", "Mozaikte su yüzeyleri 600 m/s sabit değerle doldurulmuş", n600,
    "Kara poligonuyla kesildikten sonra kalan 600 m/s hücreleri 06_zemin_bina'da su/dolgu olarak işaretlenir",
    "Değer eşitliğiyle silmek kara üstündeki gerçek 600 m/s hücreleri de siler; önce kara maskesi, sonra değer kontrolü")
qc(ADIM, "Vs30 kesiti boyutu makul", 5000 < gec.sum() < 20000, f"{out.shape[1]}x{out.shape[2]}, geçerli {int(gec.sum()):,} hücre, 600'lük {n600}")
