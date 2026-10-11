"""Hasar v3 ile 72 saat: kırılma senaryosu × stok varsayımı başına R gerçekleşme (toplam göçmede kalan kişiye göre sistematik
örneklem), varsayılan parametreler, "fayda" politikası. Amaç: kalabalığın (enkaz başına kişi, hastane yükü) ölümü ne kadar
büyüttüğünü ve ölümlerin anında / enkaz altında / hastane beklerken dağılımını senaryolar arasında karşılaştırmak.
Kullanım: python sim/deney_v3.py [R] [işçi]   Çıktı: data/processed/sim/v3/{senaryo}_{stok}.parquet (+ mahalle .npz)
"""
from __future__ import annotations

import multiprocessing as mp
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
OUT = KOK / "data/processed/sim/v3"; OUT.mkdir(parents=True, exist_ok=True)
KOMBI = [("temel", "ist"), ("temel", "maras_gibi"), ("dogu", "ist"), ("dogu", "maras_gibi"), ("buyuk", "ist"), ("buyuk", "maras_gibi")]
MAH = ("sikisan", "canli_sikisan", "olu_aninda", "kurtarilan_toplum", "kurtarilan_pro", "olu_enkaz", "olu_bekleme", "ilk_varis_sa")
_W: dict = {}


def gorev(arg):
    sen, stok, e = arg
    sys.path.insert(0, str(KOK / "sim"))
    from kurulum import Dunya
    from parametreler import Parametre
    if (sen, stok) not in _W:
        _W.clear(); _W[(sen, stok)] = Dunya(sen, stok)
    W = _W[(sen, stok)]
    par = replace(Parametre(), politika="fayda")
    d = W.ag_durumu(e, par, tohum=10_000 + e)
    r = W.kos(d, par, tohum=e)
    o = dict(senaryo=sen, stok=stok, e=e, **r["ozet"], cokmus_kisi=float(d["g"]["cokmus_kisi"].sum()),
             yatak=float(W.sen.has_yatak.sum()))
    return o, np.stack([r["mahalle"][k] for k in MAH]).astype(np.float32)


if __name__ == "__main__":
    R = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    isci = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    for sen, stok in KOMBI:
        if (OUT / f"{sen}_{stok}.parquet").exists():
            continue
        z = np.load(KOK / f"data/processed/hasar/v3/{sen}_{stok}.npz")
        sira = np.argsort(z["cokmus_kisi"].sum(1))
        olaylar = sira[((np.arange(R) + 0.5) * len(sira) / R).astype(int)]
        with mp.get_context("spawn").Pool(isci) as havuz:
            sonuc = havuz.map(gorev, [(sen, stok, int(e)) for e in olaylar])
        df = pd.DataFrame([s[0] for s in sonuc])
        df.to_parquet(OUT / f"{sen}_{stok}.parquet", index=False)
        np.savez_compressed(OUT / f"{sen}_{stok}_mahalle.npz", e=df.e.values, alan=np.array(MAH), x=np.stack([s[1] for s in sonuc]))
        print(f"{sen}/{stok}: ölü ort {df.olu_toplam.mean():,.0f}, medyan {df.olu_toplam.median():,.0f}; "
              f"anında {df.olu_aninda.sum() / df.olu_toplam.sum():.0%}, enkaz {df.olu_enkaz.sum() / df.olu_toplam.sum():.0%}, "
              f"hastane bekleme {df.olu_bekleme.sum() / df.olu_toplam.sum():.0%}", flush=True)
