"""Bir deprem gerçekleşmesinin simülasyon girdileri: mahalle kurban havuzları ve hastane kapasiteleri.

v3 (varsayılan): hasar modeli v3'ün (model/hs_09) senaryo × stok dosyası okunur; enkaz havuzu hazır gelir (olu_aninda, sikisan_canli),
çift sayım düzeltmesi hs_09'da yapılmıştır. v1: eski hs_02 çıktısı (aşağıdaki kural), karşılaştırma için korunur.

Çift sayım kuralı: hasar modelinin (hs_02) can kaybı ve yaralı sayıları çöken binalardaki kişileri de içerir. Çöken binaların
akıbetini simülatör zamanla üretir; bu yüzden çöken bina katkısı (KOERI Tablo 4.4.8 çöken sütunu: ölüm %10, ağır %10,
hastane %15, κ ile ölçekli) diğer kalemlerden düşülür.
Hastane binası: ağır+ hasar olasılığı kadar kapasite kaybı (kalibre B522 eğrisi, 5–8 kat 1980–2000 betonarme vekil);
adında "Şehir" geçenler sismik izolatörlü sayılır (Başakşehir Çam ve Sakura, Göztepe, Kartal şehir hastaneleri).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "model"))
from hasar_motoru import a_katsayi, hasar_olasilik, performans_sd, sa_periyot  # noqa: E402

P = KOK / "data/processed"
COKMUS_ORAN = {"can_kaybi": 0.10, "yarali_agir": 0.10, "yarali_hastane": 0.15}


class Senaryo:
    def __init__(self, senaryo: str = "temel", stok: str = "ist", surum: str = "v3"):
        self.surum = surum
        if surum == "v3":
            self.z = np.load(P / f"hasar/v3/{senaryo}_{stok}.npz")
            self.kal = pd.read_parquet(P / "hasar/kalibrasyon_v3.parquet")
        else:
            self.z = np.load(P / "hasar/simulasyon_girdi.npz")
            self.kal = pd.read_parquet(P / "hasar/kalibrasyon.parquet")
        m = pd.read_parquet(P / "mahalle.parquet", columns=["uavt", "ilce", "mahalle", "nufus_2025", "bina_toplam",
                                                            "sosyal_yardim_orani", "sosyal_gorebilirlik_ilce", "yol_erisimi"])
        assert (m.uavt.values == self.z["uavt"]).all()
        self.mah = m
        y = m.sosyal_yardim_orani.fillna(m.sosyal_yardim_orani.median()).values
        self.yoksunluk = (y - y.min()) / (y.max() - y.min())
        self.deniz = (m.yol_erisimi == "deniz").values
        h = pd.read_parquet(P / "sim/hastane_sim.parquet")  # ağ ve yer hareketi sahalarıyla aynı 377 kayıt; sahte kayıtlar yatak 0
        self.has = h
        self.has_izolatorlu = (h.tur.eq("Şehir Hastanesi") & h.ad.str.contains("Hastane", case=False)).values
        g = np.load(P / ("yer_hareketi/senaryo_alanlar.npz" if senaryo == "temel" else f"yer_hareketi/senaryo_alanlar_{senaryo}.npz"))
        s = pd.read_parquet(P / "yer_hareketi/sahalar.parquet")
        hs = s[s.tip == "hastane"]
        sira = pd.Series(np.arange(len(g["saha_id"])), index=g["saha_id"])[hs.saha_id].values
        imts = list(g["imts"]); sa = [i for i in imts if i != "PGA"]
        self.has_ln = g["ln_sa"][:, [imts.index(i) for i in sa], :][:, :, sira].transpose(0, 2, 1)  # (E, H, P)
        self.has_per = np.array([float(i[3:-1]) for i in sa])
        self.has_a = a_katsayi(hs.vs30.values)

    def gerceklesme(self, e: int) -> dict:
        z = self.z; r = self.kal.iloc[int(z["kal_secim"][e])]
        ck = z["cokmus_kisi"][e].astype(float)
        out = dict(e=e, cokmus_kisi=ck, cokmus_bina=z["cokmus_bina"][e].astype(float),
                   agir_ustu=(z["agir"][e] + z["cokagir"][e]).astype(float), cokagir=z["cokagir"][e].astype(float))
        if self.surum == "v3":
            out.update(kappa=1.0, olu_aninda=z["olu_aninda"][e].astype(float), sikisan_canli=z["sikisan_canli"][e].astype(float),
                       can_kaybi_diger=np.zeros_like(ck), yarali_agir_diger=z["yarali_agir"][e].astype(float),
                       yarali_hastane_diger=z["yarali_hastane"][e].astype(float))
        else:
            kappa = float(r.kappa); out["kappa"] = kappa
            for k, oran in COKMUS_ORAN.items():
                out[f"{k}_diger"] = np.maximum(z[k][e] - kappa * oran * ck, 0.0)
        # hastane işlevselliği
        sd = performans_sd(sa_periyot(self.has_ln[e], self.has_per, 0.75), "B522", self.has_a)
        p = hasar_olasilik(sd, "B522", float(r.s_beta), (r.theta_ho, r.theta_ho, r.theta_ac, r.theta_ac))
        islev = np.where(self.has_izolatorlu, 1.0, 1.0 - p[:, 3:].sum(1) - 0.5 * p[:, 2])
        out["has_islev"] = np.clip(islev, 0, 1)
        return out
