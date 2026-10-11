"""Web için ihtiyaç/hikaye verileri (data/processed/web_tiles; yayına w07 taşır): toplanma.json, hikaye.json, yaris.json, sinama.json.

Koordinatlar cografya.json ile aynı yerel düzlemde (UTM 35N, km, merkez çıkarılmış); mahalle sırası mahalle.parquet = cografya.
Hikaye sayıları burada tek yerde hesaplanır; site metni yalnızca bu dosyadan okur (sayı-metin tutarlılığı).
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

KOK = Path(__file__).resolve().parents[1]
P = KOK / "data/processed"; C = P / "ihtiyac"; OUT = P / "web_tiles"
CRS = 32635
TURGUT = 181502
cx, cy = json.loads((OUT / "cografya.json").read_text())["merkez_utm"]
yerel = lambda x, y: [round((x - cx) / 1000, 3), round((y - cy) / 1000, 3)]
yaz = lambda ad, v: (OUT / ad).write_text(json.dumps(v, ensure_ascii=False, separators=(",", ":")))
m = pd.read_parquet(P / "mahalle.parquet")
ti = int(np.where(m.uavt == TURGUT)[0][0])
es = m.ilce.str.contains("ESENYURT", case=False).values

# ---------------- toplanma ----------------
tp = {d: pd.read_parquet(C / f"toplanma_{d}.parquet").set_index("uavt").reindex(m.uavt) for d in ("medyan", "herkes", "p90", "medyan_1500m", "medyan_2m2", "korku_yarim")}
oz = json.loads((C / "toplanma_ozet.json").read_text())
from i02_toplanma_atama import PAY, alanlar  # noqa: E402

a = gpd.GeoDataFrame(alanlar(1.5), geometry=gpd.points_from_xy(alanlar(1.5).lon, alanlar(1.5).lat), crs=4326).to_crs(CRS)
il = tp["medyan"].groupby(m.set_index("uavt").ilce).agg(talep=("talep", "sum"), yersiz=("yersiz", "sum"))
il = il.assign(oran=il.yersiz / il.talep).sort_values("yersiz", ascending=False)
yaz("toplanma.json", dict(
    talep=tp["medyan"].talep.round().astype(int).tolist(), yersiz=tp["medyan"].yersiz.round().astype(int).tolist(),
    talep_herkes=tp["herkes"].talep.round().astype(int).tolist(), yersiz_herkes=tp["herkes"].yersiz.round().astype(int).tolist(),
    alan=[[*yerel(p.x, p.y), int(k)] for p, k in zip(a.geometry, a.kapasite)],
    pga=np.round(np.median(np.load(C / "disarida_temel_ist.npz")["pga"], 0), 3).tolist(), alan_km2=m.alan_km2.round(3).tolist(),
    ozet={d: {k: round(v) if isinstance(v, float) and v > 1 else v for k, v in oz[d].items() if k != "en_kotu_ilce"} for d in oz},
    ilce=[dict(ad=i, talep=int(r.talep), yersiz=int(r.yersiz), oran=round(float(r.oran), 3)) for i, r in il.head(15).iterrows()],
    varsayim=dict(m2_kisi=1.5, yurume_m=1000, dolambac=1.3, kullanilabilir=PAY)))

# ---------------- hikaye (Turgut Özal) ----------------
r = m.iloc[ti]
dis = np.load(C / "disarida_temel_ist.npz"); disb = np.load(C / "disarida_buyuk_ist.npz")
ds = np.load(P / "yer_hareketi/sure_ds595.npz")
s25 = pd.read_parquet(P.parent / "interim/mahalle_silivri2025.parquet").set_index("uavt").loc[TURGUT]
sinir = gpd.read_parquet(P.parent / "interim/mahalle_sinir.parquet").merge(m[["uavt", "ilce"]], on="uavt").to_crs(CRS)
poly = sinir[sinir.uavt == TURGUT].geometry.iloc[0]
es_poly = sinir[sinir.ilce.str.contains("ESENYURT", case=False)].union_all()
k = gpd.read_parquet(P / "yol_kenar.parquet").to_crs(CRS)
cik = k[k.crosses(es_poly.boundary) & k.sinif.isin(["motorway", "trunk", "primary", "secondary"])]
cik = cik[[es_poly.contains(Point(g.coords[0])) for g in cik.geometry]]
SERIT = {"motorway": 3, "trunk": 3, "primary": 2, "secondary": 2}; KAP = {"motorway": 1800, "trunk": 1500, "primary": 900, "secondary": 800}
serit = cik.lanes.map(lambda x: pd.to_numeric(str(x).split("|")[0], errors="coerce")).fillna(cik.sinif.map(SERIT))
cik_kap = float((serit * cik.sinif.map(KAP)).sum())
cik_yol = sorted({n for n in cik.name.dropna().astype(str).str.split("|").str[0]})
ic = k[k.intersects(poly)].copy(); ic["cift"] = [tuple(sorted(x)) for x in zip(ic.u, ic.v)]
ic = ic.drop_duplicates("cift").clip(poly); ic["L"] = ic.length
YAYA = {"residential": 4, "unclassified": 4, "tertiary": 8, "primary": 14, "primary_link": 6}
yaya_m2 = float(sum(ic[ic.sinif == s].L.sum() * w for s, w in YAYA.items()))
h = gpd.read_parquet(P / "hastane.parquet").to_crs(CRS).merge(m[["uavt", "ilce"]], on="uavt", how="left")
tpnt = gpd.GeoSeries(gpd.points_from_xy([r.lon_bina], [r.lat_bina]), crs=4326).to_crs(CRS).iloc[0]
h["km"] = h.distance(tpnt) / 1000
yakin = h[(h.km < 11) & (h.yatak_tahmini >= 100)].sort_values("km")
es_h = h[h.uavt.isin(m[es].uavt)]
oto_1000 = 3_793_152 / m.nufus_2025.sum() * 1000
barinma = float(r.barinma_kisi)
yaz("hikaye.json", dict(
    turgut=dict(i=ti, ad="Turgut Özal", nufus=int(r.nufus_2025), alan_km2=round(float(r.alan_km2), 2), yogunluk=round(float(r.nufus_2025 / r.alan_km2)),
                yogunluk_medyan=round(float(m.nufus_yogunlugu_km2.median())), bina=int(r.bina_toplam), kisi_bina=round(float(r.nufus_2025 / r.bina_toplam), 1),
                kisi_bina_medyan=round(float((m.nufus_2025 / m.bina_toplam.replace(0, np.nan)).median()), 1),
                yas=[int(r.bina_1980_oncesi), int(r.bina_1980_2000), int(r.bina_2000_sonrasi)], kat=[int(r.kat_1_4), int(r.kat_5_9), int(r.kat_9_19)],
                toplanma_m2=int(r.toplanma_alani_m2), sigan=int(r.toplanma_alani_m2 / 1.5), c=yerel(tpnt.x, tpnt.y)),
    s2025=dict(pga=round(float(s25.silivri2025_pga_g), 2), mmi=round(float(s25.silivri2025_mmi), 1), ds=round(float(np.exp(ds["silivri2025"][ti]))),
               incelenen=8367, agir=1, yol_dk=(15, 90), gsm_dk=(15, 60)),
    senaryo=dict(pga=round(float(np.median(dis["pga"][:, ti])), 2), pga_p10=round(float(np.percentile(dis["pga"][:, ti], 10)), 2),
                 pga_p90=round(float(np.percentile(dis["pga"][:, ti], 90)), 2), ds=round(float(np.exp(ds["senaryo"][ti]))),
                 pga_buyuk=round(float(np.median(disb["pga"][:, ti])), 2)),
    sokak=dict(disarida=[int(np.median(dis["ilk_gece"][:, ti])), int(tp["medyan"].talep.iloc[ti])], yaya_m2=round(yaya_m2), yogunluk=round(r.nufus_2025 / yaya_m2, 2)),
    toplanma=dict(talep=int(tp["medyan"].talep.iloc[ti]), yersiz=int(tp["medyan"].yersiz.iloc[ti]), oran_1500=round(float(tp["medyan_1500m"].yersiz.iloc[ti] / tp["medyan_1500m"].talep.iloc[ti]), 2),
                  oran_yarim=round(float(tp["korku_yarim"].yersiz.iloc[ti] / tp["korku_yarim"].talep.iloc[ti]), 2),
                  esenyurt=[int(tp["medyan"].talep[es].sum()), int(tp["medyan"].yersiz[es].sum())],
                  esenyurt_herkes=[int(tp["herkes"].talep[es].sum()), int(tp["herkes"].yersiz[es].sum())]),
    haberlesme=dict(baz_toplam=8900, baz_kapali=2451, aku_sa=(2, 8), jenerator=3485),
    arac=dict(oto_1000=round(oto_1000), turgut=[round(r.nufus_2025 * 0.15, -2), round(r.nufus_2025 * oto_1000 / 1000, -2)],
              esenyurt=[round(m[es].nufus_2025.sum() * 0.15, -3), round(m[es].nufus_2025.sum() * oto_1000 / 1000, -3)], cikis_kap=round(cik_kap, -3),
              cikis_yol=cik_yol, cikis_xy=[yerel(*g.coords[0]) for g in cik.geometry]),
    hastane=dict(esenyurt_sayi=int(len(es_h)), esenyurt_yatak=int(es_h.yatak_tahmini.sum()),
                 bin_kisi=round(1000 * float(es_h.yatak_tahmini.sum()) / float(m[es].nufus_2025.sum()), 2),
                 istanbul_bin_kisi=round(1000 * float(h.yatak_tahmini.sum()) / float(m.nufus_2025.sum()), 2),
                 yakin=[dict(ad=x.ad, ilce=str(x.ilce).title(), km=round(float(x.km), 1), yatak=int(x.yatak_tahmini), xy=yerel(x.geometry.x, x.geometry.y)) for x in yakin.itertuples()]),
    barinma=dict(kisi=int(barinma), pay=round(barinma / float(r.nufus_2025), 2), kamp_m2=int(barinma * 45), mahalle_m2=int(r.alan_km2 * 1e6),
                 su_ton=round(barinma * 15 / 1000), tuvalet=int(barinma / 50)),
    esenyurt=dict(nufus=int(m[es].nufus_2025.sum()), i=np.where(es)[0].tolist())))

# ---------------- dönüşüm yarışı ----------------
rh = pd.read_excel(KOK / "data/raw/ibb/yapi_ruhsat_bina.xls")
rh = rh[pd.to_numeric(rh["Yıl"], errors="coerce").notna()].astype({"Yıl": int})
eski = int((m.bina_1980_oncesi + m.bina_1980_2000).sum())
hiz = {f"{a}-{b}": round(float(rh[(rh["Yıl"] >= a) & (rh["Yıl"] <= b)].Binalar.mean())) for a, b in ((2010, 2024), (2018, 2024), (2021, 2024))}
yaz("yaris.json", dict(ruhsat=[dict(yil=int(y), bina=int(b)) for y, b in zip(rh["Yıl"], rh.Binalar)], eski=eski, eski_1980=int(m.bina_1980_oncesi.sum()),
                       toplam=int(m.bina_toplam.sum()), hiz=hiz, yil={k: round(eski / v) for k, v in hiz.items()},
                       olasilik=[dict(kaynak="Parsons (2004)", aralik="%35–70", not_="30 yıl, M≥7"), dict(kaynak="Murru vd. (2016)", aralik="%35–70", not_="30 yıl, M≥7")]))

# ---------------- 6 Şubat sınavı ----------------
s02 = json.loads((P / "sinama/maras2023_sonuc.json").read_text())
v3 = json.loads((P / "hasar/kalibrasyon_v3.json").read_text())
yaz("sinama.json", dict(gozlem=53537, modeller=[
    dict(ad="İBB'nin yöntemi (KOERI eğrileri)", olu=round(s02["temel/koeri"]["olu_ort"], -2)),
    dict(ad="USGS PAGER, Türkiye'ye kalibre", olu=21300),
    dict(ad="Bu proje, İstanbul depremlerine kalibre (v1)", olu=round(s02["temel/posterior"]["olu_ort"], -2)),
    dict(ad="Bu proje, 6 Şubat dahil kalibre (v3)", olu=round(v3["tahmin_vs_gozlem"]["m23"][0], -2))],
    v3_ist1999=[round(v3["tahmin_vs_gozlem"]["i99"][0]), 454]))
print("toplanma.json, hikaye.json, yaris.json, sinama.json yazıldı")
print(json.dumps(json.loads((OUT / "hikaye.json").read_text())["arac"] | {"cikis_xy": "…"}, ensure_ascii=False))
