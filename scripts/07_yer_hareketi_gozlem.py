"""23 Nisan 2025 Silivri Mw 6,2 depreminin gerçek kayıtları: projedeki tek GÖZLEM verisi.

Girdi : data/raw/usgs_silivri_2025/{stationlist.json, grid.xml, info.json}
Çıktı : data/interim/silivri2025_istasyon.parquet (ivmeölçer), silivri2025_dyfi.parquet (hissedilme bildirimi),
        data/interim/mahalle_silivri2025.parquet (mahalle başına ShakeMap PGA/MMI)

Neden gerekli: İBB senaryosu bir model çıktısıdır. Yer hareketi modelimizi (GMPE + Vs30) doğrulamak için ölçülmüş ivme
lazım; 2025 depremi İstanbul ağında kaydedildi. Aynı formülü bu depreme uygulayıp istasyon kayıtlarıyla karşılaştırmak,
Mw 7,5 senaryosunda kullanacağımız yer hareketinin yanlılığını sayısal olarak verir.
"""
from __future__ import annotations

import json
import re

import geopandas as gpd
import numpy as np
import pandas as pd
from ortak import INTERIM, USGS, adim_temizle, log, qc
from scipy.interpolate import RegularGridInterpolator

ADIM = "07_yer_hareketi_gozlem"
adim_temizle(ADIM)
print(ADIM)

sl = json.loads((USGS / "stationlist.json").read_text())["features"]
rows, dyfi = [], []
for f in sl:
    p = f["properties"]; lon, lat = f["geometry"]["coordinates"][:2]
    d = p.get("distances") or {}
    if p.get("station_type") == "seismic":
        amp = {}
        for ch in p.get("channels", []):
            if ch["name"].endswith("Z"):
                continue  # ShakeMap genliği yatay bileşenlerin en büyüğüdür; düşey kanal karıştırılmaz
            for a in ch["amplitudes"]:
                if a.get("flag", "0") == "0" and a["value"] not in (None, "null"):
                    amp[a["name"]] = max(amp.get(a["name"], 0), float(a["value"]))
        pred = {q["name"]: q["value"] for q in p.get("predictions", [])}
        rows.append(dict(kod=p["code"], ag=p["network"], ad=p.get("name"), lon=lon, lat=lat, vs30_usgs=p.get("vs30"),
                         repi_km=d.get("repi"), rjb_km=d.get("rjb"), rrup_km=d.get("rrup"),
                         pga_g=amp.get("pga", np.nan) / 100, pgv_cms=amp.get("pgv", np.nan),
                         sa03_g=amp.get("sa(0.3)", np.nan) / 100, sa10_g=amp.get("sa(1.0)", np.nan) / 100,
                         mmi_kayit=p.get("intensity"), pga_usgs_tahmin_g=(pred.get("pga") or np.nan) / 100))
    elif p.get("network") == "DYFI" and p.get("intensity") not in (None, "null"):
        dyfi.append(dict(lon=lon, lat=lat, mmi=float(p["intensity"]), yanit=p.get("nresp"), repi_km=d.get("repi")))
ist = pd.DataFrame(rows); dy = pd.DataFrame(dyfi)
bos = ist.pga_g.isna()
log(ADIM, "Silivri 2025", "Bazı istasyonlarda yatay PGA yok ya da USGS tarafından işaretlenmiş (flag≠0)", int(bos.sum()),
    "Bu istasyonlar çıkarıldı", "İşaretli genlik (kırpılmış, gürültülü) doğrulamada yanlılık yaratır")
ist = ist[~bos]
log(ADIM, "Silivri 2025", "İstasyon listesinde 516 DYFI 'hissettim' bildirimi var (ölçüm değil, şiddet)", len(dy),
    "Ayrı tabloya ayrıldı (silivri2025_dyfi)", "Ölçülmüş ivme ile anket şiddeti aynı doğrulama setinde karıştırılmaz")
qc(ADIM, "İvmeölçer kaydı sayısı yeterli (≥40)", len(ist) >= 40, f"{len(ist)} istasyon, ağ: {ist.ag.value_counts().to_dict()}")
qc(ADIM, "PGA fiziksel aralıkta (0–2 g)", bool(ist.pga_g.between(0, 2).all()), f"maks {ist.pga_g.max():.3f} g @ {ist.loc[ist.pga_g.idxmax(), 'kod']}")
yakin = ist[ist.rjb_km < 60]
print(f"  60 km içi istasyon: {len(yakin)}, PGA medyan {yakin.pga_g.median():.3f} g")
gpd.GeoDataFrame(ist, geometry=gpd.points_from_xy(ist.lon, ist.lat), crs=4326).to_parquet(INTERIM / "silivri2025_istasyon.parquet", index=False)
gpd.GeoDataFrame(dy, geometry=gpd.points_from_xy(dy.lon, dy.lat), crs=4326).to_parquet(INTERIM / "silivri2025_dyfi.parquet", index=False)

# ---- ShakeMap ızgarası → mahalle ----
txt = (USGS / "grid.xml").read_text()
spec = dict(re.findall(r'(\w+)="([^"]+)"', re.search(r"<grid_specification([^>]*)/>", txt).group(1)))
alanlar = re.findall(r'<grid_field index="(\d+)" name="(\w+)"', txt)
veri = np.loadtxt(txt.split("<grid_data>")[1].split("</grid_data>")[0].strip().splitlines())
nlon, nlat = int(spec["nlon"]), int(spec["nlat"])
ad = {n: int(i) - 1 for i, n in alanlar}
lon = veri[:nlon, ad["LON"]]; lat = veri[::nlon, ad["LAT"]][::-1]
er = pd.read_parquet(INTERIM / "mahalle_erisim_dugumu.parquet")[["uavt", "lon_bina", "lat_bina"]]
out = er[["uavt"]].copy()
for alan, birim in (("PGA", 100), ("PGV", 1), ("MMI", 1), ("PSA03", 100), ("PSA10", 100)):
    z = veri[:, ad[alan]].reshape(nlat, nlon)[::-1]
    f = RegularGridInterpolator((lat, lon), z)
    out[f"silivri2025_{alan.lower()}"] = (f(np.c_[er.lat_bina, er.lon_bina]) / birim).round(4)
out = out.rename(columns={"silivri2025_pga": "silivri2025_pga_g", "silivri2025_psa03": "silivri2025_sa03_g", "silivri2025_psa10": "silivri2025_sa10_g"})
qc(ADIM, "Tüm mahalleler ShakeMap ızgarasının içinde", out.silivri2025_pga_g.notna().all(),
   f"İstanbul'da PGA {out.silivri2025_pga_g.min():.3f}–{out.silivri2025_pga_g.max():.3f} g, MMI {out.silivri2025_mmi.min():.1f}–{out.silivri2025_mmi.max():.1f}")
log(ADIM, "Silivri 2025", "ShakeMap ızgarası istasyon kayıtlarıyla koşullanmış bir enterpolasyondur (yine model + gözlem karışımı)", len(out),
    "Mahalle değerleri 'ShakeMap tahmini' olarak etiketlendi; doğrulamada yalnızca istasyon kayıtları gözlem sayılır",
    "Izgarayı gözlem sayıp modelimizi ona göre ayarlamak döngüsel olur")
out.to_parquet(INTERIM / "mahalle_silivri2025.parquet", index=False)
