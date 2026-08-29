# Plan İnceleme Kararları — 2026-08-28

Bu belge, `/Users/gladius/Desktop/pixelmend-plan-inceleme-2026-08-28.md` içindeki önerilerin güncel birincil kaynaklarla doğrulanmış sonucudur. Rapor yararlı bir risk taraması yaptı; ancak önerilen çözümler kanıtlanmadan kopyalanmadı.

## Kodlama sınırı

Bu incelemede uygulama kodu yazılmadı, bağımlılık kurulmadı, paket/build üretilmedi ve `.DS_Store` dahil hiçbir dosya silinmedi. Değişiklikler plan, mimari ve proje çalışma belgeleriyle sınırlıdır.

## Karar özeti

| Madde | Karar | Uygulanan yön |
|---|---|---|
| A1 model yolu | **Değiştirerek kabul** | Tek sahip sidecar; platforma uygun cache yolu ve açık override. Büyük modeller doğrudan Electron `userData` altında tutulmayacak. |
| A2 SD kaynakları | **Değiştirerek kabul** | Güncel repo kimlikleri yazıldı; SD 1.5 kaynağı “resmî ayna” diye tanımlanmadı. Revision ve SHA-256 sabitleme kapısı eklendi. |
| A3 asyncio kuyruğu | **Değiştirerek kabul** | Tüm senkron pipeline'ın tek thread executor'a taşınması planlandı; cancellation ve shutdown sınırları ayrıca tanımlandı. |
| A4 açık kararlar | **Değiştirerek kabul** | Gerçek açık kararlar, son karar tarihleriyle `DURUM.md`'de toplandı. PixelMend adı zaten seçilmiş; ikon Faz 2 engeli değil. Sabit imzalama maliyetleri yazılmadı. |
| A5 GFPGAN | **Değiştirerek kabul** | Tek adapter olmadığı ve lisans/provenance kapıları doğrulandı; GFPGAN v1 kapsamından çıkarıldı. Real-ESRGAN arka plan adımı zorunlu değil, opsiyonel. |
| B1 görsel I/O | **Değiştirerek kabul** | Merkezi I/O sözleşmesi eklendi. ICC'yi yalnız kopyalamak yerine renk yönetimli sRGB çalışma alanı tanımlandı. HEIF hedefi, decoder lisansı çözülene kadar bağımlılık kapısına alındı. |
| B2 sidecar auth | **Değiştirerek kabul** | Token renderer'a verilmeyecek; Electron main dar IPC aracısı olacak. Prod'da `/health` dahil bütün endpoint'ler doğrulanacak. |
| B3 tier hesabı | **Teşhis kabul, formül reddedildi** | RAM ve VRAM tek “etkin bellek” sayısında birleştirilmeyecek. Algoritma bazlı bağımsız host/device/backend/latency uygunluğu kullanılacak. |
| B4 EP doğrulaması | **Değiştirerek kabul** | EP listesi yalnız keşif. CPU/CoreML cold-warm ölçümü, toleranslı çıktı karşılaştırması, tanısal fallback/profiling ve cache durumu eklendi. Sabit `%20` eşiği konmadı. |
| B5 benchmark seti | **Değiştirerek kabul** | Sürümlü fixture/manifest ve ölçüm şeması eklendi. Çıktı hash'i yalnız fingerprint; kalite kapısı toleranslı metrik ve onaylı baseline. Unsplash/Pexels, CC0 sayılmadı. |
| C1 sonuç taşıma | **Değiştirerek kabul** | `result_path` veya renderer'a doğrudan localhost URL yerine opaque `result_id`, authenticated endpoint ve kontrollü Electron protokolü. |
| C2 undo/redo | **Değiştirerek kabul** | Tam-canvas snapshot yerine orijinal görsel koordinatlarında stroke journal + seyrek checkpoint. Hızlı, kesintisiz ve klavye erişilebilir undo/redo sözleşmesi eklendi. |
| C3 macOS Intel | **Sonuç değiştirilerek kabul** | v1 macOS hedefi Apple Silicon. Güncel Intel runner var; asıl engel güncel ONNX Runtime macOS x64 wheel'inin kalkmış olması. |
| C4 maske sözleşmesi | **Kabul** | Tek kanal `uint8`, aynı boyut, `255=işlenecek`, `0=korunacak`, canonical binary maske ve ayrı blend maskesi. |
| C5 çoklu form alanı | **Kabul** | Tek değer teknik hata değildi; çoklu fan-out testi eksikti. Tekrarlı multipart alanı, dedupe/422 davranışı ve terminal event doğrulaması eklendi. |
| C6 `.ai/rules` | **Kabul** | Klasörün otomatik yüklenmediği açıklandı; `CLAUDE.md` ilgili işe başlamadan kuralları doğrudan okutuyor. Vendor-neutral klasör bu aşamada korunuyor. |
| C7 LaMa boyutu | **Kısmen reddedildi** | Runtime shape kontrolü kabul edildi; “seçilen model dinamik olabilir” varsayımı reddedildi. Kanonik artefakt doğrulanmış fixed 512×512. Dikdörtgen ROI esnetilmeyecek. |
| C8 küçük notlar | **Ayrıştırılarak kabul** | Tarih, PyInstaller erken smoke test ve geçici sonuç temizliği kabul. Dinamik localhost CSP zorunluluğu main-proxy nedeniyle reddedildi. `.DS_Store` silme yalnız ilk commit öncesi görev olarak planlandı. |

