# DURUM — PixelMend

Son güncelleme: 2026-09-15

## Şu an neredeyiz

**Faz 1 — Hafif/headless motor** başladı. Faz 0 M4 kurulumu tamamlandı; kullanıcı 2026-08-29 tarihinde açık kodlama onayı verdi. Repo üst lisansı Apache-2.0 olarak seçildi, HEIF/HEIC v1 kapsamından çıkarıldı.

Python motorunda normalize image I/O, model bütünlüğü, token korumalı asset/health/capabilities API, sıralı job kuyruğu, SSE replay, iptal, sonuç export ve sonuçtan asset oluşturma mevcut. OpenCV, LaMa CPU ve Lanczos adaptörleri eklendi. RealESRGAN_x4plus için model yaşam döngüsü, tiled ONNX adapter, 200 MP kaynak/çıktı politikası ve masaüstü Performans ayarları uygulandı. Public, immutable ONNX artefaktı ve lisanslı benchmark fixture seti henüz yayımlanmadığından AI seçeneği kullanılabilir değildir; Lanczos güvenli fallback olarak kalır.

## Sıradaki işler — 2026-09-14 kararı

1. **AI kalite artırma:** İlk ürün adayı RealESRGAN_x4plus'ın yerel altyapısı tamamlandı. Sıradaki dış kapılar public immutable ONNX yayını (revision, byte, SHA-256, lisans) ve CC0/public-domain 12 fotoğraflık M4 benchmarkıdır. Ayrıntılı araştırma: `docs/ai-upscale-arastirmasi-2026-09-14.md`.
2. **Windows/Linux:** Platforma özgü engine ikilileri, paketleme ve gerçek makine inference doğrulaması olmadan paylaşılabilir paket ilan edilmeyecek.
3. **Üretken doldurma:** SD 1.5 / SDXL ayrı ağır runtime olarak, lisans onayı ve bellek/iptal korumalarıyla ele alınacak.
4. **İleri kalite adayları:** SwinIR ve HAT benchmark sonrası; SUPIR ticari lisans ve ağır bağımlılıklar nedeniyle v1 dışındadır.

Kolaydan zora, bağımlılık kapılarıyla sıralanmış nihai ürün yol haritası: `docs/superpowers/specs/2026-09-15-product-completion-roadmap-design.md`.

## Ortam

- **Bu klasörün oluşturulduğu makine:** MacBook, Apple M1, 8GB RAM, macOS 26.6.1. Sadece planlama/doküman üretimi için kullanıldı, hiç kurulum yapılmadı.
- **Etkin geliştirme makinesi:** Mac Mini, Apple M4, 16GB unified memory, macOS 26.6 (25G72), arm64.
- **Araçlar:** Node 25.9.0, pnpm 11.24.0, uv 0.11.25, uv-managed CPython 3.12.13, Apple Git 2.50.1.
- **v1 hedef dağıtım platformları:** macOS Apple Silicon (arm64), Windows x64, Linux x64. macOS Intel güncel ONNX Runtime'ın x64 wheel yayımlamaması nedeniyle v1 kapsamı dışında; bkz. `docs/karar-gunlugu.md` madde 11.
- Faz 0 araç doğrulaması tamamlandı. Sistem `python3` komutu macOS Python 3.9.6'yı gösterdiği için proje komutları `uv` üzerinden Python 3.12 kullanır.

## Yapılanlar (tarihli, en yeni üstte)

### 2026-09-15 — RealESRGAN AI upscale altyapısı ve güvenli performans sözleşmesi eklendi

