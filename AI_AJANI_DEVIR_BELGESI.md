# PixelMend — Codex ve Claude Code İçin Ayrıntılı Proje Devir Belgesi

**Hazırlanma tarihi:** 29 Ağustos 2026
**Amaç:** Proje başka bir bilgisayara taşındığında Codex, Claude Code veya başka bir yazılım ajanının eski sohbeti görmeden ürün fikrini, alınan kararları, teknik sınırları, faz sırasını ve açık kapıları doğru anlaması.
**Belge türü:** Açıklayıcı devir özeti. `DURUM.md`, `CLAUDE.md`, `.ai/rules/` ve ADR belgelerinin yerine geçmez.

## 1. Yeni ajan önce ne yapmalı?

1. Proje kökünü doğrula; eski bilgisayardaki mutlak yollara güvenme.
2. `CLAUDE.md` dosyasını oku. Dosya adı Claude'a özgü görünse de içindeki proje kuralları Codex için de geçerlidir.
3. `DURUM.md` dosyasını baştan sona oku. Canlı aşama, açık kararlar ve ilk kesin devam noktası oradadır.
4. Motor veya UI dosyasına dokunmadan önce `.ai/rules/README.md` ve `.ai/rules/` altındaki tüm Markdown dosyalarını açıkça oku. Bu klasör otomatik yüklenmeyebilir.
5. Yapılacak fazın belgesini ve `docs/mimari.md` içindeki ilgili sözleşmeyi oku.
6. `git status` ve mevcut dosyaları incele; kullanıcıya ait değişiklikleri silme veya üstüne yazma.

Kritik durum: Kullanıcı 2026-08-29 tarihinde kodlama onayı verdi ve Faz 1 başladı. Faz sırasını koru; model indirme, build, silme veya commit gibi ayrı kontrollü işlemlerde `DURUM.md` ve kullanıcı talimatlarını izlemeye devam et.

## 2. Projenin mevcut durumu

- PixelMend Faz 1 hafif/headless motor aşamasındadır.
- Python omurgası, `paths.py`, çevrimdışı model manifesti/dosya bütünlüğü çekirdeği ve toplam 21 test vardır; FastAPI, image I/O, adapter, kuyruk ve UI henüz uygulanmamıştır.
- Git deposu başlatılmıştır fakat henüz commit yoktur.
- Belgeler ilk olarak M1/8 GB MacBook üzerinde hazırlanmış, geliştirme M4/16 GB Mac mini'ye taşınmıştır.
- Faz 0 kurulumu tamamlanmış ve gerçek araç sürümleri `DURUM.md` içine yazılmıştır.
- Repo üst lisansı Apache-2.0'dır; HEIF/HEIC v1 kapsamı dışındadır.
- Commit ve silme için kullanıcı onayı gereklidir.

Güncel durum değişebileceği için kesin kaynak her zaman `DURUM.md`dir.

## 3. Ürün fikri

PixelMend, masaüstünde tamamen yerel çalışan bir fotoğraf düzeltme ve karşılaştırma uygulamasıdır.

Kullanıcının temel akışları:

1. Bir fotoğraf açar.
2. Silmek istediği nesne, leke, yazı veya alanı fırçayla maskeler.
3. Bir veya birden fazla inpainting algoritmasını çalıştırır.
4. Sonuçları yan yana ya da karşılaştırmalı biçimde inceler.
5. İstediği sonucu seçip kaydeder.
6. Ayrı bir iş olarak düşük çözünürlüklü görseli klasik veya model tabanlı yöntemlerle büyütebilir.

Ürün tek bir algoritmayı “doğru sonuç” diye dayatmaz. Aynı görselde farklı yöntemler farklı sonuç verebildiği için karşılaştırma deneyimi ürünün temel değeridir.

En önemli ürün vaadi:

- Görseller cihazdan çıkmaz.
- Dış AI/API servisi yoktur.
- İnternet olmadan temel işlevler çalışabilir.
- Uygun olmayan ağır model kullanıcıdan habersiz indirilmez veya çalıştırılmaz.
- Donanım kapasitesi yalnız RAM etiketiyle varsayılmaz; model ve backend gerçekten ölçülür.

## 4. Hedef platformlar

v1 hedefleri:

- macOS Apple Silicon / arm64.
- Windows x64.
- Linux x64.

