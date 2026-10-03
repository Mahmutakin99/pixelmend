# macOS rc.3 paket doğrulaması — 2026-10-03

Hedef: macOS Apple Silicon ARM64. Sürüm: 1.0.0-rc.3.
Paketler Developer ID ile imzalanmamış ve notarize edilmemiştir.

- Masaüstü: 7 Electron kontrolü + 39 Vitest testi geçti.
- CI araçları: 15 test geçti.
- Motor: sandbox dışındaki yerel bağlantı testi dahil 179 test geçti, 2 gerçek-model testi atlandı. Starlette bağımlılık uyarısı mevcut.
- PyInstaller ARM64 motoru, TypeScript/Vite build, Electron DMG ve ZIP üretimi tamamlandı.
- DMG iç bütünlük kontrolü ve ZIP sıkıştırma kontrolü geçti.
- Salt okunur bağlanan DMG ve çıkarılan ZIP içindeki uygulamalar ayrı ayrı gerçek motor/OpenCV/PNG smoke testinden geçti (çıkış kodu 0).
- `SHA256SUMS` iki dağıtım dosyası için doğrulandı.
- Paketli uygulamanın otomatik standart tanısı `verification/` altında ZIP ve HTML/JSON rapor oluşturdu. OpenCV, Lanczos, maske/alfa, temel iş iptali, iptal sonrası iş, açık/koyu tema kontrolleri, boya, PNG kayıt, proje kayıt/açma, nesne silme arayüzü ve motor kapanması geçti.

## İlk paket doğrulamasının sınırı

Bu makinede MI-GAN, LaMa ve iki RealESRGAN model dosyası kurulu değildir.
Bu yüzden model adımları `not_installed`, ileri iki model `unsupported` olarak
raporlandı; genel tanı `incomplete` (çıkış kodu 2) durumundadır.
Mevcut `e2e/editor.cjs` testi de varsayılan AI silme adımında kurulu LaMa
beklediği için durdu; renderer hatası yoktu. Bu koşu başarılı sayılmadı.

Model kurulumu sonrası AI işlemleri ve kapsamlı fotoğraf kalitesi yeniden
doğrulanmalıdır. Önceki Mac kabul kayıtları bu yeni rc.3 paketinin tamamı için
güncel kalite kabulü sayılmaz. Bu teslim çalıştırılabilir rc.3 dağıtım paketidir.

Build manifestindeki commit, kaynak tabanı commitidir; paket üretimi sırasında
sürüm numarası ve Mac yönergesi çalışma ağacında değiştirilmiştir.

## Model kurulumu sonrası kullanıcı koşuları

2026-10-03'te kullanıcı dört modeli kurup standart ve kapsamlı koşuyu
tamamladı. Standartta 21, kapsamlıda 707 kontrol geçti; başarısız kontrol yok.
İki raporda yalnız beklenen SDXL/Swin2SR `unsupported` satırları bulundu.
12 fotoğraf ve büyük çıktılar ayrıca AI destekli görsel karşılaştırmadan geçti.
Sabit küçük maske nedeniyle büyük nesne silme ve çalışan AI iptali kabulü
bu raporlardan çıkarılamaz; kullanıcı normal kullanım değerlendirmesi bekleniyor.
Güncel kanıt ve sınırlar:
[`Mac rc.3 incelemesi`](../../../docs/verification/mac-rc3-review-2026-10-03.md).
