<p align="center"><img src="assets/icon.png" width="96" alt="PixelMend uygulama simgesi"></p>

<h1 align="center">PixelMend</h1>
<p align="center">Fotoğraflarınızı onarın, büyütün ve düzenleyin. Kendi bilgisayarınızda.</p>
<p align="center"><strong>macOS · Apple Silicon · Yerel görüntü işleme · Geliştirme / RC</strong></p>
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

PixelMend geliştirme aşamasındadır. Bu tanıtımdaki kurulu uygulama **1.0.0-rc.2** sürümüdür; ekran görüntüleri **2 Ekim 2026** tarihinde alınmıştır. Kaynak projenin 24 Eylül 2026 durum kaydında ileri model kabulü, Windows / Linux gerçek cihaz doğrulaması ve nihai yayın açık işler olarak yer alır.

| Platform | Durum |
| --- | --- |
| macOS / Apple Silicon | Yerel RC uygulaması; bu galerinin platformu |
| Windows / Linux | Hedef platformlar; genel kullanıma hazır veya cihaz üzerinde kabul edilmiş olarak sunulmaz |
| Genel indirme | Bu tanıtım deposunda yayımlanmış kurulum paketi yok |

Ekran görüntüleri yalnız arayüzü belgelemektedir. Bu depo yeni bir kalite karşılaştırması, hız ölçümü, GPU hızlanması kanıtı veya tüm modellerin hazır olduğuna dair bir iddia içermez.

## Geri bildirim

[Hata bildirimi](https://github.com/Mahmutakin99/pixelmend-showcase/issues/new?template=bug-report.yml) veya [özellik önerisi](https://github.com/Mahmutakin99/pixelmend-showcase/issues/new?template=feature-request.yml) ile katkıda bulunabilirsiniz. Sürüm ve işletim sistemi bilgisini, beklenen davranışı ve tekrar adımlarını ekleyin. Herkese açık bir bildirime özel fotoğraf, kişisel dosya yolu veya hassas tanı verisi eklemeyin.

Mahmut AKIN · [GitHub](https://github.com/Mahmutakin99)

## Haklar ve üçüncü taraflar

Bu tanıtım deposunun özgün metinleri için [haklar bildirimi](RIGHTS.md) geçerlidir. Kaynak projedeki Apache-2.0 lisansı, ilgili devralınan varlıkların hakları ve üçüncü taraf fotoğraf / model lisansları ayrı ayrı korunur. Buradaki haklar bildirimi mevcut lisansları değiştirmez. Model dosyaları ve uygulama ikilileri bu depoya dahil değildir.
