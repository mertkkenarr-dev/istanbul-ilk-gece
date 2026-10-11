"""Araç yol ağı grafı (sokak düzeyi dahil) ve deprem kırılganlığı için kenar etiketleri.

Girdi : data/interim/istanbul.osm.pbf, acil_yol.parquet, sanat_yapisi.parquet, mahalle_sinir.parquet, bina_istanbul.parquet
Çıktı : data/interim/yol_dugum.parquet, yol_kenar.parquet (GeoParquet), yol_agi.graphml, mahalle_erisim_dugumu.parquet

v1 yalnızca ana yolları (otoyol → tertiary) kullanıyordu; mahalle merkezlerinin %5'i yola 1 km'den uzaktı. Burada
residential ve living_street de alınır. osmnx sadeleştirmesi (simplify) kavşak olmayan ara düğümleri birleştirir.
Hızlar gece 03:00 serbest akış varsayımıdır (senaryo saati); maxspeed etiketi varsa o, yoksa yol sınıfı varsayılanı.
"""
from __future__ import annotations

import subprocess
import time

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
import shapely
from ortak import CRS_METRIK, INTERIM, adim_temizle, log, qc

ADIM = "05_yol_agi"
adim_temizle(ADIM)
print(ADIM)

SURULEBILIR = ["motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link",
               "tertiary", "tertiary_link", "unclassified", "residential", "living_street"]
# km/sa; Karayolları Trafik Yönetmeliği şehir içi sınırları ve OSM Türkiye varsayılanları
HIZ = {"motorway": 100, "motorway_link": 50, "trunk": 82, "trunk_link": 40, "primary": 60, "primary_link": 40, "secondary": 50,
       "secondary_link": 30, "tertiary": 40, "tertiary_link": 30, "unclassified": 30, "residential": 30, "living_street": 15}

xml = INTERIM / "_yol_surulebilir.osm"
subprocess.run(["osmium", "tags-filter", str(INTERIM / "istanbul.osm.pbf"), "w/highway=" + ",".join(SURULEBILIR),
                "-o", str(xml), "-f", "osm", "--overwrite"], check=True, capture_output=True)
ox.settings.useful_tags_way = list(set(ox.settings.useful_tags_way + ["bridge", "tunnel", "layer", "surface"]))
t0 = time.time()
G = ox.graph_from_xml(xml, bidirectional=False, simplify=True, retain_all=True)
xml.unlink()
print(f"  graf okundu: {G.number_of_nodes():,} düğüm, {time.time() - t0:.0f} sn", flush=True)
n_ham_d, n_ham_k = G.number_of_nodes(), G.number_of_edges()

# En büyük güçlü bağlı bileşen dışındaki parçalar (site içi yollar, kopuk eşleme hataları) erişim hesabını bozar
bilesen = max(nx.strongly_connected_components(G), key=len)
kopuk = n_ham_d - len(bilesen)
G = G.subgraph(bilesen).copy()
log(ADIM, "Yol ağı", "Ana ağa bağlı olmayan yol parçaları (kapalı siteler, tek yön hataları, eşleme kopuklukları)", kopuk,
    f"En büyük güçlü bağlı bileşen tutuldu: {G.number_of_nodes():,}/{n_ham_d:,} düğüm (%{100 * G.number_of_nodes() / n_ham_d:.1f})",
    "Güçlü bağlı olmayan düğümden çıkış veya o düğüme varış yolu olmayabilir; erişim süresi sonsuz çıkar")
qc(ADIM, "Ağın ≥%95'i tek güçlü bileşende", G.number_of_nodes() / n_ham_d >= 0.95, f"%{100 * G.number_of_nodes() / n_ham_d:.1f}")

G = ox.add_edge_speeds(G, hwy_speeds=HIZ, fallback=30)
G = ox.add_edge_travel_times(G)
dug, ken = ox.graph_to_gdfs(G)
ken = ken.reset_index()
for c in ("highway", "bridge", "tunnel", "name", "maxspeed", "oneway", "lanes", "osmid", "layer", "ref"):
    if c in ken:
        ken[c] = ken[c].map(lambda v: "|".join(map(str, v)) if isinstance(v, list) else v)
