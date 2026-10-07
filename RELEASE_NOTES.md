# PixelMend 1.1.0-alpha.5

Apple Silicon için deneysel Mac ön sürümü. [İndirme dosyaları](https://github.com/Mahmutakin99/pixelmend/releases/tag/v1.1.0-alpha.5).

## Değişiklikler

Kaynak kod incelemesindeki 19 bulgu giderildi:

- PNG ve proje kayıtları geçici dosyada tamamlanıp atomik olarak değiştirilir; başarısız kayıt mevcut dosyayı korur.
- Önizleme, export ve iş varlıklarının sahipliği ortak yönetilir. Vazgeçilen sonuçlar temizlenir; proje geçmişindeki fotoğraflar ve devam eden işlemlerin kaynakları korunur. Pencere yenilenirken geç gelen sonuçlar da temizlenir.
- Geri al/yinele geçmişi değişmeyen çizgi verilerini paylaşır. Yeni `.pixelmend` v2 biçimi fotoğrafları ve çizgileri tekrar saklamaz; PNG'ler Base64 yerine arşive akışla yazılır. Arşiv girişleri, boyutları ve SHA-256 değerleri açılmadan önce doğrulanır; başarısız açılış mevcut belgeyi korur.
- Motor tamamlanmış işler, model önbelleği ve benchmark tekrarlarından kalan büyük nesneleri bırakır. Ağır görsel hazırlığı kısa varlık deposu kilidinden ayrılır. Desteklenmeyen birden fazla AI adımı model yüklenmeden reddedilir.
- Boya bindirmesi Canvas ile aynı source-over davranışını kullanır. Fırça maskeleri sınırlı parçalarda hesaplanır; imleç hareketinde tüm çizgi tekrar dönüştürülmez. Çok uzun çizgiler aynı geri alma adımı içinde parçalara ayrılır.
- Düzenleme ön kontrolü yalnız seçim geometrisini hazırlar; tam görsel hazırlığı bellek kontrolünden sonra yapılır. Tekrarlayan bellek ayırma hataları gereksiz hızlı yeniden denemeye dönüşmez; iptal edilebilir bekleme ve tamamlanmış denoise verisi korunur.
- Çizgi doğrulaması motor ve arayüz arasında tutarlıdır. Yeni model olayları eski istek sonuçlarıyla ezilmez. Tanılama, kurulu üretken modelleri ve başarısız/iptal edilmiş kurulumları doğru değerlendirir; takılan istekler zaman aşımıyla iptal edilir.
- Paket profili kontrolleri, test kiti çıktı argümanı, yalnız açık fotoğraf referanslarıyla proje varlığı tespiti ve SDXL seçim kırpması düzeltildi. SDXL kullanıma açılmadı.

Mevcut arayüz, model, hassasiyet ve çalışma çözünürlüğü korunur. Düşük kullanılabilir bellek kaliteyi otomatik düşürmez; kritik baskıda aşamalar arasında beklenebilir. Süre bellek baskısına ve takas belleğine bağlıdır.

## Proje uyumluluğu

Alpha5 eski v1 `.pixelmend` dosyalarını açar. Yeni kayıtlar v2 biçimindedir ve **Alpha4 ile açılamaz**. Eski uygulamada açmanız gereken v1 dosyalarının kopyalarını saklayın.

V2 arşivindeki belge bildirimi en fazla 64 MiB, fotoğraf sayısı en fazla 32 olabilir. Tek çizgi parçası 8192, tek katman 2048 çizgi ve 250.000 noktayla sınırlıdır. Sınır aşılırsa mevcut kayıt değiştirilmez.

## Kurulum

Developer ID Application imzalı ve Apple tarafından notarize edilmiş paketler:

- [DMG](https://github.com/Mahmutakin99/pixelmend/releases/download/v1.1.0-alpha.5/PixelMend-1.1.0-alpha.5-arm64-signed.dmg)
- [ZIP](https://github.com/Mahmutakin99/pixelmend/releases/download/v1.1.0-alpha.5/PixelMend-1.1.0-alpha.5-arm64-signed.zip)

DMG'yi açıp PixelMend'i Applications klasörüne sürükleyin veya ZIP'i açın. Homebrew ile:

```sh
brew install --cask Mahmutakin99/pixelmend/pixelmend
```

Homebrew ile kurulu uygulamayı güncellemek için:

```sh
brew upgrade --cask Mahmutakin99/pixelmend/pixelmend
```

Homebrew tanımı [ayrı tap deposundadır](https://github.com/Mahmutakin99/homebrew-pixelmend). Elle kurulmuş uygulamayı Homebrew yönetimine geçirirken uygulamayı kapatıp yalnız eski `PixelMend.app` kopyasını kaldırın; model ve proje dizinlerini silmeyin.

Apple Silicon ve macOS 15+ gerekir. Üretken AI en az 16 GB fiziksel RAM ve kabul edilmiş cihaz/profil eşleşmesi gerektirir. Modeller paketlere dahil değildir; Ayarlar → AI modelleri üzerinden ayrıca kurulur. Mevcut kurulu modeller yeniden indirilmez.

## Doğrulama

343 Python testi geçti, iki test atlandı. Ayrıca 38 Electron, 69 arayüz ve 31 araç testi ile TypeScript kontrolü geçti. Gerçek uygulamada yarı saydam boyanın PNG export sonucu Canvas ile kanal başına en fazla bir ton farklılık gösterdi. 8193 noktalı çizgi canlı görünümle aynı tekrar çizildi; tek geri alma adımıyla kompakt projeye kaydedildi.

Gerçek model kalite/hız karşılaştırması, paket kabul kontrolleri, SHA-256 ve imza/notarizasyon sonuçları Release eklerindeki `verification-report.md`, `native-acceptance.json`, `build-manifest.json` ve `signing-status.json` dosyalarındadır. Sonuçlar bu Mac'te ölçülmüştür; her cihazda aynı süreyi veya bellek kullanımını garanti etmez.
