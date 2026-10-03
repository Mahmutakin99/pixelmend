# PixelMend 1.0.0-rc.3 — macOS Apple Silicon

DMG normal kurulum içindir; ZIP aynı uygulamanın alternatif arşividir. İkisini birden kurmanız gerekmez. DMG içindeki PixelMend uygulamasını Applications klasörüne sürükleyin.

Bu paket ARM64 (M1 ve sonraki Apple Silicon Mac) içindir. Developer ID imzası ve Apple notarization yoktur; macOS ilk açılışta güvenlik onayı isteyebilir. Sistem Ayarları → Gizlilik ve Güvenlik üzerinden uygulamaya özel açma seçeneğini kullanın.

Test adımları `test-kit/ONCE-OKUYUN.md` dosyasındadır. Testler model dosyalarını gerektiğinde indirir. Dört temel AI modeli kullanılabilir; ileri kartların “yakında” olması beklenir.

`SHA256SUMS` dosyasını bu klasörde `shasum -a 256 -c SHA256SUMS` komutuyla doğrulayabilirsiniz.
