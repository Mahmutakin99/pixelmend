# Mimari

## Genel şema ve güven sınırı

```text
┌───────────────────────────────────────────────────────────┐
│ Electron main (güvenilen aracı)                           │
│ · sidecar spawn / token / health / shutdown               │
│ · dar ve doğrulanan IPC API                               │
│ · authenticated HTTP + SSE istemcisi                      │
│ · native dosya diyalogları + kontrollü pixelmend: protocol│
└───────────────┬───────────────────────┬───────────────────┘
                │ contextBridge IPC     │ token'lı HTTP/SSE
┌───────────────▼─────────────────┐ ┌───▼───────────────────┐
│ Renderer: React + TypeScript    │ │ Python sidecar        │
│ · dosya/mask UI                 │ │ FastAPI + PyInstaller │
│ · sonuç grid/slider             │ │ · image I/O           │
│ · ayarlar/model UI              │ │ · job queue/storage   │
│ Port, token, path veya Node yok │ │ · ONNX/OpenCV         │
└─────────────────────────────────┘ │ · opsiyonel ağır motor│
                                    └───────────────────────┘
```

Renderer sidecar'a doğrudan bağlanmaz. Port ve oturum token'ı yalnız Electron main'de kalır. Preload genel amaçlı ağ/dosya sistemi API'si değil, görev bazlı dar metotlar sunar. Bu sınır, renderer içeriği bozulsa bile sidecar'ın kolayca genel yerel servis gibi kullanılmasını önler.

## Neden Electron ↔ Python sidecar

ONNX Runtime'ın Node binding'i olsa da opsiyonel PyTorch ağır motoru Python gerektirir. Görsel decode, preprocessing, model çıkarımı ve çıktı encoding'in tek Python sözleşmesinde kalması; renk/maske davranışının algoritmalar arasında ayrışmasını önler. Electron süreç yönetimi, OS entegrasyonu ve UI ile sınırlıdır.

## Tehdit modeli ve sidecar kimlik doğrulaması

- Sidecar yalnız `127.0.0.1` üzerinde dinler; `0.0.0.0` kullanılmaz. Port `0` ile sidecar tarafından seçilip kontrollü başlangıç mesajıyla main'e bildirilir.
- Main her oturumda en az 256-bit token üretir, log/CLI yerine env ile sidecar'a aktarır ve bütün isteklerde header olarak kullanır.
- Prod'da `/health` dahil tüm endpoint'ler token ister. Token yoksa sidecar başlamaz; auth ancak açık `--insecure-dev` veya test token'ıyla geliştirme modunda devre dışı bırakılabilir.
- Permissive CORS eklenmez. `Origin` içeren istekleri ve loopback dışı `Host` değerlerini reddetmek ek savunmadır; token'ın yerini tutmaz.
- Renderer token/port almaz. Main SSE'yi tüketir, payload şemasını doğrular ve renderer'a yalnız gerekli alanları IPC ile yollar.
- Token env aktarımı; web sayfalarını, renderer'ı ve rastlantısal localhost istemcilerini sınırlamak içindir. Aynı kullanıcı hesabında çalışan zararlı yazılıma karşı tam izolasyon vaadi değildir. Bu tehdit kapsama alınırsa Unix domain socket / Windows named pipe ve OS ACL ayrı ADR gerektirir.

## Süreç yaşam döngüsü

1. Electron main token üretir ve sidecar'ı platforma özel PyInstaller binary'sinden başlatır; geliştirmede açık dev komutu kullanılır.
2. Sidecar loopback portunu bildirir; main token'lı `/health` cevabını timeout içinde bekler.
3. Renderer yalnız preload'daki görev API'leriyle main'e istek yapar. Main sender frame/origin ve payload şemasını doğrular.
4. Normal kapanış: yeni job alımı durur, bekleyen işler iptal edilir, aktif ORT işine termination gönderilir, worker/executor grace süresince beklenir.
5. Grace süresi aşılırsa main platforma özgü process-tree sonlandırmasını son çare olarak uygular. Zombi process/thread testle kontrol edilir.

