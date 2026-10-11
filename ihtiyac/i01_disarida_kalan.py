"""İhtiyaç analizi, adım 1: her deprem gerçekleşmesinde kaç kişi ilk gece dışarıda, kaç kişi uzun süre evsiz?

Ölüm sayısından farklı olarak bu büyüklükler hasarın kaba ölçeğine bağlıdır (göçme eğrisinin ucuna ve ölümcüllüğe değil), bu
yüzden kalibrasyon belirsizliğine çok daha az duyarlıdır.
  uzun_sureli  evine dönemeyen: ağır/çok ağır hasarlı binada yaşayan + orta hasarlıda yaşayanların yarısı (tespit ve onarım bekler).
               İBB'nin barınma tahmini (hane) ile karşılaştırılır.
  ilk_gece     uzun_sureli + kalan nüfusun q(PGA) kadarı (korku, artçı, elektrik/su yok). q: 0,05 g'de %10 → 0,30 g'de %80, doğrusal
               (VARSAYIM; 2025 Silivri'de ~0,05–0,1 g altında bile parklar ve araçlar doldu, 6 Şubat'ta hasarsız binalara haftalarca
               girilmedi). Duyarlılık: q × 0,5 ve q × 1,25.
Çıktı: data/processed/ihtiyac/disarida_{senaryo}_{stok}.npz  (E × mahalle)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[1]
P = KOK / "data/processed"
CIKTI = P / "ihtiyac"; CIKTI.mkdir(exist_ok=True)
KOMBI = [("temel", "ist"), ("temel", "maras_gibi"), ("dogu", "ist"), ("buyuk", "ist"), ("buyuk", "maras_gibi")]


def korku(pga: np.ndarray, olcek: float = 1.0) -> np.ndarray:
    return np.clip((0.10 + 0.70 * (pga - 0.05) / 0.25) * olcek, 0.10 * olcek, 1.0)


def pga_mahalle(senaryo: str) -> np.ndarray:
    m = pd.read_parquet(P / "mahalle.parquet", columns=["uavt"])
    s = pd.read_parquet(P / "yer_hareketi/sahalar.parquet")
    ms = s[s.tip == "mahalle"].set_index(s[s.tip == "mahalle"].kaynak_id.astype(int)).reindex(m.uavt)
    z = np.load(P / ("yer_hareketi/senaryo_alanlar.npz" if senaryo == "temel" else f"yer_hareketi/senaryo_alanlar_{senaryo}.npz"))
    sira = pd.Series(np.arange(len(z["saha_id"])), index=z["saha_id"])[ms.saha_id].values
    return np.exp(z["ln_sa"][:, 0, sira])


if __name__ == "__main__":
    m = pd.read_parquet(P / "mahalle.parquet", columns=["uavt", "ilce", "nufus_2025", "barinma_kisi"])
    nuf = m.nufus_2025.values.astype(float)
    satir = []
    for sen, stok in KOMBI:
        k = np.load(P / f"hasar/v3/{sen}_{stok}_kisi.npz")
        pga = pga_mahalle(sen)
        uzun = np.minimum(k["agir_ustu_kisi"] + 0.5 * k["orta_kisi"], nuf)
        kalan = nuf - uzun
        ilk = {o: uzun + korku(pga, o) * kalan for o in (0.5, 1.0, 1.25)}
        np.savez_compressed(CIKTI / f"disarida_{sen}_{stok}.npz", uavt=m.uavt.values, uzun_sureli=uzun.astype(np.float32),
                            ilk_gece=ilk[1.0].astype(np.float32), ilk_gece_dusuk=ilk[0.5].astype(np.float32),
                            ilk_gece_yuksek=ilk[1.25].astype(np.float32), pga=pga.astype(np.float32))
        U, I = uzun.sum(1), ilk[1.0].sum(1)
        satir.append(dict(senaryo=sen, stok=stok, uzun_p50=np.median(U), uzun_p90=np.percentile(U, 90),
                          ilk_p50=np.median(I), ilk_p90=np.percentile(I, 90), ilk_dusuk_p50=np.median(ilk[0.5].sum(1)),
                          ilk_yuksek_p50=np.median(ilk[1.25].sum(1))))
    d = pd.DataFrame(satir)
    d.to_parquet(CIKTI / "disarida_ozet.parquet", index=False)
    pd.set_option("display.width", 200)
    print((d.set_index(["senaryo", "stok"]) / 1e6).round(2).to_string())
    print(f"İBB barınma tahmini (kişi): {m.barinma_kisi.sum() / 1e6:.2f} M; nüfus {nuf.sum() / 1e6:.2f} M")
