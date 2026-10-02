# Ekran görüntüsü kaydı / Screenshot provenance

**Tarih / Date:** 2026-10-02

**Uygulama / Application:** PixelMend 1.0.0-rc.2, installed macOS Apple Silicon application

**Dil / Language:** Türkçe
**Tema / Theme:** Sistem / açık (system / light)

Galeri, gerçek Electron uygulaması ve yerel motoru başlatılarak, ayrı geçici kullanıcı profiliyle yakalandı. Projenin mevcut Electron / Playwright yaklaşımı kullanıldı. Yalnız uygulamanın renderer alanı kaydedildi; masaüstü, diğer uygulamalar, yerel dosya yolları veya kullanıcı fotoğrafları dahil edilmedi. Görseller oluşturulmuş tasarım maketleri değildir; uygulamanın arayüzü değiştirilmedi. Düzenleyici görünümünde uygulamanın kendi yakınlaştırma hareketi kullanıldı.

The gallery was captured from the real Electron application with its local engine and an isolated temporary profile, following the project's existing Electron / Playwright approach. Only the application renderer was captured. No desktop, unrelated applications, personal paths or user photos are included. These are not generated mockups; no interface content was substituted. The editor uses the application's own zoom gesture.

| Dosya / File | Görünüm / View |
| --- | --- |
| `01-workspace.png` | Başlangıç / Start screen |
| `02-editor.png` | Açılmış fotoğraf ve çizim araçları / Imported photo and drawing tools |
| `03-upscale.png` | Standart ve AI büyütme seçenekleri / Standard and AI enlargement controls |
| `04-settings.png` | Genel ayarlar / General settings |

Bu çekimde model kurulumu veya AI işlemi çalıştırılmadı. AI yolunun hazır olmadığı metin olduğu gibi bırakıldı. Ekranlar model kalitesi, hız veya donanım hızlanması hakkında kanıt değildir. Kaynak projenin daha yeni çalışma ağacı, kurulu RC ile aynı sürüm olarak sunulmaz.

No model installation or AI operation was performed for this capture. The displayed unavailable-model state is preserved. These captures are not quality, speed or hardware acceleration evidence. A newer source working tree is not presented as identical to the installed RC.

## Fotoğraf / Photograph

NASA'nın Eileen Collins fotoğrafı, scikit-image `astronaut` örneği üzerinden alınmıştır. Kaynak projenin doğrulanmış tanı fixture'ı kullanıldı: RGB / Lanczos thumbnail, 192 × 192 px. Görselin kullanımı bir AI sonucu veya before/after karşılaştırması değildir.

The photograph depicts Eileen Collins and originates from NASA, distributed as scikit-image's `astronaut` sample. The source project's verified diagnostic fixture was used: RGB / Lanczos thumbnail, 192 × 192 px. This is an imported sample, not an AI result or before/after comparison.

- Kaynak / Source: [scikit-image v0.25.2 astronaut image](https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png)
- Hak durumu / Rights: Public domain / kamu malı; [scikit-image data documentation](https://scikit-image.org/docs/0.25.x/api/skimage.data.html#skimage.data.astronaut)
- Fixture SHA-256: `1998f41015c1258f6ff375a146575644390ad607f0e59c446806857321b966e2`
- Orijinal / Original SHA-256: `88431cd9653ccd539741b555fb0a46b61558b301d4110412b5bc28b5e3ea6cb5`

NASA veya görseldeki kişinin uygulamayı desteklediği ima edilmez. / No endorsement by NASA or the person depicted is implied.

## Uygulama varlıkları / Application assets

`assets/icon.png` kaynak projenin mevcut uygulama simgesidir. Yeni bir logo üretilmedi. Kaynak projenin Apache-2.0 lisans bildirimi [burada](LICENSE.Apache-2.0.txt) korunur.

`assets/icon.png` is the existing application icon from the source project. No replacement logo was generated. The source project's Apache-2.0 license notice is [retained here](LICENSE.Apache-2.0.txt).

Yakalanan / Captured application `app.asar` SHA-256: `e16136d26e33c60c6091f79b0dae64af42e81f92efb0ad0df86dc2899500bc1f`.