macOS Intel v1 kapsamında değildir. Bunun nedeni runner eksikliği değil, güncel ONNX Runtime'ın macOS x86_64 wheel yayımlamamasıdır. Intel desteği ileride ayrı bağımlılık, native build ve gerçek cihaz test kararı gerektirir.

## 5. Kesin teknik yığın

### Python çıkarım sidecar'ı

- Python 3.12.
- `uv` ile paket ve ortam yönetimi.
- FastAPI.
- ONNX Runtime varsayılan çıkarım motoru.
- OpenCV ve Pillow tabanlı merkezi görsel I/O.
- Opsiyonel ağır tier için ayrı PyTorch/diffusers ortamı.
- PyInstaller ile platforma özel sidecar paketleme.

### Masaüstü kabuğu

- Electron.
- Vite.
- React.
- TypeScript.
- Node paket yöneticisi `pnpm`.

Tauri/Rust seçilmedi. Electron'un daha büyük bellek ve paket maliyeti kabul edildi; Python sidecar süreç yönetimi, mevcut React/TS deneyimi ve çapraz platform entegrasyonu daha değerli bulundu.

## 6. Ana mimari ve güven sınırı

```text
Renderer: React + TypeScript
  │ yalnız dar, şemalı contextBridge IPC
  ▼
Electron main — güvenilen aracı
  │ token'lı HTTP/SSE, süreç ve dosya kontrolü
  ▼
Python sidecar — FastAPI + görüntü işleme + modeller
```

### Renderer'ın alamayacağı yetkiler

- Sidecar portu.
- Sidecar oturum token'ı.
- Mutlak dosya yolu.
- Genel amaçlı ağ isteği API'si.
- Node veya doğrudan dosya sistemi erişimi.

### Electron main'in görevi

- Her oturumda en az 256-bit rastgele token üretmek.
- Token'ı log veya CLI yerine environment üzerinden sidecar'a vermek.
- Sidecar'ı başlatmak, health kontrolü yapmak ve kontrollü kapatmak.
- Authenticated HTTP/SSE istemcisi olmak.
- Payload ve event şemalarını doğrulamak.
- Native dosya açma/kaydetme diyaloglarını yönetmek.
- Renderer'a yalnız görev bazlı IPC sunmak.
- Görselleri ve sonuçları allowlist'li `pixelmend:` protokolüyle opaque kimlik üzerinden göstermek.

### Sidecar güvenliği

- Yalnız `127.0.0.1` üzerinde dinler; `0.0.0.0` yoktur.
- Port `0` ile seçilebilir; port rastgeleliği güvenlik değil çakışma önlemidir.
- Production'da `/health` dahil her endpoint token ister.
- Token olmadan production sidecar başlamaz.
- Permissive CORS eklenmez.
- Renderer sidecar'a doğrudan bağlanmaz.
- Bu model aynı kullanıcı hesabında çalışan zararlı yazılıma karşı tam işletim sistemi izolasyonu vaat etmez; böyle bir hedef için Unix socket/Windows named pipe ve ACL ayrı ADR ister.

## 7. Asset, job ve sonuç yaşam döngüsü

Planlanan akış:

```text
Native dosya seçimi
  → POST /assets
  → merkezi orientation/renk/alfa normalizasyonu
  → opaque asset_id + boyut + warning
  → kontrollü preview
  → UI aynı normalize piksel koordinatında maske üretir
  → POST /jobs (asset_id + mask + algorithms)
  → sıra tabanlı inference
  → SSE progress/result/error/terminal event
  → opaque result_id
  → kontrollü preview ve native kaydetme
  → dispose / TTL / shutdown temizliği
```

Renderer'a `result_path` veya localhost URL verilmez. Sonuç yalnız authenticated endpoint ve opaque `result_id` ile taşınır.

`cancel` ile `delete` farklıdır:

- `POST /jobs/{id}/cancel`: queued/running işi idempotent olarak terminal `cancelled` durumuna getirir.
- `DELETE /jobs/{id}`: yalnız terminal job artefaktlarını temizler.

Her job tam bir terminal event üretir: `completed`, `failed` veya `cancelled`. İptalden sonra geç result yayınlanamaz.

## 8. Event loop, kuyruk ve iptal yaklaşımı

