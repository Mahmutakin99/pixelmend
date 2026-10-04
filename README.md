# PixelMend

Fotoğrafları cihazınızda düzenleyen masaüstü uygulaması. Görselleriniz işlenmek için dış servislere gönderilmez.

- Nesne silme: LaMa ile AI veya OpenCV ile hızlı doldurma.
- Büyütme: Lanczos veya RealESRGAN ile 2×, 4× ve özel ölçüler.
- Çizim, seçim ve silgi araçları; geri al/yinele ve sonuç önizlemesi.
- PNG kaydı ve `.pixelmend` proje dosyaları.

## İndirme ve kurulum

Mac Apple Silicon (M1 ve sonrası) paketleri [Releases](https://github.com/Mahmutakin99/pixelmend/releases) bölümündedir. DMG'yi açıp PixelMend'i Applications klasörüne sürükleyin. ZIP aynı uygulama için alternatiftir.

Windows/Linux ve Intel Mac bu yeni Mac dağıtımının kapsamında değildir. RC sürümleri ön sürümdür; AI çıktısını kaydetmeden önce inceleyin.

## İlk kullanım

1. Uygulamayı açın ve Ayarlar → AI modelleri bölümünden ihtiyacınız olan modelleri kurun.
2. Bir fotoğraf açın; silmek istediğiniz bölgeyi seçim fırçasıyla işaretleyin.
3. Nesne silme veya büyütme yöntemini seçip önizlemeyi oluşturun.
4. Sonucu inceleyip Uygula veya Vazgeç'i seçin; PNG ya da proje olarak kaydedin.

Model dosyaları uygulama paketine dahil değildir. İndirme internet gerektirir; kurulumdan sonra görüntü işleme yereldir. Modeller arka planda hazırlanırken görsel açma, çizim, OpenCV ve Lanczos kullanılabilir. AI yalnız ilgili model hazır olduğunda etkinleşir. SDXL ve Swin2SR bu sürümde kullanıma açık değildir.

## Modeller ve gizlilik

İndirmelerde boyut ve SHA-256 doğrulanır. Kalıcı model deposu varsayılan olarak `~/Library/Caches/PixelMend/models/` altındadır. Core ML uygun olduğunda kullanılabilir; tüm işlemlerin GPU'da çalıştığına dair bir garanti yoktur.

Test kiti sonuçları otomatik göndermez. Bir hata bildirirken kişisel fotoğraflarınızı veya parolalarınızı paylaşmayın.

## Kaynaktan geliştirme

Yayınlanan uygulamayı derlemek için ilgili Release etiketiyle aynı kaynak sürümünü kullanın. `apps/desktop` altında:

```sh
corepack pnpm install --frozen-lockfile
corepack pnpm test
corepack pnpm build
corepack pnpm test:ci-tools
```

Python motoru için `engine` altında `uv sync --all-groups --locked` ve `uv run pytest -q` çalıştırın. Yerel imzasız Mac paketi için `apps/desktop` altında `corepack pnpm package:mac` kullanın; bu geliştirme komutu imzalı Release üretmez.

Uygulama `apps/desktop`, motor `engine/src`, testler `apps/desktop/e2e` ve `engine/tests` altındadır. Model export araçları `tools/model-export`, benchmark araçları `engine/bench` içindedir.

## Lisans

Kaynak kod [Apache-2.0](LICENSE) lisanslıdır. Bağımlılıklar ve model lisansları ayrıca geçerlidir: [üçüncü taraf bildirimleri](THIRD_PARTY_NOTICES.md).

## Türkçe komutla üretim — 1.1.0-alpha.1

Yazıyla Düzenle seçili alana komutla nesne ekler veya değiştirir; Yazıyla Oluştur
fotoğraf açmadan yeni görsel üretir. Türkçe komutlar ayrı yerel OPUS-MT çeviri
modeliyle hazırlanır; İngilizce karşılığı gelişmiş bölümden düzeltebilirsiniz.
Görsel modeli FLUX.2 Klein distilled 4B'nin MLX 4-bit paketidir.

Bu özellik macOS 15+, Apple Silicon ve en az 16 GB RAM ister. Her profil ayrıca
cihaz sınıfında kalite ve kaynak kabulünü geçmelidir; kabul edilmemiş profil
başlatılmaz. Kullanılabilir bellek işlem başında yeniden kontrol edilir. Modelin
kurulu olması profil kabulü veya her Mac'te çalışma garantisi değildir.

İlk kurulumda Ayarlar → Modeller'den doğrulanmış Klein ve OPUS-MT paket
klasörlerini seçin. Paket boyutu ve SHA-256 dosya listesi kurulum sırasında
kontrol edilir. Üretken paketlerin varsayılan yeri Application Support altındaki
uygulama model-paket dizinidir; mevcut ONNX önbelleği taşınmaz. Paket yayın
adresleri hazırlanıp doğrulanmadan otomatik indirme sunulmaz.

Kurulumdan sonra işlemler çevrim dışıdır; fotoğraf ve komutlar sunucuya
aktarılmaz, çalışma sırasında otomatik model indirilmez. Çeviri ve görsel
süreçleri sırayla çalışır ve her iş sonunda kapanır. Komutlar yalnız açıkça
kaydettiğiniz yerel `.pixelmend` projesine eklenir; PNG'ye komut yazılmaz.

Manuel kontrol:

1. İki modeli Ayarlar'dan kurun.
2. İnterneti kapatıp uygulamayı yeniden açın.
3. Fotoğrafta alan seçip “buraya turuncu bir kedi ekle” yazın.
4. Önizlemede bir kez Vazgeç, sonra yeniden üretip Uygula seçin.
5. Geri al/Yinele ile fotoğraf, boyama ve seçimin geri döndüğünü kontrol edin.
6. Bir üretimi İptal edip uygulamanın yeniden kullanılabildiğini kontrol edin.
7. Yazıyla Oluştur'da yeni görsel üretip Düzenleyicide Aç seçin.
8. PNG ve proje kaydedip projeyi yeniden açın.

Yeni görseller opak sRGB'dir. Düzenlemede alfa ve seçim dışı pikseller korunur;
tamamen şeffaf boşluğa yeni opak nesne eklenmez. Ayrıntı çalışma çözünürlüğüyle
sınırlıdır; kaynak boyutuna birleştirme doğrudan 4K üretim anlamına gelmez.

Kaynak geliştiriciler için gömülü çalışma paketi ve imzalama hazırlığı:
[Mac alpha paketleme](tools/generative/README.md).