- `realesrgan-x4plus` için immutable-manifest temelli model yöneticisi, token korumalı model API/SSE, indirme iptali, atomik doğrulama, süreçler arası kilit, probe ve kullanım sırasında silmeye karşı lease eklendi. Uygulama açılışındaki cache keşfi yalnız hash/boyut doğrular; runtime yüklemesi yalnız açık probe veya kurulum eyleminde yapılır.
- RealESRGAN_x4plus ONNX adapter'ı dinamik NCHW doğrulaması, 4× doğal ara çıktı sınırı, alfa koruması, iptal/progress ve disk tabanlı feather-blended tile birleştirmesiyle eklendi. Varsayılan sınır çıktı ve AI doğal ara çıktı için 200 MP; sonuç bütçesi 1 GiB, asset deposu 2 GiB'dir. Sınırlar `GET /capabilities` ile masaüstüne taşınır.
- Masaüstünde AI/Lanczos seçimi, model durumu/sağlayıcı probe'u gösteren Ayarlar → Performans ekranı ve dar IPC/SSE proxy eklendi. AI yalnız model gerçekten `ready` ve probe başarılıysa seçilebilir; yayımlanmamış manifest `unavailable` görünür. Çizim yokken kaydetme tam çözünürlüklü native export kullanır; mevcut browser canvas katmanı nedeniyle çizimli 50 MP üzeri export açıkça reddedilir.
- `tools/model-export/` yalıtılmış export/parity kapısını ve `engine/bench/` kaynak lisansı/hash zorunlu benchmark runner'ını içerir. Yerel aday üretildi ve parity geçti, ancak ağırlık/aday ONNX git'e eklenmedi ve public artefakt bilgileri uydurulmadı.
- Doğrulama: `engine/.venv/bin/python -m pytest engine/tests -q -k 'not sidecar_process'` → **107 passed, 1 skipped, 1 deselected** (tek üçüncü taraf TestClient deprecation warning); `apps/desktop` altında `corepack pnpm test` → **16 passed**; `corepack pnpm build` geçti. Sandbox loopback kısıtı nedeniyle sidecar alt-süreç testi bu tam koşudan ayrı tutuldu; önceki yükseltilmiş koşuda geçti.

### 2026-09-15 — Private GitHub kaynak deposu oluşturuldu