Görsel decode, preprocessing, ONNX/OpenCV çıkarımı, blend ve encode senkron işlerdir. Bunlar doğrudan FastAPI event loop'unda çalıştırılmaz.

- `asyncio.Queue` ve tek consumer kullanılır.
- Bütün senkron pipeline, lifespan'a bağlı `ThreadPoolExecutor(max_workers=1)` üzerinde çalışır.
- Böylece yavaş inference sırasında health, heartbeat, cancel ve yeni istekler cevap verebilir.
- Async future iptali native işi kendiliğinden durdurmaz.
- ONNX Runtime işi mümkün olduğunda `RunOptions.terminate` ile durdurulur.
- OpenCV gibi preemption sunmayan iş tamamlanabilir; fakat iptal edilmiş sonuç yayınlanmaz.
- Kapanışta yeni iş kabulü durur, bekleyenler iptal edilir, aktif iş sonlandırılmaya çalışılır ve grace süresi sonunda Electron process tree'yi son çare olarak kapatır.

## 9. Merkezi görsel I/O sözleşmesi

Adapter'lar dosyayı kendi başına açmaz. Tüm girişler `imageio.py` üzerinden tek sözleşmeye dönüştürülür:

```text
ImageAsset(
  rgb: H×W×3 uint8, renk yönetimli sRGB,
  alpha: H×W uint8 veya None,
  metadata,
  warnings
)
```

Kurallar:

- EXIF orientation decode sırasında uygulanır.
- Gömülü geçerli ICC profilinden gerçek piksel dönüşümüyle sRGB'ye geçilir.
- Profilsiz RGB, sRGB kabul edilir.
- Alfa inference öncesi ayrılır, sonra geri eklenir.
- CMYK, 16-bit/HDR ve multi-frame dönüşümleri sessiz yapılmaz; warning üretir.
- Decode bombası, aşırı piksel/frame/metadata limitleri korunur.
- İlk formatlar JPEG, PNG, WebP ve TIFF'tir.
- HEIF/HEIC v1 kapsamı dışındadır; ayrı ADR ve codec/provenance incelemesi olmadan dependency lock'a girmez.

Çıktı metadata politikası henüz açıktır: EXIF/GPS/thumbnail korunacak mı temizlenecek mi Faz 2 kaydetme akışından önce kararlaştırılmalıdır. Orientation normalizasyonu ve sRGB davranışı ise kesindir.

## 10. Maske sözleşmesi

Canonical inference maskesi:

- Görselle aynı `H×W` boyutunda.
- Tek kanallı `uint8`.
- Yalnız `0` ve `255` değerleri.
- `255 = işle/sil/doldur`.
- `0 = koru`.

Resize/crop/pad sırasında nearest-neighbor kullanılır. UI'ın anti-aliased fırça görünümü canonical maskeden ayrıdır. Feather gerekiyorsa inference maskesinin anlamı değiştirilmeden blend için ayrı float alpha türetilir.

Bu karar OpenCV, LaMa, Real-ESRGAN ve gelecekteki adapter'ların farklı veya ters maske yorumlamasını engeller.

## 11. Model ve algoritma stratejisi

### Hafif

- OpenCV Telea inpainting.
- OpenCV Navier-Stokes inpainting.
- Klasik Lanczos benzeri resize baseline.
- Model ağırlığı gerektirmeyen, düşük riskli varsayılan yol.

### Orta

- LaMa ONNX.
- Kanonik artefakt: `Carve/LaMa-ONNX/lama_fp32.onnx`.
- Opset 17.
- Sabit 512×512 giriş.
- SHA-256: `1faef5301d78db7dda502fe59966957ec4b79dd64e16f03ed96913c7a4eb68d6`.
- Model hash ve input shape fail-fast doğrulanır.
- Maske bounding box'ı çevresinde bağlamlı ROI alınır.
- Dikdörtgen ROI kareye esnetilmez; kare ROI veya letterbox/pad ile hazırlanır.
- Çıktı unpad ve geri ölçek sonrası yalnız ilgili bölgeye mask-aware feather blend ile birleştirilir.
- Dinamik LaMa export'u v1 kapsamı dışıdır.

### Yüksek

