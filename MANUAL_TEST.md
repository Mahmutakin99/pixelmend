# PixelMend 1.0.0-rc.1 — Manuel Kabul

Paket: `release/1.0.0-rc.1/PixelMend-1.0.0-rc.1-arm64.dmg`. Bu imzasız test sürümüdür; macOS ilk açılışta güvenlik onayı isteyebilir. Model ağırlıkları uygulama paketinde değildir; LaMa ilk kullanımda indirilebilir.

1. DMG’yi açın, `PixelMend.app` dosyasını Applications’a sürükleyin ve açın. Boş durum ile “Görsel Aç” görünmelidir.
2. PNG/JPEG/WebP/TIFF dosyalarını dosya seçiciyle açın. EXIF yönlü görselde çizim, gösterilen pikselin üstünde kalmalıdır.
3. Tek tık ve uzun stroke ile maske boyayın; Silgi, Geri al, Yinele ve Maskeyi temizle düğmelerini deneyin.
4. Sil ile OpenCV sonucunu üretin; iş sırasında İptal’i deneyin. Sonuç gelince PNG kaydedin.
5. Şeffaf PNG/WebP/TIFF ile kaydedilen alfa kanalını, JPEG ile beyaz zemin birleşimini doğrulayın. Çıktılarda konum/EXIF olmamalıdır.
6. LaMa ile bir alanı silin. Sonuç seçildikten sonra ikinci düzenleme için kaynak tekrar açılabilir; orijinal dosyanın değişmediğini doğrulayın.
7. Lanczos 2× seçin; sonuç eni ve boyu iki kat olmalıdır.
8. Pencereyi daraltın, Tab/Enter ile kontrolleri gezin ve VoiceOver ile düğme adlarını kontrol edin.
9. İş sürerken uygulamayı kapatıp tekrar açın. Donmuş pencere veya eski sidecar süreci kalmamalıdır.

Hata raporunda paket adı, macOS sürümü, adım numarası, beklenen/gerçek sonuç ve `DURUM.md` içindeki son commit’i ekleyin. Kaynak fotoğraf veya token paylaşmayın.
