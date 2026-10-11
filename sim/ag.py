"""Simülasyon yol ağı: ana arterler (otoyol → tertiary) ve mahalle/üs/hastane bağlantıları (bir kez kurulur).

Neden ana arter: yardım ekipleri ve ambulanslar mahalleye ana yoldan girer; sokak düzeyi erişim, mahallenin bina ağırlıklı
merkezinden en yakın arter düğümüne "yerel erişim süresi" (kuş uçuşu × 1,4 dolambaç / 15 km/sa) olarak eklenir. 72 bin düğümlü
güçlü bağlı bileşen üzerinde 1.400 kaynaktan Dijkstra ~6 sn; her deprem gerçekleşmesi için yeniden hesaplanabilir.
Çıktı: data/processed/sim/ag.npz, sim/noktalar.parquet
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from sabitler import GIRIS
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

KOK = Path(__file__).resolve().parent.parent
P = KOK / "data/processed"
CIKTI = P / "sim"; CIKTI.mkdir(exist_ok=True)
OMURGA = ["motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link", "tertiary", "tertiary_link"]
YEREL_HIZ_MS = 15 / 3.6
DOLAMBAC = 1.4

k = gpd.read_parquet(P / "yol_kenar.parquet", columns=["u", "v", "sinif", "length", "travel_time", "acil_yol", "kritik_yapi",
                                                        "sanat_yapisi_id", "sanat_yapisi_tur", "bridge", "tunnel", "geometry"])
k = k[k.sinif.isin(OMURGA)].reset_index(drop=True)
dug = pd.unique(np.r_[k.u.values, k.v.values])
ix = pd.Series(np.arange(len(dug)), index=dug)
G = csr_matrix((np.ones(len(k)), (ix[k.u].values, ix[k.v].values)), shape=(len(dug),) * 2)
_, lab = connected_components(G, directed=True, connection="strong")
buyuk = lab == np.bincount(lab).argmax()
k = k[buyuk[ix[k.u].values] & buyuk[ix[k.v].values]].reset_index(drop=True)
dug = pd.unique(np.r_[k.u.values, k.v.values]); ix = pd.Series(np.arange(len(dug)), index=dug)
d = pd.read_parquet(P / "yol_dugum.parquet", columns=["osmid", "x", "y"]).set_index("osmid").loc[dug]
agac = cKDTree(np.c_[d.x.values * np.cos(np.radians(41)), d.y.values])


def bagla(lon, lat) -> tuple[np.ndarray, np.ndarray]:
    """En yakın arter düğümü ve yerel erişim süresi (sn)."""
    dist, i = agac.query(np.c_[np.asarray(lon) * np.cos(np.radians(41)), np.asarray(lat)])
    return i, dist * 111_320 * DOLAMBAC / YEREL_HIZ_MS


# kenar → mahalle (orta nokta) ve en yakın yer hareketi sahası (köprü kırılganlığı için)
mah = gpd.read_parquet(P / "mahalle.parquet", columns=["uavt", "geometry"])
orta = gpd.GeoDataFrame(geometry=k.to_crs(32635).geometry.interpolate(0.5, normalized=True), crs=32635).to_crs(4326)
j = gpd.sjoin_nearest(orta.to_crs(32635), mah.to_crs(32635), how="left", max_distance=2000)
k["uavt"] = j.groupby(level=0).uavt.first().reindex(k.index).fillna(-1).astype(int).values
saha = pd.read_parquet(P / "yer_hareketi/sahalar.parquet")
sy = saha[saha.tip == "sanat_yapisi"]
ys = cKDTree(np.c_[sy.lon.values * np.cos(np.radians(41)), sy.lat.values])
_, yi = ys.query(np.c_[orta.geometry.x * np.cos(np.radians(41)), orta.geometry.y])
k["gm_saha"] = np.where(k.kritik_yapi, sy.saha_id.values[yi], -1)
k["yapi_turu"] = np.select([k.tunnel.fillna("no").ne("no") | k.sanat_yapisi_tur.eq("Karayolu - Tünel"),
                            k.sanat_yapisi_tur.eq("Karayolu - Araç Alt Geçidi"), k.kritik_yapi], ["tunel", "alt_gecit", "kopru"], "yok")

# noktalar: mahalle, itfaiye, hastane, giriş
nok = []
m2 = pd.read_parquet(P / "mahalle.parquet", columns=["uavt", "lon_bina", "lat_bina", "yol_erisimi"])
i, t = bagla(m2.lon_bina, m2.lat_bina)
nok.append(pd.DataFrame(dict(tip="mahalle", kimlik=m2.uavt.astype(str), dugum=i, yerel_sn=np.where(m2.yol_erisimi == "deniz", np.nan, t))))
f = gpd.read_parquet(P / "itfaiye.parquet"); i, t = bagla(f.geometry.x, f.geometry.y)
nok.append(pd.DataFrame(dict(tip="itfaiye", kimlik=f.ad.values, dugum=i, yerel_sn=t, profesyonel=f.sar_ekip_kaynagi.values)))
h = gpd.read_parquet(P / "sim/hastane_sim.parquet"); i, t = bagla(h.geometry.x, h.geometry.y)
nok.append(pd.DataFrame(dict(tip="hastane", kimlik=h.index.astype(str), dugum=i, yerel_sn=t)))
i, t = bagla([v[0] for v in GIRIS.values()], [v[1] for v in GIRIS.values()])
nok.append(pd.DataFrame(dict(tip="giris", kimlik=list(GIRIS), dugum=i, yerel_sn=t)))
nok = pd.concat(nok, ignore_index=True)
nok["profesyonel"] = nok.profesyonel.fillna(False).astype(bool)
nok.to_parquet(CIKTI / "noktalar.parquet", index=False)

# mahalle başına tüm sürülebilir yol uzunluğu (km): enkaz yoğunluğunun paydası (yalnızca arter değil, sokaklar dahil)
tum = gpd.read_parquet(P / "yol_kenar.parquet", columns=["length", "geometry"])
to = gpd.GeoDataFrame(tum[["length"]], geometry=tum.to_crs(32635).geometry.interpolate(0.5, normalized=True), crs=32635)
tj = gpd.sjoin(to, mah.to_crs(32635), predicate="within")
yol_km = (tj.groupby("uavt")["length"].sum() / 2000).reindex(m2.uavt).fillna(0.5).clip(lower=0.5)  # yön çiftleri: /2

carpan = {"motorway": 0.2, "motorway_link": 0.2, "trunk": 0.2, "trunk_link": 0.2, "primary": 0.5, "primary_link": 0.5}
np.savez_compressed(CIKTI / "ag.npz", u=ix[k.u].values, v=ix[k.v].values, sure=k.travel_time.values.astype(np.float32),
                    uzunluk=k["length"].values.astype(np.float32), acil=k.acil_yol.values, uavt=k.uavt.values,
                    gm_saha=k.gm_saha.values, yapi_turu=k.yapi_turu.values, enkaz_carpani=k.sinif.map(carpan).fillna(1.0).values,
                    n_dugum=len(dug), dugum_x=d.x.values, dugum_y=d.y.values, mahalle_uavt=m2.uavt.values, mahalle_yol_km=yol_km.values.astype(np.float32))
print(f"ağ: {len(dug):,} düğüm, {len(k):,} kenar; köprü {int((k.yapi_turu == 'kopru').sum())}, alt geçit "
      f"{int((k.yapi_turu == 'alt_gecit').sum())}, tünel {int((k.yapi_turu == 'tunel').sum())}, acil {int(k.acil_yol.sum())}")
print(nok.groupby("tip").agg(n=("dugum", "size"), yerel_dk_medyan=("yerel_sn", lambda s: np.nanmedian(s) / 60)))
