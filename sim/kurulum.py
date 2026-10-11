"""Simülasyon nesnelerini bir kez kurar (ağ, senaryo, üs/hastane eşleşmeleri) ve tek bir koşuyu çalıştıran yardımcı."""
from __future__ import annotations

import numpy as np
from ag_hasar import Ag
from girdi import Senaryo
from motor import calistir
from parametreler import Parametre


class Dunya:
    def __init__(self, senaryo: str = "temel", stok: str = "ist", surum: str = "v3"):
        self.ag = Ag(senaryo)
        self.sen = Senaryo(senaryo, stok, surum)
        us = self.ag.us
        self.sen.us_pro = np.where((us.tip == "itfaiye") & us.profesyonel)[0]
        self.sen.us_giris = np.where(us.tip == "giris")[0]  # sıra: İstanbul Hv., Sabiha Gökçen, doğu kapısı, batı kapısı
        assert len(self.sen.us_giris) == 4
        self.sen.has_yatak = self.sen.has.yatak_tahmini.values.astype(float)
        assert len(self.ag.has) == len(self.sen.has_yatak)

    def ag_durumu(self, e: int, par: Parametre, tohum: int, ek=None) -> dict:
        g = self.sen.gerceklesme(e)
        d = self.ag.durum(e, g["agir_ustu"], par, np.random.default_rng(tohum), ek)
        return dict(g=g, ag=d)

    def kos(self, durum: dict, par: Parametre, tohum: int, plan: np.ndarray | None = None, ek_hastane: dict | None = None,
            kayit: bool = False) -> dict:
        return calistir(durum["g"], durum["ag"]["mats"], self.sen, par, np.random.default_rng(tohum), plan, ek_hastane, kayit)

    def lp_plan(self, durum: dict, par: Parametre, z: float = 0.0, agirlik: np.ndarray | None = None) -> dict:
        from optimizasyon import plan_coz, ulasilabilirlik
        g = durum["g"]
        H = par.p_sikisma * g["cokmus_kisi"] * (1 - par.p_aninda) * (1 - par.p_hafif_sikisma)
        ul = ulasilabilirlik(durum["ag"]["mats"], np.r_[self.sen.us_pro, self.sen.us_giris])
        return plan_coz(H, np.maximum(np.ceil(g["cokmus_bina"]), 1), ul, par, z, agirlik)