- Kaynak depo: [`Mahmutakin99/pixelmend`](https://github.com/Mahmutakin99/pixelmend) (private). `main` temizlenmiş geçmişle push edildi ve `origin/main` izleniyor.
- Eski yerel geçmişte GitHub'ın normal Git dosya boyutu sınırını aşan DMG/ZIP release ikilileri vardı. Profesyonel kaynak depo politikası olarak `release/` tüm `main` geçmişinden çıkarıldı; en büyük erişilebilir kaynak nesnesi artık yaklaşık 108 KiB'dir. Eski geçmiş yalnız yerel `refs/archive/pre-github-cleanup` referansında korunur.
- Gelecek DMG/ZIP/SBOM/manifest yayın paketleri Git nesnesi değil, ilgili GitHub Release'in asset'leri olarak yayımlanacaktır.

### 2026-09-14 — macOS arm64 imzasız release candidate paketlendi

- Electron/React masaüstü kabuğu, sandbox renderer, contextBridge dar API, tokenlı sidecar main-client bağlantısı, pixelmend preview protokolü, mask stroke journal, undo/redo, OpenCV/LaMa/Lanczos başlatma ve save akışlarıyla eklendi.
- PyInstaller `onedir` sidecar üretildi; pakete `extraResources` olarak alındı. Paketli app açılışında Electron main, sandbox renderer ve `Resources/engine/pixelmend-engine` sidecar süreçleri doğrulandı.
- `release/1.0.0-rc.1/` altında DMG, ZIP, SHA256SUMS, SBOM ve build manifest bulunuyor. DMG/ZIP SHA-256 doğrulaması geçti; DMG başarıyla bağlandı/ayrıldı.
- Doğrulama: engine tam koşusu **87 passed, 1 skipped, 1 third-party TestClient deprecation warning**; masaüstü Vitest **2 passed** ve production Vite build geçti. Gerçek LaMa smoke ayrıca önceki koşuda başarılıydı.
- RC imzasızdır; Developer ID/notarization yoktur. Varsayılan Electron ikonu kullanılıyor; Real-ESRGAN ve SD/SDXL runtime/model yöneticisi bu RC'de uygulanmadı. `MANUAL_TEST.md` bu sınırları ve kabul adımlarını içerir.

### 2026-09-14 — Paketli renderer beyaz ekran düzeltmesi

- Vite production çıktısı Electron `file:` URL bağlamında mutlak `/assets/...` yazarak JS bundle'ını filesystem kökünde arıyordu. Bu paketli uygulamada beyaz pencereye neden oldu.
- `apps/desktop/vite.config.ts` ile `base: './'` seçildi; üretim index'i artık `./assets/...` yolunu kullanıyor. Yeni DMG/ZIP oluşturuldu ve `SHA256SUMS` yenilendi.

### 2026-09-14 — Canlı maske geri bildirimi ve görünür işlem hataları

- Fırça pointer-down/move sırasında aktif stroke'u anında overlay'e çiziyor; mask rengi seçilebilir. Silgi, aynı overlay'i pointer hareketiyle anında kaldırıyor.
- Renkli overlay server tarafında varlık eşikleme ile canonical 0/255 maskeye dönüyor; renk seçimi inference maskesinin anlamını değiştirmiyor.
- Açma, iş başlatma, durum sorgusu, iptal, sonuç okuma ve kaydetme artık başarısız HTTP yanıtlarını IPC üzerinden renderer'a hata olarak taşıyor. UI iş kuyruğu, iptal ve kaydetme başarısını veya hatasını canlı durum metniyle gösteriyor.
- Doğrulama: Vitest **3 passed**, TypeScript/Vite production build geçti; job API ve kuyruk regresyonları **4 passed**.

### 2026-09-14 — İş kuyruğu, export ve gerçek sidecar temel akışı

- OpenAPI kapatıldı; Origin/Host sınırı ve bozuk token reddi test edildi. Dört export formatında kaynak EXIF temizliği, ICC, alfa ve JPEG beyaz zemin doğrulandı.
- Tek native worker, sıralı işler, SSE sıra numaralı replay, idempotent iptal ve geç sonuç bastırma eklendi. Native çağrı dönene kadar asset referansı tutuluyor. Sonuçtan yeni asset akışı özgün kaynağı koruyor.
- Asset sayısı/bellek bütçesi, eşzamanlı erişim kilidi ve idle expiry çekirdeği eklendi. Periyodik TTL sürücüsü ve disk tabanlı session depolama henüz bağlanmadı.
- Loopback CLI gerçek alt süreçle başlatılıp token korumalı health ve SIGTERM kapanışı test edildi. Uvicorn kapanıştan sonra SIGTERM'i yeniden yükselttiğinden -15 beklenen çıkış biçimidir.
- LaMa modeli manifest boyut/hash doğrulamasıyla OS cache'e indirildi; CPU session şekilleri gerçek dosyadan incelendi. Gerçek inference smoke testi maskesiz piksellerin birebir korunduğunu doğruladı (2 LaMa testi, 3.32 saniyelik pytest koşusu; benchmark değildir).
- Tam koşu: `PIXELMEND_REAL_MODELS=1 engine/.venv/bin/python -m pytest engine/tests -q` → **88 passed, 1 TestClient deprecation warning**, 4.14 saniye. Tam RC doğrulaması ve performans raporları bekliyor.

### 2026-09-14 — Hafif OpenCV inpainting adaptörleri eklendi

- `engine/src/pixelmend_engine/models/opencv_inpaint.py`, ortak `run(image, mask=None, **params)` imzasıyla Telea ve Navier–Stokes algoritmalarını sunuyor. Girdi RGB `uint8`, maske aynı boyda tek kanallı `uint8` ve yalnız `0/255`; adapter resize veya maske tersleme yapmıyor.
- `opencv-python-headless` ve `onnxruntime`, Faz 1 bağımlılık sözleşmesine göre lock'a eklendi. Bu adımda model ağırlığı indirilmedi veya cache'e alınmadı.
- TDD kanıtı: adapter testleri başlangıçta eksik modülle RED verdi; ardından iki algoritmanın yalnız maskeli pikseli değiştirmesi ve yanlış maskeyi reddetmesi GREEN oldu. Tam koşu: `cd engine && uv lock --check && uv run python -m pytest -q` → **73 passed, 1 third-party TestClient deprecation warning**.

### 2026-09-14 — Ölçülebilir capabilities ve token korumalı sağlık uçları eklendi

- `engine/src/pixelmend_engine/capabilities.py`, host toplam/kullanılabilir RAM, CPU sayısı ve ORT'nin kuruluysa bildirdiği execution provider listesini topluyor. Accelerator kimliği, budget ve headroom ölçülemiyorsa tahmin edilmiyor; `unknown`/`null` olarak kalıyor.
- `GET /health` ve `GET /capabilities` sidecar'ın diğer üretim uçları gibi oturum token'ı istiyor. Yeni testler token yokken 401'i, doğrulanmış isteklerde sağlık yanıtını ve ölçülen capability şemasını kapsıyor.
- TDD kanıtı: yeni capability testi önce eksik modülle RED verdi; implementation sonrası GREEN. Tam koşu: `cd engine && uv lock --check && uv run python -m pytest -q` → **70 passed, 1 third-party TestClient deprecation warning**.

### 2026-09-14 — Token korumalı session asset import sınırı eklendi

- `engine/src/pixelmend_engine/assets.py`, normalize edilmiş `ImageAsset` değerini ve yalnız sRGB PNG önizlemesini işlem-içi, opaque UUID altında saklıyor. Asset kaynak dosya adı veya yolu hiçbir API tipine alınmıyor; aktif job referansı varken silme `AssetInUseError` ile reddediliyor.
- `engine/src/pixelmend_engine/auth.py` sabit-zamanlı karşılaştırmalı, en az 256-bit token doğrulaması ekliyor. `engine/src/pixelmend_engine/main.py` bu doğrulamayı `POST /assets`, `GET /assets/{id}/preview` ve `DELETE /assets/{id}` uçlarına uyguluyor; açık CORS veya dokümantasyon ucu yayınlamıyor.
- `engine/tests/test_assets.py` ve `engine/tests/test_main.py` önce eksik modül nedeniyle RED verdi; ardından opaque import/alpha preview, aktif referans koruması, 401 token reddi, dosya adı gizliliği ve PNG preview davranışı GREEN oldu.
- Python ortamı, Pillow `_imaging` içe aktarımını `SIGKILL (137)` ile sonlandıran uv CPython 3.12.14 yerine proje kaydındaki CPython 3.12.13 ile yeniden kuruldu. Tam doğrulama: `cd engine && uv lock --check && uv run python -m pytest -q` → **68 passed, 1 third-party TestClient deprecation warning**.

### 2026-08-29 — Merkezi, renk yönetimli görsel I/O eklendi

- `engine/src/pixelmend_engine/imageio.py`, JPEG/PNG/WebP/TIFF girdilerini orientation uygulanmış, C-contiguous sRGB `RGB uint8` varlığa dönüştürüyor; RGBA/LA/palet alfa kanalını ayrı tutuyor ve normalize preview PNG'de geri birleştiriyor.
- Geçerli gömülü ICC profilleri LittleCMS ile gerçek piksel dönüşümünden geçiriliyor. Bozuk ICC, CMYK, 16-bit ve çok kareli kaynaklar makinece okunabilir warning üretiyor; ton eşleme politikası olmayan `I/F` HDR modları açıkça reddediliyor.
- Seek edilebilir akış sınırı ile 256 MiB kaynak, 50 milyon piksel, 256 kare ve 4 MiB metadata limitleri eklendi. Pillow decompression-bomb uyarıları domain hatasına yükseltiliyor; GIF/BMP/HEIF ile bozuk veya truncated girdiler allowlist sınırında reddediliyor.
- `encode_preview_png`, yalnız normalize sRGB ICC ve alfa taşıyor; kaynak EXIF/GPS/thumbnail verisini preview'e yeniden eklemiyor. Ham kaynak EXIF'i, Faz 2 metadata politikası kararlaştırılana kadar yalnız dahili provenance olarak tutuluyor.
- `engine/pyproject.toml` ve `engine/uv.lock` içine NumPy 2.5.2 ile Pillow 12.3.0 eklendi. Programatik fixture kullanan `engine/tests/test_imageio.py` TDD ile orientation, ICC, alfa, derinlik, çok-kare, format ve güvenlik sınırlarını kapsıyor; ilgili koşu **27 passed**, son tam `uv run --offline pytest -q` koşusu **65 passed** sonucunu verdi ve `uv lock --check` başarılıdır.

### 2026-08-29 — Atomik model edinimi ve süreçler arası kilit eklendi

- `engine/src/pixelmend_engine/model_store.py` artık modeli `model_id/revision/filename` altında çözüyor; Hugging Face'e yalnız immutable manifest koordinatlarıyla ve tokensız bağlanıyor.
- İndirme hedefle aynı dosya sistemindeki izole staging klasörüne yapılıyor. Boyut ve SHA-256 doğrulamasından sonra `os.replace` ile etkinleşiyor; eksik/bozuk aday, taşıma hatası veya aktivasyon hatası staging'i temizliyor ve doğrulanmamış yol döndürmüyor.
- Hedefe özel `FileLock`, eşzamanlı süreç/iş parçacıklarının aynı modeli paralel indirmesini engelliyor. Geçerli cache yeniden kullanılıyor; bozuk cache yalnız doğrulanmış adayla değiştiriliyor.
- `engine/pyproject.toml` ve `engine/uv.lock` içine `huggingface-hub` 1.29.0 ile `filelock` 3.32.4 eklendi. Testlerde sahte downloader kullanıldı; gerçek LaMa ağırlığı indirilmedi.
- `engine/tests/test_model_store.py` TDD ile genişletildi. Path traversal, sabit Hub koordinatları, cache, staging, boyut/hash, taşıma/aktivasyon hatası ve eşzamanlı edinim senaryolarının ilgili koşusu **36 passed**; son tam `uv run --offline pytest -v` sonucu **38 passed** ve `uv lock --check` başarılıdır.

### 2026-08-29 — Kanonik LaMa manifesti immutable revision ile kilitlendi

- Hugging Face birincil kayıtlarından `Carve/LaMa-ONNX/lama_fp32.onnx` için revision `a3ee2fca54baebec351b8fa7786154ffa7555aa6`, `208044816` byte boyutu, Apache-2.0 model kartı ve mevcut SHA-256 doğrulandı.
- `engine/src/pixelmend_engine/model_store.py` içine bu değerleri taşıyan değişmez `LAMA_ONNX_MANIFEST` eklendi; hareketli `main` kullanılmıyor.
- `engine/tests/test_model_store.py` içindeki yeni test önce sabit bulunmadığı için beklenen RED sonucunu verdi; minimal uygulama sonrası ilgili dosyada **20 passed**, son tam `uv run --offline pytest -v` koşusunda **22 passed** sonucu alındı.
- `docs/faz-1-hafif-motor.md` ile `docs/modeller-ve-lisanslar.md` doğrulanmış revision ve byte boyutuyla güncellendi. Model ağırlığı indirilmedi ve yeni bağımlılık kurulmadı.

### 2026-08-29 — Push çalışma anlaşması kaydedildi

- Kontrol öncesinde yerel `main` dalının son commit'i `45dea06 docs: record commit workflow authorization` idi; `git remote -v` çıktısı boş olduğundan henüz push atılmamıştır ve tanımlı uzak depo yoktur.
- Kullanıcı, gün sonunda açıkça istediğinde veya zorlu bir görev doğrulanıp commit edildikten sonra push atılmasına izin verdi. Sıradan ara adımlar otomatik push edilmeyecek; tag ve release ayrıca açık izin gerektirmeye devam edecek.
- Çalışma anlaşması `CLAUDE.md` ve `AI_AJANI_DEVIR_BELGESI.md` içine işlendi. Bu yalnız dokümantasyon değişikliğidir; kod/test davranışı değişmedi.

### 2026-08-29 — Model manifesti ve çevrimdışı bütünlük çekirdeği eklendi

- `engine/src/pixelmend_engine/model_store.py` içine değişmez `ModelManifest` ve manifest doğrulaması eklendi. Hareketli revision, path bileşenli filename, boş kimlik/lisans alanı, pozitif olmayan boyut ve canonical olmayan SHA-256 reddediliyor.
- Model dosyası doğrulaması eksik dosya, byte boyutu uyuşmazlığı ve SHA-256 uyuşmazlığını ayrı domain hatalarıyla bildiriyor; hash büyük ağırlıkları belleğe almadan parçalı okunuyor.
- `engine/tests/test_model_store.py` TDD ile yazıldı. Manifest ve dosya API'leri önce beklenen RED sonuçlarını verdi; refactor ve runtime tip sınırı kontrolü sonrası tam `uv run --offline pytest -v` sonucu: **21 passed**.
- Gerçek LaMa manifesti, indirme, atomik etkinleştirme ve eşzamanlı edinim kilidi henüz eklenmedi; model ağırlığı indirilmedi ve yeni bağımlılık kurulmadı.
- Kullanıcı tamamlanan ve doğrulanan işlerin commit edilmesine izin verdi. İlk proje commit'i: `4c5a1c3 feat: initialize PixelMend engine foundation`.

### 2026-08-29 — Faz 0 tamamlandı, Faz 1'in ilk TDD dilimi başladı

- Kullanıcı açık kodlama onayı verdi; repo üst lisansı Apache-2.0 seçildi ve standart `LICENSE` dosyası eklendi.
- HEIF/HEIC v1 kapsamından çıkarıldı; v1 girişleri JPEG, PNG, WebP ve TIFF olarak kilitlendi. Üçüncü parti/model/native binary lisans takibi ayrı kalmaya devam ediyor.
- M4/16GB ortamı ve araç sürümleri doğrulandı; eksik pnpm 11.24.0 Homebrew ile kuruldu.
- `engine/pyproject.toml`, `engine/uv.lock` ve paket omurgası oluşturuldu; bu ilk dilimde yalnız `platformdirs` ve test bağımlılıkları kuruldu.
- `engine/tests/test_paths.py` önce iki beklenen başarısız testle çalıştırıldı; ardından `engine/src/pixelmend_engine/paths.py` eklendi. `uv run --offline pytest tests/test_paths.py -v` sonucu: **2 passed**.
- Model indirilmedi, build alınmadı, proje dosyası silinmedi ve commit atılmadı.

### 2026-08-29 — Codex ve Claude Code için ayrıntılı devir belgesi hazırlandı

- Proje başka bilgisayara taşındığında eski sohbet geçmişi olmadan devralınabilsin diye `AI_AJANI_DEVIR_BELGESI.md` oluşturuldu.
- Belgede ürün amacı, yerel çalışma vaadi, Electron main–renderer–Python sidecar güven sınırı, image I/O ve maske sözleşmesi, model/tier/benchmark kararları, UI ve erişilebilirlik yönü, Faz 0–6 sırası, lisans riskleri, açık kararlar ve yeni ajanın başlangıç protokolü bir araya getirildi.
- Belgenin açıklayıcı olduğu; canlı durum için bu dosyanın, çalışma kuralları için `CLAUDE.md` ve `.ai/rules/`, kalıcı kararlar için ADR belgelerinin yetkili kaldığı açıklandı.
- Kod, bağımlılık, model, build, commit veya dış işlem yapılmadı; Faz 0/1 bekleme sınırı değişmedi.

### 2026-08-28 — Plan inceleme raporu araştırıldı ve kararlar plana işlendi

- `/Users/gladius/Desktop/pixelmend-plan-inceleme-2026-08-28.md` içindeki A1-C8 önerileri güncel birincil kaynaklarla kontrol edildi.
- Kabul/değiştirerek kabul/reddet gerekçeleri `docs/plan-inceleme-kararlari-2026-08-28.md` içinde kayda alındı.
- Model yolu ve güvenli edinim, normalize asset import/preview, image I/O ve maske sözleşmesi, sidecar güven sınırı, bloklamayan kuyruk/iptal, ölçüme dayalı tier, benchmark, sonuç taşıma ve geçici dosya yaşam döngüsü planları hizalandı.
- GFPGAN v1 kapsamından; macOS Intel de güncel ONNX Runtime x64 dağıtımı bulunmadığı için v1 platform hedeflerinden çıkarıldı.
- Uygulama kodu yazılmadı, bağımlılık kurulmadı, build/paket üretilmedi ve dosya temizliği yapılmadı.

### 2026-08-13 — Proje planlandı, Faz 0 iskeleti oluşturuldu
- Sohbet boyunca (bkz. plan dosyası: `~/.claude/plans/evet-masa-st-ne-gerekli-ara-t-rmalar-compressed-reef.md`) şu kararlar netleşti:
  - Çıkarım motoru: **hibrit ONNX Runtime (paketli, hafif/orta tier) + opsiyonel PyTorch (ağır tier, ayrıca indirilir)**.
  - Masaüstü kabuğu: **Electron + Vite + React + TS** (Rust/Tauri değil — bu makinede Node var, Rust yok).
  - IOPaint (Apache-2.0, arşivlenmiş) **referans** olarak kullanılacak, fork edilmeyecek.
  - İlk tier taslağı: Hafif (8GB, ONNX) / Orta (16GB, ONNX) / Yüksek (24GB, ONNX) / Maksimum (32GB+, PyTorch+SD). **Bu RAM-only taslak 2026-08-28'de karar 10 ile değiştirildi;** ağır tier'lerin varsayılan kapalı olması korundu.
- Klasör yapısı oluşturuldu: `docs/`, `.ai/rules/`, `engine/src/pixelmend_engine/models/`, `engine/tests/`, `apps/desktop/electron/`, `apps/desktop/src/`.
- Dokümantasyon yazıldı: bu dosya, `README.md`, `CLAUDE.md`, `docs/mimari.md`, `docs/karar-gunlugu.md`, `docs/modeller-ve-lisanslar.md`, `docs/faz-0-kurulum.md` (M4 kurulum adımları).
- Henüz **hiç kod yazılmadı** — engine/ ve apps/desktop/ klasörleri şimdilik boş, sadece iskelet.
- `git init` yapıldı, ilk commit atılmadı (kullanıcı onayı gerekiyor — bkz. CLAUDE.md commit kuralı).

## Sırada ne var

1. Session-scoped asset deposunu ve `POST /assets` + normalize preview yaşam döngüsünü `imageio.py` üzerinde test-first kur.
2. Opaque `asset_id`, boyut/warning yanıtı, aktif job referansı ve güvenli dispose/TTL sınırlarını kilitle.
3. Her anlamlı adımda bu dosyayı doğrulama kanıtıyla güncelle; diğer açık kararları tabloda belirtilen son noktadan önce sonuçlandır.

## Açık kararlar / takıldığımız yerler

| Karar | Son karar noktası | Mevcut durum |
|---|---|---|
| Yayıncı kimliği ve reverse-DNS `appId` | Faz 2'deki ilk paketli smoke build'den önce | Açık. Ürün adı **PixelMend**, paket adı `pixelmend` olarak kararlı. |
| Çıktı metadata politikası: EXIF/GPS/thumbnail koruma veya temizleme | Faz 2 kaydetme akışından önce | Açık. Orientation normalizasyonu ve renk yönetimli sRGB zorunlu; gizlilik tercihi ayrıca kararlaştırılacak. |
| macOS dağıtım kimliği | İlk imzalı beta öncesi | Apple Developer Program üyeliği, Developer ID, hardened runtime, notarization ve sidecar imzalama kararı açık; geliştirmeyi bloklamaz. |
| Windows dağıtım/imzalama yolu | İlk genel Windows betası öncesi | Microsoft Store / Artifact Signing / CA sertifikası seçenekleri açık. İmza SmartScreen uyarısını ilk günden kesin kaldırmaz. |
| Yayın ikonu | Faz 6 release candidate öncesi | Açık; Faz 2'yi bloklamaz, geçici ikon kullanılabilir. |

## Kalıcı kararlar

Detaylı gerekçeler için bkz. `docs/karar-gunlugu.md`. Özet:
1. Hibrit ONNX + opsiyonel PyTorch motor.
2. Electron kabuk.
3. IOPaint referans, fork değil.
4. Hiç dış API yok — tamamen yerel çalışma.
5. Tier sistemi: ağır algoritmalar varsayılan kapalı, kullanıcı elle açar; öneri yalnız RAM'e değil algoritma bazlı doğrulanmış uygunluğa dayanır.
6. Renderer sidecar'a doğrudan bağlanmaz; Electron main authenticated aracı ve güven sınırıdır.
7. Model depolamasının sahibi sidecar'dır; varsayılan dizin platform cache alanıdır, ortam değişkeni yalnız açık override olarak kullanılır.
8. Tüm algoritmalar merkezi, renk yönetimli image I/O ile tek maske sözleşmesini kullanır: `uint8`, `0=koru`, `255=işle`.
9. GFPGAN v1 dışında; lisans/provenance ve uçtan uca pipeline kapısı çözülmeden ürün kapsamına girmez.
10. v1 macOS hedefi yalnız Apple Silicon'dur.
11. Repo üst lisansı Apache-2.0'dır; üçüncü parti bileşen lisanslarının yerine geçmez.
12. HEIF/HEIC v1 kapsamı dışındadır; v1 girişleri JPEG, PNG, WebP ve TIFF'tir.
## 2026-09-14 — Sil / Yinele / LaMa / Lanczos hata düzeltmesi

Bu kayıt yalnız aşağıdaki akışların doğrulamasıdır; bütün 1.0 yayın planının tamamlandığı anlamına gelmez.

- Gerçek Electron penceresinde eski hata yeniden üretildi: `invalid job or mask`. Canvas RGBA PNG gönderirken API gri tonlu maske bekliyordu. API artık RGBA/LA alfa kanalını ikili seçim maskesine dönüştürüyor; maske rengi işlemi etkilemiyor.
- İş durumu artık kuyruk mesajının arkasında kalmıyor; sonuç boyutu ve güvenli motor hata mesajları gösteriliyor. Kaydetme sonuç kimliğini koruyor. Kaynak/maske ve sonuç ayrı görüntüleniyor; sonuç üzerinde yanlışlıkla özgün kaynağı işlemek önleniyor.
- Yinele yalnız geri alınmış çizim varsa etkin. Canlı tek nokta boya/silgi, geri al/yinele gerçek canvas pikselleriyle kontrol edildi.
- `PIXELMEND_REAL_MODELS=1 engine/.venv/bin/python -m pytest engine/tests -q`: 91 geçti (bir Starlette bağımlılık deprecation uyarısı). Vitest: 3 geçti. TypeScript/Vite build başarılı.
- PyInstaller motoru yeniden üretildi; `electron-builder --mac dir --arm64` ile paket oluşturuldu. Gerçek paket üzerinde `e2e/editor.cjs`: açma, canlı boya/silgi, undo/redo, OpenCV, kurulu LaMa, Lanczos 96×64 → 192×128, gerçek PNG kaydı, LaMa iptali ve önceki sonuç korunması geçti. Yalnız native dosya seçicilerin seçimi otomatikleştiriliyor; motor/inference taklit edilmiyor.
- Kanıt ekran görüntüleri: `apps/desktop/test-results/packaged/{opencv-result,lama-result,lanczos-result}.png` (yerel, git dışında). Lanczos ekranında sonuç ölçüsü ve Kaydet etkinliği incelendi.
- Güncel imzasız test uygulaması: `apps/desktop/out/mac-arm64/PixelMend.app`. Önceki `release/1.0.0-rc.1` DMG/ZIP güncellenmedi. Varsayılan Electron ikonu ve aynı sürüm numarası sürüyor; bu paket genel yayın değildir.
- Paket komutu artık motoru da yeniden derliyor; Vite çıktısı ile Electron paket dizini ayrıldı, eski sidecar'ın yanlışlıkla paketlenmesi önlendi.
- Sınırlar: Lanczos özgün kaynağı büyütür; sonuçtan devam eden düzenleme henüz yok. Kaydet düğmesi PNG içindir. Büyük görsel performansı, tam model yönetimi, SD/SDXL ve tüm manuel kabul senaryoları bu düzeltmeyle doğrulanmış sayılmaz.
## 2026-09-14 — Silgi ve işlem düğmeleri düzeltmesi

- Boya ve seçim silgileri artık tam alfa ile kaldırıyor; eski düşük opaklıklı silgi stroke'ları da yeniden çizimde aynı davranışı kullanıyor. Seçim verisi tam opak, yarı saydam görünüm yalnız CSS kaplamasında.
- Renderer'ın `operation` alanı Electron'da LaMa/1× veya Lanczos/2× parametrelerine çevriliyor. Önceki köprü `algorithms` beklediğinden her iki düğme de hatalı istek gönderiyordu.
- Başlatma, kuyruk, işleme, iptal bekleme, önizleme ve hata durumları görünür. Başlatma isteği beklenirken çift iş gönderimi engelleniyor; geri alma dahil belge değişiklikleri işlem sırasında kilitleniyor. İşleme kaynağı geçmişteki güncel fotoğraf kimliğinden alınıyor.
- E2E sırasında çıkan `Tainted canvases may not be exported` kaydetme hatası, yalnız kayıtlı asset kimliğine izin veren yerel PNG aktarımıyla giderildi.
- Doğrulama: TypeScript/Vite build, 7 Vitest testi ve gerçek `out/mac-arm64/PixelMend.app` üzerinde `e2e/editor.cjs` başarıyla tamamlandı (exit 0 ve PASS çıktısı). İki silgide pointerup sonrası sıfır alfa, seçimde geri alma, işlem kutusu, düğme kilidi, gerçek LaMa önizleme/vazgeç/uygula, PNG kaydı ve 96×64 → 192×128 büyütme doğrulandı. Kanıtlar `apps/desktop/test-results/current-fixes/` altında.
## Kurulum konumu ve eski çıktı temizliği — 2026-09-14

Güncel uygulama `/Applications/PixelMend.app` konumuna taşındı ve buradan çalıştığı süreç listesinde doğrulandı. Spotlight sorgusu yalnız bu konumu döndürdü. Kullanıcı uygulamayı Spotlight'tan açıyor; sonraki güncellemeler de aynı kurulum konumuna uygulanmalı.

Yeni paketleme çıktıları `apps/desktop/out.noindex/` altında üretilecek; geliştirme paketlerinin Spotlight'a ayrı uygulama olarak girmemesi amaçlanıyor. Test paketleri doğrulandıktan sonra Applications kopyası güncellenmeli; açık ve kaydedilmemiş çalışma varsa zorla kapatılmamalı.

Kullanıcının isteğiyle eski `release/1.0.0-rc.1/` kurulum paketi ve manifestleri, `apps/desktop/test-results/`, `engine/build/`, `:memory:.ses` ve `apps/desktop/out/builder-debug.yml` Çöp Sepeti'ne taşındı. Eski sürüm dosyaları ayrıca Git geçmişinden geri alınabilir. Önceki kayıtlarda geçen yerel test ekran görüntüsü yolları artık mevcut değildir; test kodları korunmuştur.