- Real-ESRGAN ile model tabanlı upscale.
- Kesin ONNX graph, immutable revision, hash ve lisans Faz 3 kapısında kilitlenir.
- Büyük görsel tek seferde verilmez; tile + overlap + ağırlıklı birleştirme kullanılır.
- Tile sınırı kalite golden'ı ve 4000×3000 stress benchmark'ıyla test edilir.

### Maksimum

- İsteğe bağlı, ana paketten ayrı PyTorch/diffusers ağır motor.
- Stable Diffusion 1.5 Inpainting.
- SDXL Inpainting 0.1.
- Model ve ağır ortam yalnız açık kullanıcı eylemiyle indirilir.
- Prompt UI yalnız motor kurulu ve donanım uygunluğu doğrulanmışsa görünür.
- Open RAIL lisans linki, kullanım sınırlamaları ve yeniden dağıtım yükümlülükleri kullanıcıya doğru anlatılır.

### GFPGAN

GFPGAN v1 dışında bırakılmıştır. Bunun nedeni yalnız lisans değil; uçtan uca çözümün RetinaFace/landmark, hizalama, yüz başına inference, ParseNet/soft paste-back ve çoklu yüz işleme gerektirmesidir. Resmî desteklenen tek uçtan uca ONNX artefakt yoktur ve third-party lisans/provenance zinciri açık değildir.

GFPGAN ancak ayrı fizibilite ve lisans kapısı geçerse gelecekte değerlendirilebilir. Real-ESRGAN'i yüz iyileştirmenin zorunlu arka plan adımı gibi varsayma.

## 12. Model deposu ve indirme güvenliği

Model dosyalarının tek sahibi sidecar'dır.

Varsayılan konum:

```text
platformdirs.user_cache_path("PixelMend", appauthor=False) / "models"
```

`PIXELMEND_MODELS_DIR` yalnız açık override'dır. Electron veya renderer model yolu üretmez.

Her model manifesti şunları taşır:

- repo kimliği;
- immutable revision/commit;
- kesin filename ve beklenen boyut;
- SHA-256;
- kod/graph/ağırlık/yardımcı model lisansı;
- doğrulanmış backend ve platform.

İndirme geçici dosyaya yapılır; boyut ve hash doğrulanmadan atomik olarak etkinleşmez. Hareketli `main` revision'ına güvenilmez. Ağırlık dosyaları git'e commit edilmez.

## 13. Tier ve donanım uygunluğu

Eski 8/16/24/32 GB tablosu yalnız kaba ürün anlatımıdır; teknik karar değildir. Tier yalnız toplam RAM'e bakılarak seçilmez.

Her algoritma için ayrı değerlendirilir:

- host RAM total/available;
- seçili accelerator/adapter;
- bellek türü: dedicated/shared/unified/unknown;
- ölçülebiliyorsa device budget/headroom;
- ORT build'inde provider bulunması;
- model+provider session probe sonucu;
- çıktı doğruluğu;
- cold/warm latency;
- ölçülmüş peak host/device bellek.

RAM ve VRAM tek “etkin bellek” sayısında birleştirilmez. Ölçülemeyen değer `unknown` kalır. Ağır algoritmalar varsayılan kapalıdır; kullanıcı elle açabilir ama job öncesi admission guard yine uygulanır.

Tier kullanıcıya sade bir özet sunar:

- Hafif.
- Orta.
- Yüksek.
- Maksimum.

Gerçek karar kaynağı algoritma manifesti ve doğrulanmış benchmark'tır.

## 14. Execution Provider yaklaşımı

- macOS arm64: ONNX Runtime, CoreML ve CPU ölçülerek seçilir.
- Windows x64: DirectML/Windows ML adayları Faz 4 spike/ADR ile güncel durumda değerlendirilir.
- Linux x64: CPU varsayılanı; CUDA ayrı paket/driver/boyut kararı ister.

`get_available_providers()` yalnız provider'ın build'de varlığını gösterir; modelin gerçekten orada çalıştığını veya hızlandığını kanıtlamaz.

LaMa için CPU ve CoreML ayrı session'larda aynı tensorlerle karşılaştırılır. Session creation, cold run, cache dolu yeni session, warm median/p95 ve placement/profiling ayrı ölçülür. CoreML ancak doğruluk eşdeğerliği ve gürültünün üstünde tutarlı uçtan uca kazanç gösterirse varsayılan olur. Peşinen yüzde 20 gibi sabit eşik dayatılmaz.