## Plan içi tutarlılık tamamlamaları

Öneri maddeleri işlendiğinde fazlar arası üç ek sözleşme görünür oldu:

- Renderer ham dosyayı bağımsız decode etmeyeceği için çizimden önce sidecar'ın normalize ettiği görseli opaque `asset_id` ile sunan import/preview yaşam döngüsü tanımlandı.
- UI'daki “iptal” ile “sonuçları temizle” ayrıldı: idempotent cancel endpoint'i işi terminal `cancelled` durumuna getirir; delete yalnız terminal job artefaktlarını temizler.
- Faz 4'teki kullanıcıya dönük model yöneticisinden önce, Faz 1'de manifest/hash/atomik etkinleştirme yapan asgari model deposu kurulur; Faz 3 Real-ESRGAN da bunu kullanır.

## Rapordaki çözümden bilinçli sapmalar

### Model cache

Electron belgeleri `userData` altında büyük dosyaları önermiyor. Model deposunu sidecar çözecek: varsayılan `platformdirs.user_cache_path("PixelMend", appauthor=False) / "models"`; `PIXELMEND_MODELS_DIR` yalnız test, taşınabilir kurulum veya açık özel konum override'ı olacak. Renderer dosya yolunu görmeyecek.

### HEIF/HEIC

HEIF desteği ürün açısından değerli, fakat `pillow-heif` doğrudan bağımlılığa eklenmedi. Projenin kaynak kodu BSD-3-Clause olsa da yayımlanan binary wheel içindeki `x265` nedeniyle wheel lisans bildirimi GPLv2'dir. Decoder-only `pi-heif` daha izinli bir seçenekti ancak 1.4.0 ile sonlandırıldı. Faz 1 bağımlılık kilidinden önce sürdürülebilir, dağıtılabilir decoder yolu karara bağlanacak.

### Renk ve metadata

Bir ICC profilini piksel değerleri dönüştürülmeden çıktıya geri takmak renk doğruluğunu garanti etmez. Adapter sözleşmesi renk yönetimli **sRGB, RGB, uint8** çalışma verisidir. Orientation normalize edilir. ICC/EXIF/GPS/thumbnail saklama politikası, boyuta bağlı alanların güncellenmesi ve gizlilik tercihi Faz 2 kaydetme akışından önce ayrıca karara bağlanacak.

### Tier

Host RAM ve device memory birbirinin alternatifi değildir. Öneri motoru her algoritmanın minimum host belleği, seçili adapter'ın device bütçesi, doğrulanmış EP uyumluluğu ve ölçülmüş latency sınıfını ayrı değerlendirir. Ölçülemeyen değer `unknown` kalır; uydurma sayıya çevrilmez.

