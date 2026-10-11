import { defineConfig } from 'vite'
import { resolve } from 'node:path'
// maplibre-gl 6 işçisini ayrı ES modülü olarak göreli adresten yükler; Vite'ın ön paketlemesi bu adresi kırar.
// "Nasıl yaptık" metni tek kaynaktan (docs/web_metin) okunur; bu yüzden üst klasöre dosya erişimi açık.
export default defineConfig({
  server: { port: 5272, strictPort: true, fs: { allow: ['..'] } },
  optimizeDeps: { exclude: ['maplibre-gl'] },
  worker: { format: 'es' },
  build: { rollupOptions: { input: { ana: resolve(import.meta.dirname, 'index.html'), nasil: resolve(import.meta.dirname, 'nasil.html') } } },
})
