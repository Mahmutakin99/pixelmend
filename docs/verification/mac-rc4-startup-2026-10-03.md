# Mac rc.4 açılış doğrulaması — 2026-10-03

## Sonuç

rc.4 ARM64 uygulaması `/Applications/PixelMend.app` içine kuruldu. Pencere artık
model doğrulama/sınamalarını beklemiyor. Güvenlik ve gerçek sağlayıcı sınamaları
korunarak dört model arka planda sırayla hazırlanıyor.

Bu M4 Mac'te paketli uygulamanın normal (self-test/headless olmayan) native
koşuları, yalnız test profili ve sentetik fotoğrafla ölçüldü:

| Koşu | Etkileşimli pencere | Temel düzenleme tamamlandı | Dört model hazır |
|---|---:|---:|---:|
| 1 | 272 ms | 1299 ms | 25257 ms |
| 2 | 277 ms | 1265 ms | 25159 ms |
| 3 | 271 ms | 1267 ms | 25255 ms |

rc.3 motor sağlık yanıtı ölçümü 25555 ms idi; eski kod pencereyi bundan sonra
oluşturuyordu. Yeni ölçümler uygulama sürecinin başlatılmasından itibaren alınır;
Finder/Gatekeeper'ın ilk indirme kontrolü ya da tüm Mac'ler için süre garantisi değildir.

Her koşuda modeller hazırlanırken ayarlar, Hakkında rc.4, fotoğraf açma,
çizim, OpenCV ve Lanczos işlemleri tamamlandı; PNG kaydı doğrulandı. Hazırlık
sırasında ayrıca normal pencere kapatma 595 ms'de tamamlandı. Native motor
zorla öldürülmedi. [Ölçümler](../../release/macos/1.0.0-rc.4/verification/startup/timings.json)
ve [erken kapatma](../../release/macos/1.0.0-rc.4/verification/startup/early-close.json)
kanıtları korunuyor.

## Testler

- Python tam suite: 184 passed, 2 isteğe bağlı test skipped; mevcut Starlette
  `httpx` deprecation uyarısı. Gerçek model kabul testi ayrıca 1 passed (40.67 s):
  kaynak/maske/alfa ve gerçek model/provider sonuç bilgisi doğrulandı.
- Desktop: 14 Node kontrolü + 40 Vitest geçti; CI-tools 15 geçti; tsc/Vite build geçti.
- Kurulu uygulama editör E2E: geçti. Çizim/silgi/undo-redo, LaMa önizleme,
  vazgeç/uygula, PNG kayıt, Lanczos büyütme, ayarlar, zoom ve çıkış onayı sınandı.
- Bu E2E'de önceden var olan zoom tekerleği `preventDefault`/pasif dinleyici
  console uyarısı görüldü; renderer `pageerror` yok, zoom beklentisi geçti.
  Bu açılış düzeltmesinde tekerlek davranışı değiştirilmedi.
- İlk editör testi eski `dialog` seçicisi yüzünden çıkış onayında başarısız oldu;
  gerçek DOM/ekran `alertdialog` olduğunu gösterdi, yalnız test seçicisi düzeltildi.
- Kurulu editör ile aynı cache kullanan gerçek model testi eşzamanlı çalıştığında
  AI başlatma başarısız oldu. Süreçler arası model kilidi olası neden olarak
  belirlendi; güvenlik kilidi kaldırılmadı. Tek başına tekrar koşusu geçti.
- Bağımsız kod incelemesinin tek Important bulgusu düzeltildi: tanı zaman aşımı/
  iptal raporu, uzun native drain beklenmeden kaydedilip ZIP'e dönüştürülür.
  Regresyon önce başarısız, düzeltmeden sonra başarılı oldu.

## Standart tanı ve paketler

Kendi Mac başlatıcısı kurulu uygulamayla çalıştırıldı. Geçici test sarmalayıcısı
yalnız `--self-test-auto` ekledi; yayımlanmış başlatıcı değiştirilmedi.

- Sürüm: rc.4. 21 passed, 2 unsupported, başka sonuç yok. Beklenen SDXL ve
  Swin2SR nedeniyle genel durum `incomplete`, çıkış kodu 2.
- Dört model hazır; MI-GAN/LaMa CPU, iki RealESRGAN otomatik Core ML ve açık
  CPU koşularında başarılı. CPU sonucu GPU-only kabulü değildir.