## Job ve sonuç akışı

1. Kullanıcı dosya seçer; main dosyayı authenticated `POST /assets` ile sidecar'a gönderir. Merkezi image I/O orientation/renk/alfa normalizasyonunu yapar ve `{asset_id, width, height, warnings}` döndürür.
2. Main normalize edilmiş önizlemeyi authenticated `GET /assets/{asset_id}/preview` ile alır ve renderer'a yalnız allowlist'li `pixelmend://asset/<opaque-id>` üzerinden sunar. Ham path veya sidecar URL'si renderer'a çıkmaz.
3. Renderer maskeyi bildirilen normalize piksel boyutunda/orijinal koordinatlarda üretir. Main `asset_id`, maske ve algoritma seçimlerini authenticated `POST /jobs` ile yollar; sidecar `{job_id}` döndürür.
4. Sidecar aynı iş türündeki algoritmaları tek inference kuyruğunda sırayla işler.
5. Main `/jobs/{id}/events` SSE akışını tüketir. Heartbeat, result, warning/error ve tam bir terminal event şemalıdır.
6. Result event'i mutlak path veya localhost URL değil opaque `result_id` taşır.
7. Main sonucu authenticated `GET /jobs/{job_id}/results/{result_id}` ile alır. Renderer'a allowlist'li `pixelmend://result/<opaque-id>` protokolü üzerinden sunar; handler keyfî URL/path proxy etmez.
8. `POST /jobs/{id}/cancel` bekleyen veya çalışan işi idempotent biçimde iptal eder ve tam bir terminal `cancelled` event'i üretir. `DELETE /jobs/{id}` bundan ayrı olarak yalnız terminal job artefaktlarını temizler.
9. Kaydetme main'in native diyaloğu üzerinden olur. Editör kapanırken terminal job'lar ve artık kullanılmayan asset kendi opaque id'leriyle dispose edilir.

## Job kuyruğu ve event loop

Inference ve görsel pipeline çağrıları senkrondur. Bunları doğrudan asyncio task'ında çalıştırmak event loop'u inference boyunca bloke eder; health, heartbeat, cancel ve yeni istekler cevap veremez.

- `asyncio.Queue` + tek consumer normal job sıralılığını sağlar.
- Decode/preprocess, adapter `run`, blend ve output encode dahil bütün senkron pipeline FastAPI lifespan'a bağlı `ThreadPoolExecutor(max_workers=1)` üzerinde `run_in_executor` ile çalışır.
- Tek executor thread'i, async bekleyici iptal edilse fakat native çağrı sürse bile yeni inference'ın paralel başlamamasını sağlar.
- Async future cancellation çalışan thread'i kendiliğinden durdurmaz. ORT per-run `RunOptions.terminate` ile durdurulmaya çalışılır; OpenCV gibi preemption API'si olmayan iş tamamlanır fakat iptal edilen sonuç yayımlanmaz.
- Cancel durum geçişi tek yerde tutulur: bekleyen iş `queued → cancelled`, aktif iş `running → cancelling → cancelled`. Aynı cancel isteği güvenle tekrarlanabilir; result ile terminal cancelled event aynı iş için birlikte yayımlanmaz.

## Görsel I/O sözleşmesi

Tüm adapter'lar dosyayı kendileri açmaz; merkezi `imageio.py` kullanır.

```text
load(source) -> ImageAsset(
  rgb: ndarray[H,W,3] uint8,      # renk yönetimli sRGB çalışma alanı
  alpha: ndarray[H,W] uint8 | None,
  metadata: Metadata,
  warnings: list[Warning]
)
```

