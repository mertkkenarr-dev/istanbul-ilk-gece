"""Bir deprem gerçekleşmesi için hasarlı yol ağı ve zamana bağlı seyahat süresi matrisleri.

Köprü/alt geçit/tünel: HAZUS-MH köprü kırılganlığı, Sa(1,0 s) (g), β = 0,6. HWB5 (çok açıklıklı basit mesnetli, eski tasarım)
0,25/0,35/0,45/0,70; HWB10 (sürekli betonarme) 0,60/0,90/1,10/1,50. Alt geçitler HWB10 sayılır. Tüneller PGA tabanlı, geçilmez
medyanı 0,8 g. Ağır+ hasarlı yapı 72 saat boyunca kapalı; orta hasarda hız yarıya iner.
Enkaz: mahalle i'deki arter kenarı p = 1 − exp(−a · c · yoğunluk_i) ile etkilenir; yoğunluk = ağır+ bina / mahalle yol km,
c yol sınıfı çarpanı (otoyol/trunk 0,2, primary 0,5). Etkilenen kenarın %25'i tamamen kapanır, kalanında bir şerit açık kalır
ve hız 1/4'e düşer (arterler nadiren tümüyle tıkanır). Açılma süresi üstel; İBB 1. derece acil yollarında ortalama 1/3.
Son kilometre: araçla ulaşılamayan mahalleye 3 km içindeki ulaşılabilir komşu mahalleden yürüyerek (4 km/sa, ×1,3 dolambaç)
erişilir; ekipler ve taşınan yaralılar için aynı kural (2023 Hatay'da ekipler son kısmı yaya tamamladı).
Dönemler: 0, 6, 12, 24, 48 sa. Her dönemde o ana kadar açılan kenarlar ağa geri döner.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.special import ndtr

KOK = Path(__file__).resolve().parent.parent
P = KOK / "data/processed"
DONEM = np.array([0.0, 6.0, 12.0, 24.0, 48.0])
HWB5 = np.array([0.25, 0.35, 0.45, 0.70]); HWB10 = np.array([0.60, 0.90, 1.10, 1.50])
TAM_KAPANMA, ENKAZ_YAVAS = 0.25, 4.0
YURUME_MS, YURUME_YARICAP_M = 4 / 3.6 / 1.3, 3000


class Ag:
    """Statik ağ + yer hareketi alanları; gerçekleşmeye özgü durum `durum()` ile üretilir."""

    def __init__(self, senaryo: str = "temel"):
        z = np.load(P / "sim/ag.npz", allow_pickle=True)
        self.u, self.v, self.sure = z["u"], z["v"], z["sure"].astype(float)
        self.acil, self.uavt, self.gm_saha, self.tur = z["acil"], z["uavt"], z["gm_saha"], z["yapi_turu"]
        self.enkaz_c, self.n = z["enkaz_carpani"], int(z["n_dugum"])
        self.mah_uavt, self.yol_km = z["mahalle_uavt"], z["mahalle_yol_km"]
        self.dx, self.dy = z["dugum_x"], z["dugum_y"]
        nok = pd.read_parquet(P / "sim/noktalar.parquet")
        self.nok = nok
        self.mah = nok[nok.tip == "mahalle"].reset_index(drop=True)
        self.us = nok[nok.tip.isin(["itfaiye", "giris"])].reset_index(drop=True)
        self.has = nok[nok.tip == "hastane"].reset_index(drop=True)
        g = np.load(P / ("yer_hareketi/senaryo_alanlar.npz" if senaryo == "temel" else f"yer_hareketi/senaryo_alanlar_{senaryo}.npz"))
        imts = list(g["imts"]); self.saha_sira = pd.Series(np.arange(len(g["saha_id"])), index=g["saha_id"])
        self.ln_sa10 = 0.5 * (g["ln_sa"][:, imts.index("SA(0.9)")] + g["ln_sa"][:, imts.index("SA(1.2)")])  # log-orta ≈ Sa(1,0)
        self.ln_pga = g["ln_sa"][:, imts.index("PGA")]
        self.mah_ix = pd.Series(np.arange(len(self.mah_uavt)), index=self.mah_uavt)
        self.kenar_mah = np.where(self.uavt >= 0, self.mah_ix.reindex(self.uavt).fillna(-1).values, -1).astype(int)
        kaynak = np.unique(np.r_[self.mah.dugum, self.us.dugum, self.has.dugum])
        self.kaynak, self.k_ix = kaynak, pd.Series(np.arange(len(kaynak)), index=kaynak)
        mm = pd.read_parquet(P / "mahalle.parquet", columns=["lon_bina", "lat_bina"])
        x = mm.lon_bina.values * 111_320 * np.cos(np.radians(41)); y = mm.lat_bina.values * 111_320
        dist = np.hypot(x[:, None] - x[None, :], y[:, None] - y[None, :])
        self.komsu = [np.where((dist[j] < YURUME_YARICAP_M) & (np.arange(len(x)) != j))[0] for j in range(len(x))]
        self.yurume = [dist[j, k] / YURUME_MS for j, k in enumerate(self.komsu)]

    def durum(self, e: int, agir_ustu_mah: np.ndarray, par, rng: np.random.Generator, ek: pd.DataFrame | None = None) -> dict:
        """agir_ustu_mah: mahalle sırasıyla ağır+ hasarlı bina (gerçekleşme e). ek: isteğe bağlı ek hedef tesisler
        (dugum, yerel_sn; ör. sahra hastanesi adayları) – mahalleden bu tesislere süreler 'mah_ek' olarak döner."""
        # hasar durumu yapı başına bir kez örneklenir: aynı köprünün birden çok kenarı aynı kaderi paylaşır
        yap = self.gm_saha >= 0
        yapi, ters = np.unique(self.gm_saha[yap], return_inverse=True)
        si = self.saha_sira.reindex(yapi).values
        sa = np.exp(self.ln_sa10[e, si]); pga = np.exp(self.ln_pga[e, si])
        tur = pd.Series(self.tur[yap]).groupby(ters).first().values
        eski = rng.random(len(yapi)) < par.p_eski_kopru
        med = np.where((tur == "kopru")[:, None] & eski[:, None], HWB5, HWB10)
        asim = ndtr(np.log(sa[:, None] / med) / 0.6)  # (yapı, 4) P(DS ≥ k)
        tun = tur == "tunel"
        asim[tun] = ndtr(np.log(pga[tun] / 0.8) / 0.6)[:, None] * np.array([1, 1, 1, 0.5])
        ds_yapi = (rng.random(len(yapi))[:, None] < asim).sum(1)  # 0 yok … 4 çok ağır
        ds = ds_yapi[ters]
        kapali = np.zeros(len(self.u), bool); yavas = np.ones(len(self.u))
        kapali[np.where(yap)[0][ds >= 3]] = True
        yavas[np.where(yap)[0][ds == 2]] = 2.0
        # enkaz
        yog = np.zeros(len(self.u))
        m = self.kenar_mah >= 0
        yog[m] = agir_ustu_mah[self.kenar_mah[m]] / self.yol_km[self.kenar_mah[m]]
        p_kapan = 1 - np.exp(-par.enkaz_a * self.enkaz_c * yog)
        enkaz = (rng.random(len(self.u)) < p_kapan) & ~kapali
        tam = enkaz & (rng.random(len(self.u)) < TAM_KAPANMA)
        acilma = np.where(enkaz, rng.exponential(np.where(self.acil, par.temizleme_sa / 3, par.temizleme_sa)), 0.0)
        mats = []
        for t in DONEM:
            gecer = ~kapali & ~(tam & (acilma > t))
            carp = yavas * np.where(enkaz & ~tam & (acilma > t), ENKAZ_YAVAS, 1.0)
            G = csr_matrix((self.sure[gecer] * carp[gecer], (self.u[gecer], self.v[gecer])), shape=(self.n, self.n))
            D = np.full((len(self.kaynak), self.n), np.inf, np.float32)
            for b in range(0, len(self.kaynak), 300):
                D[b:b + 300] = dijkstra(G, indices=self.kaynak[b:b + 300], limit=6 * 3600)
            mats.append(self._matrisler(D, ek))
        return dict(mats=mats, kapali_saha=yapi[ds_yapi >= 3].tolist(), kopru_kapali=int((ds_yapi >= 3).sum()), kopru_hasarli=int((ds_yapi >= 2).sum()), yapi_sayisi=len(yapi),
                    enkaz_kenar=int(enkaz.sum()), enkaz_tam_kapali=int(tam.sum()), enkaz_acil=int((enkaz & self.acil).sum()))

    def bagla(self, lon, lat) -> tuple[np.ndarray, np.ndarray]:
        """Herhangi bir noktayı en yakın arter düğümüne bağlar (ag.py ile aynı yerel erişim kuralı)."""
        from scipy.spatial import cKDTree
        c = np.cos(np.radians(41))
        dist, i = cKDTree(np.c_[self.dx * c, self.dy]).query(np.c_[np.asarray(lon) * c, np.asarray(lat)])
        return i, dist * 111_320 * 1.4 / (15 / 3.6)

    def _matrisler(self, D: np.ndarray, ek: pd.DataFrame | None = None) -> dict:
        def blok(kay: pd.DataFrame, hed: pd.DataFrame) -> np.ndarray:
            M = D[self.k_ix[kay.dugum].values][:, hed.dugum.values]
            M = M + kay.yerel_sn.values[:, None].astype(np.float32) + hed.yerel_sn.values[None, :].astype(np.float32)
            return np.where(np.isfinite(M), M, np.inf).astype(np.float32)
        mm, um, mh = blok(self.mah, self.mah), blok(self.us, self.mah), blok(self.mah, self.has)
        # son kilometre yürüyüş: hedef mahalle j'ye komşu k üzerinden (sütun güncellemesi); yaralı taşıma için kaynak tarafı
        for M in (mm, um):
            for j, (k, w) in enumerate(zip(self.komsu, self.yurume)):
                if len(k):
                    M[:, j] = np.minimum(M[:, j], (M[:, k] + w[None, :]).min(1))
        for i, (k, w) in enumerate(zip(self.komsu, self.yurume)):
            if len(k):
                mh[i] = np.minimum(mh[i], (mh[k] + w[:, None]).min(0))
        out = dict(mah_mah=mm, us_mah=um, mah_has=mh)
        if ek is not None:
            me = blok(self.mah, ek)
            for i, (k, w) in enumerate(zip(self.komsu, self.yurume)):
                if len(k):
                    me[i] = np.minimum(me[i], (me[k] + w[:, None]).min(0))
            out["mah_ek"] = me
        return out
