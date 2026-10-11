"""Harita maketinin kapanış bölümü: 959 mahallede medyan senaryoda yürüme mesafesinde yer bulamayan kişi sayısı, enlem-boylamlı.
i02 sonuçları mahalle sırasındadır; konum için binaların ağırlık merkezi (lon_bina, lat_bina) kullanılır, çünkü insanlar orada yaşar.
Çıktı: data/processed/web_tiles/istanbul_yersiz.json
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[1]
P = KOK / "data/processed"; T = P / "web_tiles"

def baslik(ad: str) -> str:
    """Türkçe büyük harf → başlık biçimi (str.title İ/I'yı bozar)."""
    k = ad.replace("I", "ı").replace("İ", "i").lower()
    return " ".join(w[:1].replace("i", "İ").replace("ı", "I").upper() + w[1:] for w in k.split())


if __name__ == "__main__":
    m = pd.read_parquet(P / "mahalle.parquet", columns=["uavt", "lon_bina", "lat_bina"])
    t = pd.read_parquet(P / "ihtiyac/toplanma_medyan.parquet").merge(m, on="uavt", validate="1:1")
    assert len(t) == 959 and t[["lon_bina", "lat_bina"]].notna().all().all()
    # ilçe etiketi: yer bulamayanların ağırlık merkezine konur, böylece etiket pembe yığının üstüne düşer
    t["w"] = t.yersiz.clip(lower=1)
    g = t.groupby("ilce").apply(lambda d: pd.Series(dict(
        lon=(d.lon_bina * d.w).sum() / d.w.sum(), lat=(d.lat_bina * d.w).sum() / d.w.sum(), yersiz=d.yersiz.sum(), talep=d.talep.sum())), include_groups=False)
    g = g.assign(oran=g.yersiz / g.talep).sort_values("yersiz", ascending=False).head(6)
    oz = json.loads((P / "ihtiyac/toplanma_ozet.json").read_text())
    veri = dict(
        mahalle=[[round(r.lon_bina, 5), round(r.lat_bina, 5), int(round(r.yersiz)), int(round(r.talep))] for r in t.itertuples()],
        ilce=[dict(ad=baslik(i), lonlat=[round(r.lon, 5), round(r.lat, 5)], yersiz=int(round(r.yersiz, -3)), oran=round(float(r.oran), 2))
              for i, r in g.iterrows()],
        ozet=oz["medyan"] if "medyan" in oz else oz,
    )
    (T / "istanbul_yersiz.json").write_text(json.dumps(veri, ensure_ascii=False, separators=(",", ":")))
    print(len(veri["mahalle"]), "mahalle;", int(t.yersiz.sum()), "yersiz /", int(t.talep.sum()), "dışarıda")
