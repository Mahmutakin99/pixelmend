<p align="center"><img src="assets/icon.png" width="96" alt="PixelMend uygulama simgesi"></p>

<h1 align="center">PixelMend</h1>
<p align="center">Fotoğraflarınızı onarın, büyütün ve düzenleyin. Kendi bilgisayarınızda.</p>
<p align="center"><strong>macOS Apple Silicon · Windows x64 · Yerel görüntü işleme · RC</strong></p>
<p align="center"><a href="https://github.com/Mahmutakin99/pixelmend-showcase/releases/tag/v1.0.0-rc.2">İndir · 1.0.0-rc.2</a></p>
<p align="center">Türkçe · <a href="README.en.md">English</a></p>

![PixelMend fotoğraf düzenleyicisi](assets/02-editor.png)

PixelMend, fotoğraftaki istenmeyen alanları seçerek silmenizi, görseli büyütmenizi ve fırça araçlarıyla düzenlemenizi sağlayan bir masaüstü uygulamasıdır. Fotoğraf işleme yerel motor üzerinde yapılır; fotoğraflar düzenleme için dış servislere gönderilmez. Model kurulumu ayrıca indirme gerektirebilir.

Bu depo uygulamanın herkese açık tanıtım ve geri bildirim alanıdır. Uygulama kaynak kodu burada yayımlanmaz.

## Bir fotoğraftan sonraki adıma

| İşlem | PixelMend'de |
| --- | --- |
| Nesne silme | Fırçayla alan seçimi; hazır modele bağlı AI yolu veya ayrı Hızlı / OpenCV seçimi |
| Büyütme | Standart / Lanczos ve hazır modele bağlı AI iyileştirme; 2×, 4× veya özel ölçü |
| Düzenleme | Çizim, silgi, seçim araçları, geri al / yinele ve yakınlaştırma |
| Sonucu değerlendirme | İşlem önizlemesini uygulama veya vazgeçme; sonuçtan düzenlemeye devam etme |
| Çalışmayı saklama | PNG dışa aktarma ve `.pixelmend` proje kaydı |
| Çalışma alanı | Türkçe arayüz, açık / koyu / sistem teması ve model durumları |

AI sonuçları fotoğrafa ve seçime göre değişir. Önizleme, bir sonucu kaydetmeden önce değerlendirmeniz içindir; AI ile büyütme özgün ayrıntıyı yeniden yorumlayabilir.

## Uygulamanın içinden

Ekran görüntüleri çalışan macOS uygulamasından alınmıştır; tasarım maketi değildir. Gösterilen fotoğraf kamu malı NASA / Eileen Collins görselidir. [Görsel ve sürüm kaydı](docs/SCREENSHOTS.md).

| Başlangıç | Büyütme |
| --- | --- |
| ![PixelMend başlangıç ekranı](assets/01-workspace.png) | ![Büyütme seçenekleri](assets/03-upscale.png) |

![PixelMend ayarları](assets/04-settings.png)

## Kullanılabilirlik

PixelMend geliştirme aşamasındadır. Bu tanıtımdaki kurulu uygulama **1.0.0-rc.2** sürümüdür; ekran görüntüleri **2 Ekim 2026** tarihinde alınmıştır. Windows'ta çalıştığı geliştirici tarafından aynı tarihte doğrulanmıştır. Bu yayın hazırlığında ayrıca Windows cihaz testi yapılmamıştır. İleri model kabulü ve nihai kararlı sürüm çalışmaları devam eder.

| Platform | Durum |
| --- | --- |
| macOS / Apple Silicon | RC.2 · [DMG](https://github.com/Mahmutakin99/pixelmend-showcase/releases/download/v1.0.0-rc.2/PixelMend-1.0.0-rc.2-macOS-arm64.dmg) / [ZIP](https://github.com/Mahmutakin99/pixelmend-showcase/releases/download/v1.0.0-rc.2/PixelMend-1.0.0-rc.2-macOS-arm64.zip) |
| Windows x64 | RC.2 · [EXE](https://github.com/Mahmutakin99/pixelmend-showcase/releases/download/v1.0.0-rc.2/PixelMend-1.0.0-rc.2-Windows-x64-Setup.exe) / [ZIP + test başlatıcısı](https://github.com/Mahmutakin99/pixelmend-showcase/releases/download/v1.0.0-rc.2/PixelMend-1.0.0-rc.2-Windows-x64.zip); ZIP portable değildir |
| Linux | Destek tamamlanmadı; paket yayımlanmıyor |

[Sürüm notları, SHA-256 ve test kiti](https://github.com/Mahmutakin99/pixelmend-showcase/releases/tag/v1.0.0-rc.2). Test kitindeki `.sh` / `.command` / `.cmd` dosyaları kurulum yapmaz, kurulu uygulamanın tanı penceresini açar. macOS paketleri mevcut kurulu uygulamadan hazırlanmıştır; noter onayı yoktur. Windows SmartScreen uyarısı çıkabilir; doğrulanmış Authenticode imzası iddia edilmez. Sistem genelinde güvenlik korumalarını kapatmayın.

Kaynak Git deposu private kalır; ancak public Electron kurulum paketlerinden uygulamanın JavaScript kodu çıkarılabilir. Private depo, dağıtılan paketin kodunun incelenmesini mutlak biçimde engellemez.

Ekran görüntüleri yalnız arayüzü belgelemektedir. Bu depo yeni bir kalite karşılaştırması, hız ölçümü, GPU hızlanması kanıtı veya tüm modellerin hazır olduğuna dair bir iddia içermez.

## Geri bildirim

[Hata bildirimi](https://github.com/Mahmutakin99/pixelmend-showcase/issues/new?template=bug-report.yml) veya [özellik önerisi](https://github.com/Mahmutakin99/pixelmend-showcase/issues/new?template=feature-request.yml) ile katkıda bulunabilirsiniz. Sürüm ve işletim sistemi bilgisini, beklenen davranışı ve tekrar adımlarını ekleyin. Herkese açık bir bildirime özel fotoğraf, kişisel dosya yolu veya hassas tanı verisi eklemeyin.

Mahmut AKIN · [GitHub](https://github.com/Mahmutakin99)

## Haklar ve üçüncü taraflar

Bu tanıtım deposunun özgün metinleri için [haklar bildirimi](RIGHTS.md) geçerlidir. Kaynak projedeki Apache-2.0 lisansı, ilgili devralınan varlıkların hakları ve üçüncü taraf fotoğraf / model lisansları ayrı ayrı korunur. Buradaki haklar bildirimi mevcut lisansları değiştirmez. Uygulama paketleri Releases alanındadır; kaynak kod Git ağacına eklenmez. Model dosyaları ayrı indirilir.
