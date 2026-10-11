/** Kaydırmalı anlatının DOM tarafı: bölüm kartları, bölüm geçişini tetikleyen gözlemci ve lejant. */
import type { Bolum } from './bolumler'
import type { Arayuz } from './dil'
import { yerYaricap } from './katmanlar'

export function hikaye(bol: Bolum[], sahne: (b: Bolum) => void, a: Arayuz): void {
  const kok = document.getElementById('hikaye')!
  kok.innerHTML = bol.map((b, i) => `
    <section class="bolum ${i === 0 ? 'kapak' : b.id}" data-i="${i}">
      <article class="kart">
        ${i === 0 ? '' : `<p class="ust"><span class="no">${String(i).padStart(2, '0')}</span>${b.ust}</p>`}
        ${i === 0 ? `<p class="ust">${b.ust}</p><h1>${b.baslik}</h1>` : `<h2>${b.baslik}</h2>`}
        <p class="metin">${b.metin}</p>
        ${b.defter ? `<dl class="defter">
          <div><dt>${a.veri}</dt><dd>${b.defter.veri}</dd></div>
          <div><dt>${a.nasil}</dt><dd>${b.defter.nasil}</dd></div>
          ${b.defter.hesap ? `<div class="hesap"><dt>${a.hesap}</dt><dd>${b.defter.hesap}</dd></div>` : ''}
        </dl>` : `<p class="analiz"><span>${a.analiz}</span>${b.analiz ?? ''}</p>`}
      </article>
    </section>`).join('')
  let aktif = -1
  const io = new IntersectionObserver((g) => {
    for (const e of g) {
      if (!e.isIntersecting) continue
      const i = Number((e.target as HTMLElement).dataset.i)
      if (i === aktif) continue
      aktif = i
      document.querySelectorAll('.bolum').forEach((el, j) => el.classList.toggle('aktif', j === i))
      sahne(bol[i]!)
    }
  }, { rootMargin: '-45% 0px -45% 0px' })
  kok.querySelectorAll('.bolum').forEach((el) => io.observe(el))
}

export function lejant(b: Bolum, a: Arayuz): void {
  const l = a.lejant
  const el = document.getElementById('lejant')!
  const k = b.katman
  const satir: string[] = []
  if (k.akis) satir.push(`<li><i class="cizgi amber"></i>${l.akis}</li>`)
  if (k.istanbul) {
    const daire = (n: number) => { const d = 2 * yerYaricap(n); return `<span class="olcek"><i style="width:${d}px;height:${d}px"></i>${l.bin(n)}</span>` }
    satir.push(`<li class="baslik">${l.istanbul}</li><li class="olcekler">${[5000, 20000, 50000].map(daire).join('')}</li>`,
      `<li><i class="nokta soluk"></i>${l.yeterli}</li>`)
  }
  if (k.yersiz) satir.push(`<li><i class="nokta pembe"></i>${l.yersiz}</li>`)
  if (k.alan) satir.push(`<li><i class="halka"></i>${l.alan}</li>`)
  if (k.cikis) satir.push(`<li><i class="cizgi amber"></i>${l.cikis}</li>`)
  if (k.hastane) satir.push(`<li><i class="sutun mavi"></i>${l.hastane}</li>`)
  if (b.id === 'kalabalik' || b.id === 'yakin') satir.push(`<li><i class="kutu"></i>${l.bina}</li>`)
  el.innerHTML = satir.length ? `<ul>${satir.join('')}</ul>` : ''
  el.classList.toggle('gorunur', satir.length > 0)
}
