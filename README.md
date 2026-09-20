# PixelMend

Bu Mac üzerinde fotoğrafları yerel olarak düzenleyen Electron uygulaması. Görseller dış servislere gönderilmez.

- **Nesne silme:** varsayılan AI — LaMa veya açıkça seçilen Hızlı — OpenCV. LaMa hazır değilse Ayarlar → Modeller üzerinden kurulum/sınama gerekir; sessiz yöntem değişikliği yapılmaz.
- **Büyütme:** RealESRGAN x4plus AI veya Lanczos; 2×, 4× ve özel ölçü. AI önce doğal 4× çıktı üretir. Sonuç önizlemesini uygulayabilir veya vazgeçebilirsiniz.
- **Düzenleme:** çizim, seçim ve silgiler, geri al/yinele, zoom, sonuçtan devam, PNG kaydı ve `.pixelmend` projesi.
- **Modeller:** SHA-256 ve boyut doğrulanır; kullanım boyunca kilit tutulur. Bu teslimde CPU kullanılır. LaMa sabit yayımlanmış kaynaktan indirilir; RealESRGAN uygulamanın sabit manifestine uyan yerel ONNX dosyasından kurulur.

Bu teslim yalnız macOS Apple Silicon üzerindeki mevcut Mac'i kapsar. Genel imzalı dağıtım, Windows/Linux kabulü ve üretken doldurma kapsam dışıdır. Güncel doğrulama ve sınırlar: [Mac kabul raporu](docs/verification/mac-acceptance.md), [durum](DURUM.md).

## Model deposu

Varsayılan kalıcı konum `~/Library/Caches/PixelMend/models/<model>/<revision>/`.
`PIXELMEND_MODELS_DIR` yalnız açık geliştirme/test override'ıdır. Her açılışta bütünlük ve gerçek CPU sınaması tekrar yapılır. Model dosyaları projeye veya Git'e eklenmez.

Yerel RealESRGAN export aracı `tools/model-export/export.py`; kaynak ağırlık, lisans, export ortamı ve PyTorch/ONNX eşdeğerliği [provenance kaydında](docs/verification/realesrgan-export.json). Ayarlar → Modeller → Yerel ONNX kur, dosyayı atomik olarak model deposuna kopyalar. Başka hash'e sahip ONNX dosyaları kabul edilmez.

## Geliştirme ve doğrulama

```sh
cd apps/desktop
corepack pnpm test
corepack pnpm build
corepack pnpm test:ci-tools
```

Zorunlu gerçek model kabulü (iki model kurulu olmalıdır; atlanan test başarı değildir):

```sh
PIXELMEND_REAL_MODELS=1 engine/.venv/bin/python -m pytest engine/tests -q
```

Paketleme: `apps/desktop` altında `corepack pnpm package:mac`. Paketli GUI testleri `e2e/editor.cjs` ve `e2e/models.cjs`; `PIXELMEND_E2E_APP` uygulamanın `Contents/MacOS/PixelMend` yoludur. İkinci testte `PIXELMEND_E2E_FRESH=1` temiz model deposuna kurulum ve yeniden açılışı da doğrular.

## Klasörler

| Yol | Amaç |
|---|---|
| `apps/desktop/src`, `electron` | Arayüz ve güvenli yerel motor köprüsü |
| `apps/desktop/e2e`, `engine/tests` | Gerçek uygulama ve motor regresyonları |
| `engine/src` | Görsel, model, kuyruk ve kaynak sınırı kodu |
| `engine/bench` | Fotoğraf benchmark araçları; yerel fixture pikselleri Git dışında |
| `tools/model-export` | Yalıtılmış model export ortamı ve kaynak/lisans doğrulaması |
| `docs/verification` | Manifestler, ölçümler ve kabul raporu |
| `apps/desktop/test-results` | Yerel ekran görüntüleri ve karşılaştırma PNG'leri; Git dışında |
| `node_modules`, `.venv` | Geliştirme/paketleme bağımlılıkları |
| `dist`, `build`, `out.noindex` | Yeniden üretilebilir derleme/paket çıktıları |
| `.git`, `.github`, `.ai` | Geçmiş, CI ve proje çalışma kuralları |

Proje Apache-2.0 lisanslıdır. Model ve üçüncü taraf lisansları ayrıca geçerlidir: [model lisansları](docs/modeller-ve-lisanslar.md).