- [Standart ZIP](../../release/macos/1.0.0-rc.4/verification/standard/PixelMend-Test-2026-10-03T20-03-13-879Z-6b11d8bf.zip)
  bütünlüğü doğrulandı. SHA-256:
  `d63f7652dcc06e1ca97ae267ea56279c02d396bfb8e1538dd105fbfdf1af1e64`.
- DMG dahili checksum, ZIP bütünlüğü ve [SHA256SUMS](../../release/macos/1.0.0-rc.4/SHA256SUMS)
  geçti. Salt-okunur DMG uygulaması ve ZIP'ten çıkarılan uygulama bağımsız
  OpenCV/PNG smoke testlerinde exit 0 verdi; DMG bağlaması kaldırıldı.
- Commit öncesi kurulu ve yerel paket uygulamasının `app.asar` / motor binary
  SHA-256 değerleri birebir eşleşti: sırasıyla
  `5abe59e55a3045a377a6d714284ec9d26341684f92e234ee0c6e8d877df5ca86` ve
  `3bbf8d5a15eaadb4962322a03352a1d0709f652f92fe22b7a05ac80b4c01ee94`.
- Paket Developer ID ile imzalanmadı/notarize edilmedi. PyInstaller'ın isteğe
  bağlı `onnxruntime.quantization` toplama uyarısı (onnx yok) runtime smoke ve
  dört gerçek model testini engellemedi. Paketleme anında kaynak değişiklikleri
  commit edilmemişti; tarihsel manifest bu nedenle commit'i taban revizyon ve
  paketleme çalışma ağacını dirty olarak belirtir.

## Kapsamlı tanı — commit öncesi tekrar

Kurulu rc.4/kendi Mac test-kiti + yalnız otomatik/kapsamlı bayrak ekleyen
geçici sarmalayıcı: 20:48:57–21:34:53 UTC, yaklaşık 46 dakika, exit 2.
707 passed + beklenen 2 unsupported; hiçbir failed/timeout/kaynak yetersizliği
yok. 12 fotoğraf/672 iş, 1600×900 ve 2400×1350 kaynaklar dahil, dört tekrar
boyunca geçti. En büyük çıktı 9600×5400. Motor kapanışı geçti; uygulama ve
motor süreçlerinin kalmadığı kontrol edildi.

721 artefakt oluştu; 685 sonuç PNG'sinin başlığı/boyutu ayrıca raporla
karşılaştırıldı. ZIP bütünlüğü geçti; SHA-256
`9d65c1b7928f83e1ad84bb3ea806f69aecbba531e620aa4299f996acb3bee228`.
[Yerel kapsamlı ZIP](../../release/macos/1.0.0-rc.4/verification/comprehensive/PixelMend-Test-2026-10-03T20-48-57-928Z-ab6b7efa.zip)
ve [AI destekli görsel inceleme](mac-rc4-visual-review-2026-10-03.md) korunur.
PNG/ZIP/DMG'ler yereldir; git'e yalnız kaynak/test-kiti ve seçili metin kanıtı
alınır. İnsan kalite onayı veya GPU-only kabulü verilmez.

## Koruma ve kalan kabul

İndirilen modeller ve kullanıcı profili değiştirilmedi. rc.3 paket/ZIP kanıtları
korundu. Eski uygulama geri alınabilir olarak
`/Users/gladius/.Trash/PixelMend-rc4-update.7k6DYd/PixelMend-rc.3.app` içine taşındı.
Yeni DMG/ZIP/test kiti [rc.4 klasöründedir](../../release/macos/1.0.0-rc.4).

Kısa günlük kullanıcı kontrolü kullanıcı tarafından "tamamdır sorun yok" ile
onaylandı. rc.4 kapsamlı ZIP ve AI destekli görsel inceleme tamamlandı;
kapsamlı sonuçların nihai insan görsel onayı henüz beklemede.
rc.3 kapsamlı raporları rc.4 nihai kabulü sayılmadı.
Windows/Linux işleri ertelendi. Kaynaklar mevcut `feat/mac-local-ai` dalına
commit/push için hazırlandı; merge, release tag ve paket yayımlama kapsam dışı.

Uygulama-planı/TDD becerileri regresyon ve bağımsız inceleme kapısını; React
becerisi türetilmiş hazırlık durumlarını ekstra effect/state olmadan göstermeyi;
axiom-ai becerisi native sınamayı arka planda tutarken gerçek donanım ve çıktı
doğrulamasını korumayı yönlendirdi. Playwright için mevcut Electron harness'ı kullanıldı.