## 15. Benchmark ve regresyon sözleşmesi

- Fixture, maske ve model dosyalarının SHA-256 değeri bütünlük kanıtıdır.
- Çıktının canonical raw RGB SHA-256 değeri yalnız fingerprint'tir; kalite oracle'ı değildir.
- Farklı provider ve floating-point davranışı için toleranslı piksel/kalite ölçüleri ve insan onaylı golden baseline kullanılır.
- Ham tarihli koşular local/CI artefaktıdır.
- Yalnız onaylı baseline'lar sürümlenir.
- Session creation, cold run, warm median/p95 ayrı raporlanır.
- Host RSS ve device memory ayrı ölçülür.
- Benchmark fixture'ı kendi üretilmiş veya açıkça uygun lisanslı olmalıdır. Unsplash/Pexels içerikleri otomatik olarak CC0 sayılmaz.

## 16. Arayüz ve etkileşim yönü

UI henüz kodlanmadı; fakat deneyimin temel davranışı kararlaştırıldı. Global `apple-design` yaklaşımı uygulanmalıdır: anlık geri bildirim, doğrudan manipülasyon, kesilebilir hareket, mekânsal tutarlılık, platforma uyum, erişilebilirlik ve gereksiz süsten kaçınma.

### Ana editör akışı

- Görsel aç.
- Boyut/format/renk/alpha warning'lerini gör.
- Fırça ile boya veya sil.
- Fırça boyutunu ayarla.
- Undo/redo kullan.
- Bir veya birden fazla algoritma seç.
- İş ilerlemesini gör ve iptal edebil.
- Sonuçları grid/slider ile karşılaştır.
- Seçilen sonucu native diyalogla kaydet.

### Canvas davranışı

- Pointer down anında görsel fırça geri bildirimi.
- `setPointerCapture` ile kesintisiz çizim.
- Zoom/pan olsa da stroke'lar normalize orijinal görsel koordinatında tutulur.
- Undo/redo tam 4 kanallı canvas snapshot yığını değildir; stroke journal ve ölçülmüş seyrek tek-kanal checkpoint yaklaşımıdır.
- Standart `Cmd/Ctrl+Z` ve `Cmd/Ctrl+Shift+Z` kısayolları.
- Undo/redo input'u gereksiz yere kilitlemez.
- Yeni stroke redo kolunu öngörülebilir biçimde temizler.
- Fırça, erase, clear, undo ve redo görünür kontroller ve erişilebilir adlara sahiptir.

### Akıcılık ve erişilebilirlik

- Kullanıcının çizgisi işaretçiyle 1:1 hareket eder; gecikmeli hayalet maske hissi oluşmaz.
- İşleme kuyruğu UI'ı kilitlemez.
- Cancel anında görünür duruma geçer; native iş hemen duramasa bile geç sonuç gösterilmez.
- Animasyonlar kullanıcının mevcut görsel durumundan devam edebilmeli ve mümkün olduğunca kesilebilir olmalıdır.
- `prefers-reduced-motion` benzeri tercih için büyük kayma/zoom yerine kısa cross-fade veya statik geçiş kullanılır.
- Sadece renkle anlam verilmez; durumlar metin ve ikonla açıklanır.
- Klavye odağı, erişilebilir adlar ve tam klavye yolu korunur.
- Hata mesajı eyleme dönük olmalıdır: disk dolu, model bozuk, hash uyuşmazlığı, decoder yok, yetersiz bellek veya backend başarısızlığı birbirinden ayrılır.
- Büyük yüzeylerde translucency yalnız hiyerarşi için ve okunabilirlik korunarak kullanılmalıdır; model yönetimi gibi yoğun yüzeylerde gösterişli glass katmanları üst üste yığılmamalıdır.

## 17. Faz planı

### Faz 0 — M4 kurulum ve zemin — tamamlandı 2026-08-29

- M4 üzerinde macOS, RAM, Node, Python ve Git sürümlerini doğrula.
- Python 3.12 ve `uv`.
- `pnpm`/Corepack.
- Gerçek sürümleri `DURUM.md` içine yaz.
- Repo lisansını Apache-2.0 olarak, HEIF/HEIC'i v1 dışında bırakarak karara bağla — tamamlandı.
- Kullanıcıdan açık kodlama onayı al — tamamlandı.
- İlk commit öncesi `.DS_Store` dosyalarını yalnız hedefleri listeleyip kullanıcı onayıyla temizle.