### Sonuç güven sınırı

Renderer genel bir `request(url)` API'si, sidecar portu veya token almaz. Main süreç sidecar SSE akışını tüketir, olay şemasını doğrular ve yalnız görev bazlı IPC yayınlar. Sonuç görseli kontrollü bir `pixelmend:` protokolü üzerinden opaque kimlikle sunulur.

### Benchmark

Fixture ve model dosyalarının SHA-256 değerleri bütünlük kanıtıdır. Çıktının canonical raw RGB SHA-256 değeri yalnız iz sürme fingerprint'idir. Farklı EP'lerdeki kayan nokta farkları nedeniyle regresyon kararı toleranslı piksel/kalite metrikleri ve insan onaylı baseline ile verilir. Ham tarihli sonuçlar CI/local artefaktı; yalnız onaylı baseline'lar repoya girer.

## Başlıca birincil kaynaklar

- Electron süreç ve güvenlik: [Security](https://www.electronjs.org/docs/latest/tutorial/security), [Context Isolation](https://www.electronjs.org/docs/latest/tutorial/context-isolation), [`app.getPath`](https://www.electronjs.org/docs/latest/api/app/), [Protocol API](https://www.electronjs.org/docs/latest/api/protocol/)
- Python concurrency: [`run_in_executor`](https://docs.python.org/3.12/library/asyncio-eventloop.html#asyncio.loop.run_in_executor), [Executor shutdown/cancellation](https://docs.python.org/3.12/library/concurrent.futures.html#concurrent.futures.Executor.shutdown), [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)
- ONNX Runtime: [Execution Providers](https://onnxruntime.ai/docs/execution-providers/), [CoreML EP](https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html), [profiling](https://onnxruntime.ai/docs/performance/tune-performance/profiling-tools.html), [`RunOptions.terminate`](https://onnxruntime.ai/docs/api/python/api_summary.html#onnxruntime.RunOptions.terminate)
- Görsel I/O: [Pillow EXIF transpose](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html#PIL.ImageOps.exif_transpose), [Pillow ICC/save seçenekleri](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html), [pillow-heif metadata](https://pillow-heif.readthedocs.io/en/stable/pillow-plugin.html), [pillow-heif bundled licenses](https://github.com/bigcat88/pillow_heif/blob/master/LICENSES_bundled.txt)
- Maske/canvas: [OpenCV inpaint maskesi](https://docs.opencv.org/4.x/d7/d8b/group__photo__inpaint.html), [Canvas `ImageData` bellek düzeni](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Pixel_manipulation_with_canvas)
- Modeller: [Carve LaMa ONNX](https://huggingface.co/Carve/LaMa-ONNX), [GFPGAN LICENSE](https://github.com/TencentARC/GFPGAN/blob/master/LICENSE), [GFPGAN pipeline](https://github.com/TencentARC/GFPGAN/blob/master/gfpgan/utils.py), [SD 1.5 Inpainting](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting), [SDXL Inpainting](https://huggingface.co/diffusers/stable-diffusion-xl-1.0-inpainting-0.1)
- Paketleme/dağıtım: [GitHub runner images](https://github.com/actions/runner-images), [macOS 26 runners](https://github.blog/changelog/2026-02-26-macos-26-is-now-generally-available-for-github-hosted-runners/), [PyInstaller platform builds](https://pyinstaller.org/en/stable/usage.html#supporting-multiple-operating-systems), [Microsoft SmartScreen](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation), [Apple Developer ID](https://developer.apple.com/support/developer-id/)
- Claude Code rules: [Project memory and `.claude/rules`](https://code.claude.com/docs/en/memory)

Kaynaklar 2026-08-28 tarihinde doğrulandı. Model, runner, signing ve binary dependency bilgileri hareketli olduğu için ilgili faz başında revision/sürüm düzeyinde yeniden doğrulanacaktır.