- EXIF orientation decode sırasında uygulanır; UI, maske ve inference normalize edilmiş aynı piksel koordinatında çalışır.
- Geçerli gömülü ICC profilinden sRGB'ye LittleCMS/Pillow ImageCms ile dönüştürülür. Pikseli dönüştürmeden profili kopyalamak yasaktır.
- Profilsiz RGB sRGB varsayılır. CMYK, 16-bit/HDR ve çok-frame giriş dönüşümü sessiz olmaz; warning üretir.
- Alfa inference öncesi ayrılır ve sonuçta geri eklenir; adapter'lar daima üç kanallı RGB görür.
- Decode bombası/piksel-frame-metadata limitleri kaldırılmaz.
- v1 giriş formatları JPEG/PNG/WebP/TIFF'tir. HEIF/HEIC v1 dışındadır ve ayrı ADR ile codec/provenance incelemesi olmadan dependency lock'a girmez.
- Kaydetme, çıktı formatına uygun sRGB ICC ve normalize orientation üretir. Diğer EXIF/GPS/thumbnail alanlarının korunması gizlilik ve tutarlılık kararıdır; Faz 2'den önce kilitlenir.

## Maske sözleşmesi

Canonical inference maskesi:

- Görselle aynı `H×W` boyutunda, tek kanallı `uint8`.
- `255` = silinecek/doldurulacak alan; `0` = korunacak alan.
- Adapter'a girmeden yalnız `0/255` içerir. UI'ın anti-aliased stroke görünümü canonical maskeden ayrıdır; export 127 eşiği veya doğrudan binary rasterizasyonla normalize edilir.
- Resize/crop/pad sırasında maske için nearest-neighbor kullanılır; ara gri değer üretilmez.
- Feather/yumuşak geçiş canonical inference maskesinin anlamını değiştirmez. Gerekirse adapter blend adımında ayrı bir float alpha maskesi türetilir.

Bu sözleşme OpenCV, LaMa ve gelecekteki adapter'ların ters maske yorumlamasını engeller.

## Execution Provider seçimi

| Platform | v1 aday paket/backend | Karar yöntemi |
|---|---|---|
| macOS arm64 | `onnxruntime`; CoreML → CPU veya yalnız CPU | Model bazlı doğruluk + cold/warm benchmark + placement tanısı |
| Windows x64 | DirectML/Windows ML adayı + CPU | Faz 4 spike/ADR; seçili adapter ve gerçek cihazda test |
| Linux x64 | CPU; opsiyonel ayrı CUDA yolu | Driver/paket boyutu/gerçek CUDA benchmark'ı |

`get_available_providers()` yalnız ORT build'inde EP'nin bulunduğunu söyler; modelin orada çalıştığını göstermez. Model+EP session probe, çıktı toleransı ve end-to-end ölçüm ayrı tutulur. Graph partition CPU fallback'i ile Python wrapper runtime fallback'i aynı mekanizma değildir.

CPU her durumda güvenli fallback'tir; fakat sessiz performans iddiası yapılmaz. Provider seçimi model hash'i, ORT/OS sürümü, provider options ve cache durumuyla benchmark'a bağlanır.

## Tier ve admission modeli

Tier tek bir RAM veya “etkin bellek” formülünden hesaplanmaz.

1. Capabilities: host RAM total/available; seçili adapter; `dedicated/shared/unified/unknown`; varsa device budget/headroom; EP discovery; model session probe; kısa latency kalibrasyonu.
2. Algoritma manifesti: minimum host RAM; varsa minimum device budget; desteklenen/doğrulanmış backend; ölçülmüş peak değerler; kabul edilen latency sınıfı.
3. Algoritma ancak bağımsız gereksinimlerin tümünü karşılarsa varsayılan açılır. Tier bu uygunluk kümesinin sade kullanıcı etiketidir.
4. Sabit profil ilk öneriyi; anlık available/budget her job öncesi admission guard'ı belirler. Ölçülemeyen değer `unknown` kalır.

## LaMa ONNX — kanonik artefakt sabit 512×512

Faz 1 artefaktı `Carve/LaMa-ONNX/lama_fp32.onnx`: opset 17, Apache-2.0, sabit image `N×3×512×512` ve mask `N×1×512×512`; SHA-256 `1faef5301d78db7dda502fe59966957ec4b79dd64e16f03ed96913c7a4eb68d6`.

