"""OpenQuake ortamında: dört kalibrasyon depremi ve İstanbul senaryosu için sahada anlamlı sarsıntı süresi Ds5-95 (medyan).

Neden: KOERI kırılganlığı yalnızca spektral yerdeğiştirmeye bakar, süreyi görmez. Spektral olarak eşdeğer uzun ve kısa süreli kayıt
setlerinde betonarmenin medyan göçme kapasitesi uzun sürede %17–29 düşer (Chandramohan, Baker & Deierlein 2015/2016). Büyüklük
arttıkça süre uzar; bu etki kalibrasyona D = ln(Ds / 20 sn) değişkeniyle girer (hs_06).
Model: Afshari & Stewart (2016) RSD595. Çıktı: data/processed/yer_hareketi/sure_ds595.npz (olay → ln Ds dizisi, saha sırası olaylarınkiyle aynı)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from openquake.hazardlib import valid
from openquake.hazardlib.contexts import simple_cmaker
from openquake.hazardlib.geo import Point
from yh_ortak import CIKTI, KOK, iz_yonu, kirilma, sahalar

AS16 = valid.gsim("AfshariStewart2016")


def ln_ds(rup, lon, lat, vs30) -> np.ndarray:
    sc = sahalar(np.asarray(lon), np.asarray(lat), np.asarray(vs30))
    cm = simple_cmaker([AS16], ["RSD595"], mags=[f"{rup.mag:.2f}"], truncation_level=99.0)
    ctx = list(cm.get_ctxs([rup], sc))[0]
    mean = cm.get_mean_stds([ctx])[0]
    out = np.full(len(sc), np.nan); out[ctx.sids] = mean[0, 0]
    return out


def iz_2023(f: str) -> list[tuple[float, float]]:
    halka = json.loads((KOK / f"data/raw/external/usgs_2023/{f}_rupture.json").read_text())["features"][0]["geometry"]["coordinates"][0][0]
    ust = min(p[2] for p in halka)
    iz, gordu = [], False
    for p in halka:
        if p[2] == ust:
            iz.append((p[0], p[1])); gordu = True
        elif gordu:
            break
    return iz


if __name__ == "__main__":
    out = {}
    mah = pd.read_parquet(KOK / "data/processed/mahalle.parquet", columns=["uavt"]).uavt.values
    s = pd.read_parquet(CIKTI / "sahalar.parquet"); s = s[s.tip == "mahalle"].set_index(s[s.tip == "mahalle"].kaynak_id.astype(int)).loc[mah]
    iz13 = np.array(json.loads((KOK / "data/raw/external/gem_marmara_faults.geojson").read_text())["features"][1]["geometry"]["coordinates"])
    EPI = (28.1897, 40.8342, 12.7); az = iz_yonu(iz13, *EPI[:2])
    L, W = 10 ** (-2.57 + 0.62 * 6.2), 10 ** (-0.76 + 0.27 * 6.2)
    e = Point(*EPI[:2]); a, b = e.point_at(L / 2, 0, az + 180), e.point_at(L / 2, 0, az)
    r25 = kirilma([(a.longitude, a.latitude), (b.longitude, b.latitude)], 6.2, EPI[2] - W / 2, EPI[2] + W / 2, hipo=EPI)
    IZ99 = [(29.20, 40.70), (29.35, 40.72), (29.60, 40.72), (29.95, 40.73), (30.25, 40.70), (30.60, 40.68), (30.95, 40.73), (31.05, 40.75)]
    r99 = kirilma(IZ99, 7.4, 0.0, 18.0, hipo=(29.97, 40.76, 17.0))
    iz = json.loads((KOK / "data/raw/external/gem_marmara_faults.geojson").read_text())["features"][1]
    rsen = kirilma([tuple(c) for c in iz["geometry"]["coordinates"]], 7.5, 0.0, 15.0)
    out["silivri2025"] = ln_ds(r25, s.lon, s.lat, s.vs30)
    out["izmit1999"] = ln_ds(r99, s.lon, s.lat, s.vs30)
    out["senaryo"] = ln_ds(rsen, s.lon, s.lat, s.vs30)
    h = pd.read_parquet(KOK / "data/processed/hasar/bolge1999_hucre.parquet")
    out["bolge1999"] = ln_ds(r99, h.lon, h.lat, h.vs30)
    d = pd.read_parquet(KOK / "data/processed/sinama/maras2023_dugum.parquet")
    d1 = ln_ds(kirilma(iz_2023("jllz"), 7.8, 0.0, 20.0), d.lon, d.lat, d.vs30)
    d2 = ln_ds(kirilma(iz_2023("jlqa"), 7.5, 0.0, 20.0), d.lon, d.lat, d.vs30)
    out["maras2023"] = np.where(d.ln_pga.values >= -99, np.fmax(d1, d2), d1)   # iki ana şok: baskın olanın süresi (alt sınır; birikimli etki ayrıca yok)
    np.savez_compressed(CIKTI / "sure_ds595.npz", **out)
    for k, v in out.items():
        print(f"{k:12s} Ds5-95 medyan {np.exp(np.nanmedian(v)):5.1f} sn  (%10–90: {np.exp(np.nanpercentile(v, 10)):.1f}–{np.exp(np.nanpercentile(v, 90)):.1f})")