### Faz 1 — Hafif/headless motor

- Python proje omurgası.
- Merkezi paths/model store/image I/O.
- Capabilities.
- Token'lı FastAPI sidecar.
- Asset import/preview.
- OpenCV ve LaMa adapter'ları.
- Queue, SSE, cancel, opaque results ve temp lifecycle.
- Benchmark ve test altyapısı.
- UI olmadan curl/CLI ile doğrulanmış akış.

### Faz 2 — Electron kabuğu ve maskeleme

- Güvenli Electron/Vite/React/TS iskeleti.
- Main–preload–renderer güven sınırı.
- Sidecar spawn/health/shutdown.
- Native dosya aç/kaydet.
- Normalize preview, canvas mask, stroke journal undo/redo.
- Tek algoritmayla uçtan uca “yükle → çiz → sil → kaydet”.
- İlk paketli PyInstaller sidecar smoke.

### Faz 3 — Çoklu algoritma ve karşılaştırma

- OpenCV + LaMa sonuçlarının birlikte çalışması.
- Klasik upscale baseline.
- Real-ESRGAN adapter ve tiling.
- Karşılaştırma grid/slider.
- GFPGAN v1'e eklenmez; yalnız ayrı fizibilite kararı.

### Faz 4 — Tier, ayarlar ve model yöneticisi

- Platform capabilities ve model probe'ları.
- Algoritma bazlı admission/tier.
- Model indirme progress/retry/resume/hash.
- Güvenli model silme/taşıma.
- Backend ve benchmark görünürlüğü.
- Kullanıcı öneriyi değiştirebilir; uygun olmayan yol için açık uyarı.

### Faz 5 — Opsiyonel ağır motor

- Ana paketten ayrı PyTorch/diffusers kurulumu.
- SD 1.5 ve SDXL inpainting.
- Prompt UI.
- Lisans ve model manifesti.
- Kurulum, kaldırma, rollback ve OOM davranışı.
- Ağır motor yokken normal uygulama eksiksiz çalışmaya devam eder.

### Faz 6 — Paketleme ve yayın

- macOS arm64, Windows x64, Linux x64 native build.
- Electron Builder + PyInstaller.
- GitHub Actions platform matrisi.
- İmza/notarization/Windows signing kararları.
- Package SHA, build manifest, dependency/model manifest ve smoke raporu.
- İndirilen gerçek CI artefaktı üzerinde temiz profil smoke.
- THIRD_PARTY_NOTICES, lisanslar, SBOM/provenance imkânı.

Fazlar atlanmaz. Her faz tamamlandığında `DURUM.md`, test kanıtı ve gerekiyorsa ADR güncellenir. Commit yalnız kullanıcı onayıyla atılır.

## 18. Açık kararlar

| Karar | En geç kapanacağı nokta | Durum |
|---|---|---|
| Yayıncı kimliği ve reverse-DNS `appId` | Faz 2 ilk paketli smoke öncesi | Açık |
| EXIF/GPS/thumbnail saklama/temizleme | Faz 2 kaydetme akışı öncesi | Açık |
| macOS Developer ID, hardened runtime, notarization | İlk imzalı beta öncesi | Açık |
| Windows dağıtım/imzalama yolu | İlk genel Windows beta öncesi | Açık |
| Yayın ikonu | Faz 6 release candidate öncesi | Açık |

Ürün adı **PixelMend**, paket adı `pixelmend` olarak kararlıdır.

## 19. Lisans ve dağıtım uyarıları

- Repo üst lisansı üçüncü parti kod, native binary, codec, model graph'ı ve ağırlık lisanslarının yerine geçmez.
- Model ağırlıkları git'e commit edilmez.
- LaMa kaynağı/revision/hash sabitlenir.
- Real-ESRGAN ONNX artefaktı ve ağırlığı Faz 3'te ayrıca lisans/provenance incelemesiyle seçilir.
- `pillow-heif` kaynak lisansı tek başına yeterli değildir; binary wheel içindeki GPL/LGPL bileşenleri değerlendirilmelidir.
- Bakımı biten `pi-heif` otomatik çözüm değildir.
- SD/SDXL Open RAIL koşulları “koşulsuz serbest” diye özetlenemez.
- GFPGAN üst seviye Apache-2.0 ifadesi third-party NC/SA/provenance risklerini otomatik kaldırmaz.
- Her platform paketi kendi işletim sisteminde native oluşturulur; PyInstaller çapraz derleme varsayılmaz.