1. Model indirme sonrası SHA ve session input shape fail-fast doğrulanır.
2. Maskenin bounding box'ı bulunur, çevresine bağlam eklenir.
3. Dikdörtgen alan doğrudan kareye esnetilmez; kare ROI veya letterbox/padding ile 512×512 hazırlanır.
4. Çıktı unpad edilir, ROI boyutuna döndürülür ve yalnız işlenen bölge mask-aware feather blend ile orijinale birleştirilir.

Dinamik LaMa export'u v1 kapsamı dışındadır; farklı graph ve FFT/dynamic-padding doğrulaması gerektirir.

## Tiling — Real-ESRGAN

Yüksek çözünürlüklü görsel tek seferde modele verilmez. Tile boyutu ve overlap model/cihaz manifest parametresidir. Karolar ağırlıklı birleştirilir; tile sınırı kalite golden'ı ve 4000×3000 stress benchmark'ıyla doğrulanır. Host RSS ve device memory ayrı ölçülür.

## GFPGAN kapsamı

GFPGAN garanti edilen hafif motorun veya v1'in parçası değildir. Yüz tespiti, landmark/hizalama, yüz başına çıkarım, ParseNet/soft-mask paste-back ve çoklu yüz akışı; resmî hazır uçtan uca ONNX artefakt eksikliği ve third-party NC/SA/provenance belirsizlikleri nedeniyle Faz 3 belgesindeki ayrı fizibilite/lisans kapısına bağlıdır.

## Model deposu ve bütünlük

- Tek sahip sidecar'dır. Varsayılan: `platformdirs.user_cache_path("PixelMend", appauthor=False) / "models"`; `PIXELMEND_MODELS_DIR` yalnız açık override.
- Renderer/Electron model path'i üretmez. Listeleme, boyut, download ve delete model id/revision üzerinden sidecar API'sidir.
- Manifest: repo id, immutable revision, filename, lisans, byte boyutu ve SHA-256.
- Download geçici dosyaya yapılır; doğrulamadan sonra atomik etkinleştirilir. Model dosyaları git'e girmez.
- Faz 1, LaMa için bu bütünlük ve atomik edinim çekirdeğini kurar; Faz 3 Real-ESRGAN aynı çekirdeği kullanır. Faz 4 bunun üzerine progress/retry/resume, revision görünürlüğü, kullanıcı seçimi ve güvenli silme UX'ini ekler.

## Geçici sonuç yaşam döngüsü

- Sidecar açılışında OS temp altında rastgele, kullanıcıya özel session root; asset ve job başına ayrı alt dizin.
- Dışarı yalnız opaque id çıkar; istemci yolu okuma/silme hedefi olarak gönderemez.
- Bir asset birden çok job tarafından kullanılabilir. `DELETE /assets/{id}` aktif job referansı varken reddedilir; editör kapandığında artık kullanılmayan normalize source/preview temizlenir.
- `POST /jobs/{id}/cancel` çalışma durumunu değiştirir; `DELETE /jobs/{id}` yalnız terminal job artefaktlarını temizler. Normal shutdown bütün session'ı temizler.
- Crash/SIGKILL kalıntıları sonraki açılışta TTL + aktiflik kontrolüyle temizlenir. Silme yalnız doğrulanmış PixelMend temp root altında yapılır; toplam disk kotası uygulanır.

## Benchmark ve regresyon sözleşmesi

- Fixture, mask ve model dosyalarının SHA-256 değeri bütünlük kanıtıdır.
- Output canonical raw RGB SHA-256 yalnız fingerprint'tir; EP/encoder/floating-point farklarında kalite kapısı değildir.
- Regresyon; algoritma/backend'e özgü toleranslı pixel/quality metrikleri ve insan onaylı golden baseline ile değerlendirilir.
- Ham timestamp'li koşular local/CI artefaktıdır; onaylı baseline'lar sürümlenir. Süre, session creation/cold/warm olarak; bellek host RSS/device olarak ayrı tutulur.
