# PixelMend

Fotoğraf düzenleme, nesne silme ve görsel büyütme için yerel masaüstü uygulaması.
Görselleriniz işlenmek için dış servislere gönderilmez.

## Uygulamayı indirme

Mac Apple Silicon paketleri [Releases](https://github.com/Mahmutakin99/pixelmend/releases) bölümündedir. DMG'yi açıp PixelMend'i Applications klasörüne sürükleyin; ZIP aynı uygulamanın alternatifidir. Bir sürümün desteklediği platformlar ve modeller kendi Release açıklamasında belirtilir.

Yeni Mac dağıtımı Intel Mac, Windows veya Linux paketi içermez. RC sürümleri
ön sürümdür; AI çıktısını kaydetmeden önce inceleyin. Eski paketler farklı
özelliklere ve imza durumuna sahip olabilir.

Homebrew ile Alpha4 kurulumu (Apple Silicon, macOS 15+):

```sh
brew install --cask Mahmutakin99/pixelmend/pixelmend
```

Paket [PixelMend Homebrew tap](https://github.com/Mahmutakin99/homebrew-pixelmend)
üzerinden indirilir ve SHA-256 doğrulanır. Homebrew, Developer ID Application
imzalı ve Apple tarafından notarize edilmiş Alpha4 ZIP'ini kullanır. Önerilen
imzalı DMG/ZIP bağlantıları ve mevcut elle kurulumdan Homebrew'a geçiş adımları
[Alpha4 sürüm notlarındadır](https://github.com/Mahmutakin99/pixelmend/releases/tag/v1.1.0-alpha.4).

## İlk kullanım

1. Bir fotoğraf açın.
2. Silmek istediğiniz bölgeyi seçim fırçasıyla işaretleyin veya büyütme yöntemini seçin.
3. Sonucu önizleyin; uygun bulursanız uygulayıp PNG/proje olarak kaydedin.

Modeller uygulama paketinden ayrı indirilir. İndirme internet gerektirir;
kurulumdan sonra görüntü işleme yereldir. Hata bildirirken kişisel fotoğraf,
parola veya özel anahtar paylaşmayın.

## Kaynaktan geliştirme

İndirdiğiniz uygulamanın kaynağı, ilgili Release'in sürüm etiketidir.
Varsayılan dal ile yayımlanan ön sürüm aynı kodu içermeyebilir; derlemeden
önce istediğiniz sürüm etiketini seçin.

`apps/desktop` altında:

```sh
corepack pnpm install --frozen-lockfile
corepack pnpm test
corepack pnpm build
```

Python motoru için `engine` altında `uv sync --all-groups --locked` ve
`uv run pytest -q` çalıştırın. Yerel paketleme komutları geliştirme çıktısıdır;
imzalı dağıtım için ayrıca Developer ID ve Apple notarizasyonu gerekir.

## Lisans

Kaynak kod [Apache-2.0](LICENSE) lisanslıdır. Model ve bağımlılık lisansları
ayrıca geçerlidir: [üçüncü taraf bildirimleri](THIRD_PARTY_NOTICES.md).
