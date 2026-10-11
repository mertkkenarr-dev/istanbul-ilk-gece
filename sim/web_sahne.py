"""Web için sahneler: D1'den temsilî gerçekleşmeler kayıt moduyla yeniden koşulur (data/processed/web_tiles/sahne_*.json).

Seçim: "fayda" politikasında toplam ölüm dağılımının medyanı ve %90'ı (ağır ama olası). Aynı tohum ve aynı fiziksel
parametrelerle koşulduğu için D1'deki sonucu birebir tekrar üretir (kontrol edilir).
"""
from __future__ import annotations

import json
import sys
from dataclasses import fields
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "sim"))
import geopandas as gpd  # noqa: E402
from kurulum import Dunya  # noqa: E402
from parametreler import Parametre  # noqa: E402
from sabitler import GIRIS  # noqa: E402

OUT = KOK / "data/processed/web_tiles"
d1 = pd.read_parquet(KOK / "data/processed/sim/analiz/d1.parquet")
f = d1[d1.politika == "fayda"].sort_values("olu_toplam").reset_index(drop=True)
SECIM = {"medyan": f.iloc[int(0.5 * (len(f) - 1))], "agir": f.iloc[int(0.9 * (len(f) - 1))]}
W = Dunya()
itg = gpd.read_parquet(KOK / "data/processed/itfaiye.parquet")
saha = pd.read_parquet(KOK / "data/processed/yer_hareketi/sahalar.parquet").set_index("saha_id")
cog = json.loads((OUT / "cografya.json").read_text())
cx, cy = cog["merkez_utm"]
from pyproj import Transformer  # noqa: E402

tr = Transformer.from_crs(4326, 32635, always_xy=True)
km = lambda lon, lat: [[round((x - cx) / 1000, 3), round((y - cy) / 1000, 3)] for x, y in zip(*tr.transform(lon, lat))]

for ad, row in SECIM.items():
    e = int(row.e)
    par = Parametre(**{fl.name: (int(row[fl.name]) if fl.type in ("int", int) else (str(row[fl.name]) if fl.name == "politika" else float(row[fl.name])))
                       for fl in fields(Parametre)})
    D = W.ag_durumu(e, par, tohum=10_000 + e)
    r = W.kos(D, par, tohum=e, kayit=True)
    assert abs(r["ozet"]["olu_toplam"] - row.olu_toplam) < 1e-6, (r["ozet"]["olu_toplam"], row.olu_toplam)
    s = r["saatlik"]; g = D["g"]
    aninda = r["mahalle"]["olu_aninda"]
    canli0 = r["mahalle"]["canli_sikisan"]
    canli = np.vstack([canli0[None], s["canli"]])
    olu = np.vstack([aninda[None], aninda[None] + s["olu_enkaz"] + s["olu_bekleme"]])
    kurt = np.vstack([np.zeros_like(canli0)[None], s["kurtarilan"]])
    q = lambda a: np.round(a * 10).astype(int).tolist()
    # üs sırası ag.py ile aynı: itfaiye birimleri, ardından 4 giriş noktası
    us_xy = km(np.r_[itg.geometry.x.values, [v[0] for v in GIRIS.values()]], np.r_[itg.geometry.y.values, [v[1] for v in GIRIS.values()]])
    assert len(us_xy) == len(W.ag.us)
    ks = saha.loc[D["ag"]["kapali_saha"]]
    h = r["hareket"]
    out = dict(e=e, etiket=ad, politika=par.politika, olcek=10.0, canli=q(canli), kurtarilan=q(kurt), olu=q(olu),
               hareket=[[int(a), round(b, 3), round(c, 3), int(t), int(k), int(m)] for a, b, c, t, k, m in h],
               us=us_xy, seri={k: [round(float(v), 1) for v in r["seri"][kk][3::4]] for k, kk in
                               (("canli", "enkaz_canli"), ("kurtarilan", "kurtarilan_pro"), ("olu_enkaz", "olu_enkaz"), ("olu_bekleme", "olu_bekleme"), ("sahada", "ekip_sahada"))},
               ozet={k: float(v) for k, v in r["ozet"].items()} | {"agir_ustu": float(g["agir_ustu"].sum()), "kopru_kapali": float(D["ag"]["kopru_kapali"])},
               kopru_kapali=km(ks.lon.values, ks.lat.values))
    (OUT / f"sahne_{ad}.json").write_text(json.dumps(out, separators=(",", ":")))
    print(f"{ad}: e={e} ölüm {row.olu_toplam:,.0f}, ekip hareketi {len(h)}, dosya {(OUT / f'sahne_{ad}.json').stat().st_size / 1e6:.2f} MB")
