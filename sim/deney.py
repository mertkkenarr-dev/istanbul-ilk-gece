"""Deneyler D1 (ana dağılım + politika karşılaştırması) ve D2 (duyarlılık / ML eğitim verisi).

Gerçekleşme seçimi: 1.000 olay toplam ağır+ hasara göre sıralanır, R tanesi sistematik örneklemeyle alınır (kuyruklar temsil
edilir, ağırlıklar eşit). Her gerçekleşme için fiziksel parametreler Latin hiperküpten çekilir; kollar D1'de varsayılan.
D1: 3 politika, ortak tohum (eşleştirilmiş karşılaştırma). D2: aynı yol matrisleriyle K örnek; ağ dışı tüm parametreler + politika
rastgele. Her gerçekleşmenin çıktısı ayrı dosyaya yazılır (sim/kosular/r####.npz); yarıda kalırsa kaldığı yerden devam eder.
Kullanım: python sim/deney.py [R] [K] [işçi]
"""
from __future__ import annotations

import multiprocessing as mp
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
OUT = KOK / "data/processed/sim/kosular"; OUT.mkdir(parents=True, exist_ok=True)
POLITIKA = ("yakin", "fayda", "esitlik")
MAH_ALAN = ("sikisan", "canli_sikisan", "olu_aninda", "kurtarilan_toplum", "kurtarilan_pro", "olu_enkaz", "olu_bekleme", "kalan_72", "ilk_varis_sa")
_W = None


def _dunya():
    global _W
    if _W is None:
        sys.path.insert(0, str(KOK / "sim"))
        from kurulum import Dunya
        _W = Dunya()
    return _W


def gorev(arg) -> str:
    e, par_fiz, d2 = arg
    hedef = OUT / f"r{e:04d}.npz"
    if hedef.exists():
        return f"r{e} var"
    from parametreler import Parametre, orneklem
    W = _dunya(); t0 = time.time()
    durum = W.ag_durumu(e, par_fiz, tohum=10_000 + e)
    ozet, mah, seri = [], {}, {}
    for pol in POLITIKA:
        r = W.kos(durum, replace(par_fiz, politika=pol), tohum=e)
        ozet.append(dict(deney="D1", e=e, **(par_fiz.sozluk() | {"politika": pol}), **r["ozet"]))
        mah[pol] = np.stack([r["mahalle"][k] for k in MAH_ALAN]).astype(np.float32)
        seri[pol] = np.stack(list(r["seri"].values())).astype(np.float32)
    rng = np.random.default_rng(20_000 + e)
    serbest = [a for a in Parametre.__dataclass_fields__ if a not in ("politika", "enkaz_a", "p_eski_kopru", "temizleme_sa")]
    for j, p in enumerate(orneklem(d2, rng, adlar=serbest)):
        p = replace(p, enkaz_a=par_fiz.enkaz_a, p_eski_kopru=par_fiz.p_eski_kopru, temizleme_sa=par_fiz.temizleme_sa,
                    politika=str(rng.choice(POLITIKA)))
        r = W.kos(durum, p, tohum=e * 1000 + j)
        ozet.append(dict(deney="D2", e=e, **p.sozluk(), **r["ozet"]))
    ag = {k: v for k, v in durum["ag"].items() if k != "mats"}
    g = durum["g"]
    for o in ozet:
        o.update({f"ag_{k}": v for k, v in ag.items()}, agir_ustu=float(g["agir_ustu"].sum()), cokmus_kisi=float(g["cokmus_kisi"].sum()),
                 has_islev_ort=float(np.average(g["has_islev"], weights=W.sen.has_yatak)), kappa=g["kappa"], s_ag=time.time() - t0)
    np.savez_compressed(hedef, ozet=pd.DataFrame(ozet).to_records(index=False), mahalle=np.stack([mah[p] for p in POLITIKA]),
                        seri=np.stack([seri[p] for p in POLITIKA]), alanlar=np.array(MAH_ALAN), politikalar=np.array(POLITIKA))
    return f"r{e} {time.time() - t0:.0f}s"


def main(R: int = 240, K: int = 25, isci: int = 7) -> None:
    sys.path.insert(0, str(KOK / "sim"))
    from parametreler import KOL, orneklem
    z = np.load(KOK / "data/processed/hasar/simulasyon_girdi.npz")
    tot = (z["agir"] + z["cokagir"]).sum(1)
    sira = np.argsort(tot)
    secilen = sira[((np.arange(R) + 0.5) * len(tot) / R).astype(int)]
    fiz = orneklem(R, np.random.default_rng(72), adlar=[a for a in __import__("parametreler").ARALIK if a not in KOL] + ["temizleme_sa"])
    is_listesi = [(int(e), p, K) for e, p in zip(secilen, fiz)]
    t0 = time.time()
    with mp.get_context("fork").Pool(isci) as havuz:
        for i, m in enumerate(havuz.imap_unordered(gorev, is_listesi), 1):
            if i % 10 == 0 or i == len(is_listesi):
                print(f"[{i}/{len(is_listesi)}] {m}  ({(time.time() - t0) / 60:.1f} dk)", flush=True)


if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]
    main(*a)
