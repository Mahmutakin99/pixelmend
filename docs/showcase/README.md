<p align="center"><img src="assets/icon.png" width="96" alt="PixelMend uygulama simgesi"></p>

<h1 align="center">PixelMend</h1>
<p align="center">Fotoğraflarınızı onarın, büyütün ve düzenleyin. Kendi bilgisayarınızda.</p>
<p align="center"><strong>macOS Apple Silicon · Yerel görüntü işleme · İmzalı RC</strong></p>
<p align="center"><a href="https://github.com/Mahmutakin99/pixelmend/releases/tag/v1.0.0-rc.4">İndir · 1.0.0-rc.4 · Mac</a></p>
<p align="center">Türkçe · <a href="README.en.md">English</a></p>

![PixelMend fotoğraf düzenleyicisi](assets/02-editor.png)

PixelMend, fotoğraftaki istenmeyen alanları seçerek silmenizi, görseli büyütmenizi ve fırça araçlarıyla düzenlemenizi sağlayan bir masaüstü uygulamasıdır. Fotoğraf işleme yerel motor üzerinde yapılır; fotoğraflar düzenleme için dış servislere gönderilmez. Model kurulumu ayrıca indirme gerektirebilir.

Bu depo uygulamanın herkese açık tanıtım ve geri bildirim alanıdır. Açık kaynak kod [PixelMend deposundadır](https://github.com/Mahmutakin99/pixelmend); indirilen sürümün kaynağı kendi Release etiketidir.

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

Ekran görüntüleri çalışan macOS uygulamasından alınmıştır; tasarım maketi değildir. Gösterilen fotoğraf kamu malı NASA / Eileen Collins görselidir. Galeri **1.0.0-rc.2** uygulamasından **2 Ekim 2026** tarihinde alınmıştır; yeni rc.4 kalite/hız ölçümü değildir. Örnek fotoğraf: [scikit-image astronaut / NASA](https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png), [kamu malı hak bilgisi](https://scikit-image.org/docs/0.25.x/api/skimage.data.html#skimage.data.astronaut). NASA veya fotoğraftaki kişinin PixelMend’i desteklediği ima edilmez.

| Başlangıç | Büyütme |
| --- | --- |
| ![PixelMend başlangıç ekranı](assets/01-workspace.png) | ![Büyütme seçenekleri](assets/03-upscale.png) |

![PixelMend ayarları](assets/04-settings.png)

## Kullanılabilirlik

Güncel Mac yayını **1.0.0-rc.4**, Developer ID Application ile imzalı ve Apple tarafından notarize edilmiş ön sürümdür. Modeller ayrı indirilir. Model hazırlığı sırasında görsel açma, çizim, OpenCV ve Lanczos kullanılabilir; ilgili AI modeli hazır olunca etkinleşir. SDXL ve Swin2SR henüz desteklenmez.

| Platform | Durum |
| --- | --- |
| macOS / Apple Silicon | RC.4 · [DMG](https://github.com/Mahmutakin99/pixelmend/releases/download/v1.0.0-rc.4/PixelMend-1.0.0-rc.4-arm64.dmg) / [ZIP](https://github.com/Mahmutakin99/pixelmend/releases/download/v1.0.0-rc.4/PixelMend-1.0.0-rc.4-arm64-mac.zip); M1 ve sonrası, aynı uygulama için iki alternatif |
| Windows x64 | [Eski RC.2 arşivi](https://github.com/Mahmutakin99/pixelmend/releases/tag/showcase-v1.0.0-rc.2); bu yeni yayında Windows kabulü/imzası iddia edilmez |
| Linux / Intel Mac | Bu yeni Mac yayınına dahil değildir |

[Sürüm notları, SHA-256 ve Mac test kiti](https://github.com/Mahmutakin99/pixelmend/releases/tag/v1.0.0-rc.4). Test kitindeki `.command` dosyası kurulum yapmaz, kurulu uygulamanın tanı penceresini açar. Raporlar otomatik gönderilmez. Eski rc.2 paketlerinin imza durumu yeni rc.4 ile aynı değildir; eski Windows paketinde SmartScreen uyarısı çıkabilir. Sistem genelinde güvenlik korumalarını kapatmayın.

AI çıktısını kaydetmeden önce inceleyin. Ekran görüntüleri yalnız arayüzü belgeler; GPU-only çalışma veya tüm modellerin hazır olduğuna dair garanti değildir.

## Geri bildirim

[Hata bildirimi](https://github.com/Mahmutakin99/pixelmend/issues/new) veya [özellik önerisi](https://github.com/Mahmutakin99/pixelmend/issues/new) ile katkıda bulunabilirsiniz. Sürüm ve işletim sistemi bilgisini, beklenen davranışı ve tekrar adımlarını ekleyin. Herkese açık bir bildirime özel fotoğraf, kişisel dosya yolu veya hassas tanı verisi eklemeyin.

Mahmut AKIN · [GitHub](https://github.com/Mahmutakin99)

## Haklar ve üçüncü taraflar

Bu tanıtım deposunun özgün metinleri için [haklar bildirimi](RIGHTS.md) geçerlidir. Kaynak projedeki Apache-2.0 lisansı, ilgili devralınan varlıkların hakları ve üçüncü taraf fotoğraf / model lisansları ayrı ayrı korunur. Buradaki haklar bildirimi mevcut lisansları değiştirmez. Uygulama paketleri Releases alanındadır; kaynak kod Git ağacına eklenmez. Model dosyaları ayrı indirilir.