## 20. Yeni ajan ne yapmamalı?

- Dış API veya bulut inference eklememeli.
- Görseli gizlice üçüncü tarafa göndermemeli.
- Renderer'a sidecar token/port/path vermemeli.
- Renderer'dan doğrudan sidecar bağlantısı kurmamalı.
- Her adapter'ın kendi dosya decode veya maske sözleşmesini yaratmasına izin vermemeli.
- RAM ve VRAM'i tek uydurma sayıda birleştirmemeli.
- `get_available_providers()` sonucunu hızlanma kanıtı saymamalı.
- Modeli hareketli `main` revision'ından doğrulamasız indirmemeli.
- Ağırlık dosyasını repoya veya varsayılan ana pakete gömmemeli.
- GFPGAN'i v1'e sessizce geri sokmamalı.
- Fazları atlamamalı.
- Kullanıcı açık kodlama izni vermeden Faz 0/1 uygulamasına başlamamalı.
- `.DS_Store`, model cache, git geçmişi veya kullanıcı dosyalarını izinsiz silmemeli.
- Kullanıcı izni olmadan commit/tag/release yapmamalı.

## 21. Kaynak belge haritası

| Konu | Asıl kaynak |
|---|---|
| Proje çalışma kuralları | `CLAUDE.md` |
| Canlı durum ve açık kararlar | `DURUM.md` |
| Yaşanmış proje tuzakları | `.ai/rules/README.md` ve aynı klasördeki diğer `.md` dosyaları |
| Mimari ve güven sınırı | `docs/mimari.md` |
| Kalıcı kararlar ve gerekçeleri | `docs/karar-gunlugu.md` |
| Modeller, codec ve lisanslar | `docs/modeller-ve-lisanslar.md` |
| M4 kurulum | `docs/faz-0-kurulum.md` |
| Headless motor | `docs/faz-1-hafif-motor.md` |
| Electron ve maskeleme | `docs/faz-2-electron-kabuk.md` |
| Çoklu algoritma | `docs/faz-3-coklu-algoritma.md` |
| Tier ve model yöneticisi | `docs/faz-4-tier-ayarlar.md` |
| Ağır motor | `docs/faz-5-agir-motor.md` |
| Paketleme/yayın | `docs/faz-6-paketleme.md` |
| 28 Ağustos teknik plan incelemesi | `docs/plan-inceleme-kararlari-2026-08-28.md` |

## 22. Diğer bilgisayarda yeni sohbeti başlatmak için önerilen mesaj

```text
Bu klasör PixelMend projesidir. Önce CLAUDE.md, DURUM.md ve AI_AJANI_DEVIR_BELGESI.md dosyalarını baştan sona oku. Motor veya UI işinden önce .ai/rules/README.md ve aynı klasördeki tüm Markdown kurallarını ayrıca oku. Eski mutlak yollara güvenme. Faz 0 tamamlandı ve Faz 1 başladı; kesin devam noktasını DURUM.md'den al. Repo Apache-2.0'dır, HEIF/HEIC v1 dışındadır. Fazları atlama, model ağırlıklarını commit etme, izinsiz silme/commit yapma ve her anlamlı iş sonunda test kanıtı ile DURUM.md'yi güncelle.
```

## 23. Bu devir belgesinin bakım kuralı

Bu dosya açıklayıcı bir fotoğraftır. Güncel aşama ve ilk devam noktası `DURUM.md` içinde tutulur. Kalıcı teknik karar değişirse `docs/karar-gunlugu.md` güncellenir. Yaşanmış gerçek bir teknik tuzak bulunursa `.ai/rules/` altında ayrı bir kural dosyasına yazılır. Bu toplu devir belgesi yalnız başka makine/ajan için bağlamın yeniden paketlenmesi gerektiğinde veya büyük bir faz değişikliği özeti maddi biçimde eskittiğinde yenilenmelidir.