ken["sinif"] = ken.highway.str.split("|").str[0]
hiz_etiket = ken.maxspeed.notna().mean() if "maxspeed" in ken else 0
log(ADIM, "Yol ağı", "maxspeed etiketi kenarların çoğunda yok", int(ken.maxspeed.isna().sum()) if "maxspeed" in ken else len(ken),
    f"Etiket varsa o (%{100 * hiz_etiket:.0f}), yoksa sınıf varsayılanı (HIZ tablosu); gece serbest akış",
    "Senaryo gece 03:00; trafik yoğunluğu ihmal edilebilir, hasar kaynaklı yavaşlama simülasyonda ayrıca modellenir")

# ---- İBB 1. derece acil ulaşım yolu: kenarın ≥%60'ı 25 m tamponun içindeyse ----
km = ken.to_crs(CRS_METRIK)
acil = gpd.read_parquet(INTERIM / "acil_yol.parquet").to_crs(CRS_METRIK)
# Kenar boyunca ~10 m'de bir örnek nokta; noktaların ≥%60'ı acil yol çizgisine ≤25 m ise kenar acil yoldur.
# (Dev bir tampon poligonuyla kesişim almak 400 bin kenarda saatler sürüyordu; nokta örneklemesi aynı ölçüyü dakikada verir.)
agac = shapely.STRtree(acil.geometry.values)
aday = np.unique(agac.query(km.geometry.values, predicate="dwithin", distance=25)[0])
ic = np.zeros(len(km))
for i in aday:
    g = km.geometry.values[i]
    t = np.linspace(0, 1, max(2, int(g.length // 10) + 1))
    pts = shapely.line_interpolate_point(g, t, normalized=True)
    yakin = np.unique(agac.query(pts, predicate="dwithin", distance=25)[0])
    ic[i] = len(yakin) / len(pts)
ken["acil_yol"] = ic >= 0.6
# Kapsama İBB tarafından ölçülür: İBB acil yol çizgisi boyunca örnek noktaların ne kadarı bir acil_yol kenarına ≤25 m
agac_k = shapely.STRtree(km.geometry.values[ken.acil_yol.values])
ornek = [shapely.line_interpolate_point(g, np.linspace(0, 1, max(2, int(g.length // 20) + 1)), normalized=True) for g in acil.geometry]
ornek = np.concatenate(ornek)
bulunan = np.unique(agac_k.query(ornek, predicate="dwithin", distance=25)[0])
kapsama = len(bulunan) / len(ornek)
qc(ADIM, "İBB acil yollarının ≥%85'i grafta acil_yol kenarıyla karşılanıyor", kapsama >= 0.85, f"%{100 * kapsama:.1f} ({len(ornek):,} örnek nokta)")

# ---- köprü/viyadük/tünel: OSM etiketi + İBB sanat yapısı eşleşmesi ----
sy = gpd.read_parquet(INTERIM / "sanat_yapisi.parquet").to_crs(CRS_METRIK)
yapi_kenar = gpd.sjoin_nearest(km[["geometry"]], sy[["ID", "tur", "malzeme", "geometry"]], how="inner", max_distance=12, distance_col="d")
yapi_kenar = yapi_kenar[~yapi_kenar.index.duplicated()]
ken["sanat_yapisi_id"] = yapi_kenar.ID.reindex(ken.index)
ken["sanat_yapisi_tur"] = yapi_kenar.tur.reindex(ken.index)
osm_yapi = ken.bridge.fillna("no").ne("no") | ken.tunnel.fillna("no").ne("no")
ken["kritik_yapi"] = osm_yapi | ken.sanat_yapisi_id.notna()
ken["kritik_yapi_kaynagi"] = np.select([osm_yapi & ken.sanat_yapisi_id.notna(), osm_yapi, ken.sanat_yapisi_id.notna()],
                                       ["osm+ibb", "osm", "ibb"], default=None)
log(ADIM, "Yol ağı", "Köprü/viyadük/tünel bilgisi iki kaynakta farklı kapsamda", int(ken.kritik_yapi.sum()),
    "OSM bridge/tunnel etiketi VEYA 12 m içinde İBB sanat yapısı → kritik_yapi; kaynak sütunu tutuldu",
    "Simülasyonda bu kenarlar ayrı kırılganlık eğrisi alır; tek kaynak eksik kalır (İBB alt geçitleri OSM'de çoğu zaman etiketsiz)")

# ---- mahalle erişim düğümü: bina ağırlıklı merkez → en yakın düğüm ----
sinir = gpd.read_parquet(INTERIM / "mahalle_sinir.parquet")
bn = pd.read_parquet(INTERIM / "bina_istanbul.parquet", columns=["lon", "lat", "taban_m2"])
bn = gpd.GeoDataFrame(bn, geometry=gpd.points_from_xy(bn.lon, bn.lat), crs=4326)
bj = gpd.sjoin(bn, sinir[["uavt", "geometry"]], predicate="within")
w = bj.assign(wx=bj.lon * bj.taban_m2, wy=bj.lat * bj.taban_m2).groupby("uavt")[["wx", "wy", "taban_m2"]].sum()
agirlik = pd.DataFrame({"lon_bina": w.wx / w.taban_m2, "lat_bina": w.wy / w.taban_m2})
sinir = sinir.merge(agirlik, left_on="uavt", right_index=True, how="left")
yok = sinir.lon_bina.isna()
sinir.loc[yok, ["lon_bina", "lat_bina"]] = sinir.loc[yok, ["lon_ic", "lat_ic"]].values
log(ADIM, "Erişim", "Mahalle erişim noktası olarak çokgen merkezi, ormanlık/büyük mahallelerde yerleşimin dışına düşebiliyor", len(sinir),
    f"Bina taban alanı ağırlıklı merkez kullanıldı; binası olmayan {int(yok.sum())} mahallede çokgen iç noktası",
    "Erişim süresi insanların yaşadığı yerden ölçülmeli")
x, y = sinir.lon_bina.values, sinir.lat_bina.values
nn, dist = ox.distance.nearest_nodes(G, x, y, return_dist=True)
erisim = pd.DataFrame({"uavt": sinir.uavt, "lon_bina": x, "lat_bina": y, "dugum": nn, "dugume_mesafe_m": np.round(dist, 1)})
# Adalar'ın yolları ana ağa bağlı değil (köprü yok); en yakın düğüm denizin karşısında kalır. Bu mahalleler denizden erişilir.
ada = dist > 1500
erisim["yol_erisimi"] = np.where(ada, "deniz", "kara")
erisim.loc[ada, "dugum"] = pd.NA
log(ADIM, "Erişim", "Erişim noktası ana yol ağına 1,5 km'den uzak mahalleler (Adalar)", int(ada.sum()),
    "yol_erisimi='deniz', düğüm boş bırakıldı", "Ana ağa köprüsü olmayan adada kara yolu süresi anlamsız; simülasyonda deniz lojistiği ayrı modellenir")
kd = dist[dist <= 1500]
qc(ADIM, "Kara mahallelerinin %95'inde erişim noktası yola ≤300 m", float(np.percentile(kd, 95)) <= 300,
   f"medyan {np.median(kd):.0f} m, %95 {np.percentile(kd, 95):.0f} m, maks {kd.max():.0f} m")

# ---- yaz ----
dug = dug.loc[list(G.nodes)].reset_index()
dug = dug[[c for c in ("osmid", "x", "y", "street_count", "highway", "geometry") if c in dug.columns]]
ken = ken[["u", "v", "key", "osmid", "sinif", "name", "oneway", "lanes", "length", "speed_kph", "travel_time", "bridge", "tunnel",
           "acil_yol", "sanat_yapisi_id", "sanat_yapisi_tur", "kritik_yapi", "kritik_yapi_kaynagi", "geometry"]]
for c in ("osmid", "name", "oneway", "lanes", "bridge", "tunnel", "sanat_yapisi_id"):
    ken[c] = ken[c].map(lambda v: None if pd.isna(v) else str(v)).astype("string")
dug.to_parquet(INTERIM / "yol_dugum.parquet", index=False)
ken.to_parquet(INTERIM / "yol_kenar.parquet", index=False)
erisim["dugum"] = erisim.dugum.astype("Int64")
erisim.to_parquet(INTERIM / "mahalle_erisim_dugumu.parquet", index=False)
ox.save_graphml(G, INTERIM / "yol_agi.graphml")
print(f"  graf: {len(dug):,} düğüm, {len(ken):,} kenar, {ken["length"].sum() / 1000:,.0f} km yönlü kenar uzunluğu")
print(f"  acil yol kenarı {int(ken.acil_yol.sum()):,}, kritik yapı kenarı {int(ken.kritik_yapi.sum()):,}")
