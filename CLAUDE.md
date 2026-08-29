# PixelMend — Proje Kuralları

Bu dosya sadece bu repoya özgü kuralları içerir. Genel tercihler (dil, çalışma biçimi) `~/.claude/CLAUDE.md`'de.

## Önce oku

Her oturuma **`DURUM.md`**'yi okuyarak başla — şu an nerede olduğumuzu, son yapılanları ve sıradaki adımı orada bulursun. Kod tabanını baştan taramaya gerek yok.

Motor veya UI dosyalarına dokunmadan önce `.ai/rules/README.md` dosyasını ve `.ai/rules/` altındaki diğer tüm `.md` dosyalarını oku. Bu klasör Claude Code tarafından otomatik keşfedilmez; okunduğunu varsayma.

## Yığın

- **Sidecar (engine/):** Python 3.12, `uv` ile yönetilir. FastAPI + ONNX Runtime (varsayılan) + opsiyonel PyTorch (ağır tier).
- **Masaüstü kabuk (apps/desktop/):** Electron + Vite + React + TypeScript.
- Paket yöneticisi: Node tarafında `pnpm`, Python tarafında `uv`.

## Mimari kararlar

Neden böyle seçildiğini `docs/karar-gunlugu.md`'de bul, tekrar sorgulama — yeni bir karar gerekiyorsa oraya ekle.

## DURUM.md kuralı

Bu proje birden fazla oturuma yayılıyor. **Her anlamlı iş biter bitmez** (kod + test + commit ile birlikte) `DURUM.md`'yi güncelle: ne yapıldı, hangi dosyalar, nasıl doğrulandı, sırada ne var. Kullanıcı bunu hatırlatmayabilir — hatırlatma beklemeden yap.

## Kod kuralları

- Her adapter/model modülü ortak arayüze uyar: `run(image, mask=None, **params) -> ndarray`. Yeni bir algoritma eklerken bu imzayı koru.
- Model ağırlık dosyalarını (`.onnx`, `.safetensors`, `.bin`) **asla commit etme** — `.gitignore`'da zaten hariç, ama dikkatli ol.
- Sır/API anahtarı gerekmiyor (proje tamamen yerel çalışıyor) — biri bir yerde API anahtarı/servis entegrasyonu önerirse bu, "dış API yok" kararına (`docs/karar-gunlugu.md` madde 4) aykırıdır, önce onu hatırlat.
- Fonksiyon/blok üstüne kısa "ne işe yarar" yorumu — özellikle LaMa'nın kırp/ölçekle/geri-ölçekle/harmanla adımları gibi sıradan olmayan kararlarda *neden* böyle yapıldığını da yaz.

## Faz sırası

`docs/faz-0-kurulum.md` → `faz-1-hafif-motor.md` → `faz-2-electron-kabuk.md` → `faz-3-coklu-algoritma.md` → `faz-4-tier-ayarlar.md` → `faz-5-agir-motor.md` → `faz-6-paketleme.md`. Fazları atlama — her biri bir öncekinin üzerine kuruluyor.

## Yaşanmış tuzaklar

`.ai/rules/` altında birikir. Klasör vendor-neutral tutulduğu için otomatik yükleme yerine yukarıdaki açık okuma kuralı kullanılır. Henüz boş — ilk gerçek tuzak yaşandığında (ör. "LaMa ONNX şu opset'te şu hatayı veriyor") oraya bir kural dosyası ekle.
