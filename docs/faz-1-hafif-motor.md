# Faz 1 — Hafif Motor, Headless

Amaç: UI olmadan, CLI/curl ile güvenilir ve ölçülebilir nesne silme akışı çalışıyor olsun. Bu faz yalnız “model sonuç verdi”yi değil; görsel yönü/rengi, event loop sağlığı, model bütünlüğü, geçici dosya yaşam döngüsü ve aynı girdide tekrar edilebilir benchmark altyapısını da kurar.

## Faz kapıları

- [x] Repo üst lisansı Apache-2.0 olarak, HEIF/HEIC ise v1 kapsamı dışında bırakılarak karara bağlandı.
- [x] Faz 0 kurulumu M4 üzerinde tamamlandı; gerçek sürümler `DURUM.md` → Ortam'a yazıldı.
- [x] Uygulama koduna geçme onayı kullanıcı tarafından 2026-08-29 tarihinde açıkça verildi.

## Görevler

- [ ] `engine/pyproject.toml`: Python 3.12 + `uv`; başlangıç bağımlılıkları `fastapi`, `uvicorn`, `python-multipart`, `onnxruntime`, `opencv-python-headless`, `numpy`, `pillow`, `psutil`, `platformdirs`, `huggingface_hub`, `pytest`, `httpx`.
  - HEIF/HEIC v1 kapsamı dışındadır; decoder bağımlılığı eklenmez.
- [x] `paths.py`: model deposunu tek yerden çözer.
  - Varsayılan: `platformdirs.user_cache_path("PixelMend", appauthor=False) / "models"`.
  - `PIXELMEND_MODELS_DIR` yalnız test, taşınabilir kurulum veya kullanıcının açıkça seçtiği özel konum için override'dır.
  - Electron ve renderer model dosyalarına doğrudan dokunmaz; model listeleme/boyut/silme sidecar API'sinden yapılır.
- [ ] `model_store.py`: Faz 4'teki tam model yöneticisinden önce gereken asgari güvenli edinim çekirdeği.
  - [x] Genel manifest; model/repo kimliği, immutable revision, güvenli filename, beklenen byte boyutu, SHA-256 ve lisans kaydını doğrular. Çevrimdışı dosya doğrulayıcı eksik dosya, boyut ve hash hatalarını ayırır.
  - [x] Kanonik LaMa manifestini doğrulanmış immutable revision `a3ee2fca54baebec351b8fa7786154ffa7555aa6` ve `208044816` byte boyutuyla kilitle.
  - [ ] İndirmeyi aynı dosya sistemindeki geçici dosyaya yap; boyut+hash doğrulanınca atomik etkinleştir. Kısmi/bozuk dosyayı inference session'ına açma ve eşzamanlı aynı-model edinimini kilitle.
  - Faz 3 Real-ESRGAN aynı çekirdeği kullanır. Progress/retry/resume, revision listesi, kullanıcıya dönük silme ve taşıma UX'i Faz 4'te bu katman genişletilerek eklenir.
- [ ] `imageio.py`: tüm adapter'ların kullandığı merkezi görsel I/O katmanı.
  - Desteklenen v1 girişleri: JPEG, PNG, WebP, TIFF.
  - Decode güvenlik limitleri korunur; aşırı piksel/frame/metadata kaynak tüketimi hata olarak ele alınır.
  - EXIF orientation decode sırasında uygulanır ve orientation etiketi normalize edilir.
  - Gömülü geçerli ICC profilinden renk yönetimli **sRGB** çalışma alanına dönüştürülür; profilsiz RGB giriş sRGB varsayılır. Profil byte'ını dönüştürmeden yeniden takmak renk yönetimi sayılmaz.
  - Adapter girdisi `RGB uint8`; varsa alfa ayrı kanalda korunur ve işlem sonrası geri birleştirilir.
  - CMYK, 16-bit/HDR veya desteklenmeyen çok-frame giriş sessizce indirgenmez; dönüşüm kullanıcıya/istemciye warning olarak döner.
  - Çıktı EXIF/GPS/thumbnail saklama politikası Faz 2'den önce açık karara bağlıdır; Faz 1 testleri en az orientation, sRGB ICC, boyut ve alfa sözleşmesini doğrular.
- [ ] Session-scoped asset deposu ve import API'si:
  - `POST /assets`: multipart `image` alır; merkezi image I/O ile bir kez normalize eder ve `{asset_id, width, height, warnings}` döndürür. Dışarı path çıkmaz.
  - `GET /assets/{asset_id}/preview`: main'e normalize edilmiş, renk yönetimli önizleme byte'larını verir. Sidecar canonical inference asset'ini ayrı tutar; UI bildirilen tam piksel boyutuna koordinat eşler.
  - `DELETE /assets/{asset_id}` yalnız session'a ait opaque id kabul eder ve aktif job referansı varken reddeder. Shutdown/TTL kalıntı temizliği asset'leri de kapsar.
- [ ] `capabilities.py`: donanım profilini tek “etkin bellek” sayısına indirgemeden toplar.
  - Host RAM total/available, CPU çekirdek sayısı.
  - Seçili accelerator/adapter kimliği; bellek türü (`dedicated | shared | unified | unknown`).
  - Mümkünse seçili adapter'ın platforma özgü total/budget/headroom değeri; ölçülemiyorsa `unknown`.
  - ORT build'inde bulunan EP'ler ile **model bazlı session probe sonucu ayrı alanlar**.
  - Tier, algoritma manifestindeki bağımsız minimum host RAM, device budget, backend uyumluluğu ve ölçülmüş latency sınıfından türetilir. Ölçülemeyen kapasite uydurma sayıya çevrilmez.
- [ ] `main.py`: FastAPI app, `GET /health`, `GET /capabilities`.
- [ ] `auth.py`: sidecar güvenlik modu.
  - Prod'da Electron main'in ürettiği en az 256-bit oturum token'ı sabit-zamanlı karşılaştırmayla doğrulanır; `/health` dahil tüm endpoint'ler auth ister.
  - Token yoksa prod sidecar başlamaz. Headless geliştirme yalnız açık `--insecure-dev` modu veya açık test token'ıyla çalışır; auth sessizce kapanmaz.
  - Yalnız `127.0.0.1` dinlenir; permissive CORS eklenmez. `Origin` içeren ve loopback dışı `Host` kullanan istekler ek savunma olarak reddedilir.
- [ ] `models/opencv_inpaint.py`: `cv2.inpaint` Telea + Navier-Stokes adapter'ları, ortak arayüz `run(image: np.ndarray, mask: np.ndarray) -> np.ndarray`.
- [ ] `models/lama_onnx.py`: kanonik LaMa ONNX adapter.
  - Artefakt: `Carve/LaMa-ONNX/lama_fp32.onnx`, opset 17, sabit 512×512, SHA-256 `1faef5301d78db7dda502fe59966957ec4b79dd64e16f03ed96913c7a4eb68d6`.
  - İndirme repo kimliği + revision ile sabitlenir; dosya hash'i ve session input shape sözleşmesi yüklemeden önce/sonra fail-fast doğrulanır.
  - Maske bounding box + bağlam alınır; dikdörtgen ROI doğrudan kareye esnetilmez. Kare ROI veya letterbox/padding → 512×512 → çıkarım → unpad/geri ölçekleme → yalnız işlenen bölgeyi etkileyen mask-aware feather blend akışı kullanılır (bkz. `docs/mimari.md`).
  - Dinamik LaMa export'u v1 kapsamı dışıdır; farklı artefakt olarak ayrıca doğrulanmadan sessizce kullanılmaz.
- [ ] `queue.py`: `asyncio.Queue` + tek consumer; decode/preprocess, inference, blend ve output yazma dahil senkron pipeline, FastAPI lifespan'a bağlı `ThreadPoolExecutor(max_workers=1)` üzerinde `run_in_executor` ile çalışır.
  - Tek consumer sıralılığı; tek executor thread'i async cancellation sonrasında native iş sürerken ikinci inference'ın paralel başlamamasını garanti eder.
  - Async future iptali çalışan native thread'i durdurmaz: kuyruktaki işler iptal edilir; aktif ORT işi per-run `RunOptions.terminate` ile durdurulmaya çalışılır; preemption API'si olmayan OpenCV işi biter fakat iptal edilen sonucu yayımlanmaz.
  - Kapanışta yeni iş alımı durur, bekleyen işler iptal edilir, aktif işe termination gönderilir, worker/executor belirli grace süresince beklenir; süre aşılırsa Electron Faz 2'de sidecar'ı son çare olarak zorla kapatır.
- [ ] `registry.py`: algoritma manifesti — `opencv_telea`, `opencv_ns`, `lama`; id/ad/tür yanında minimum host RAM, opsiyonel device budget, desteklenen/doğrulanmış backend, model revision/hash ve benchmark latency sınıfı.
- [ ] `POST /jobs`: multipart `asset_id`, `mask`, tekrarlı `algorithms: list[str]` → `{job_id}`. Maske asset'in normalize `H×W` boyutuyla eşleşmezse istek reddedilir.
  - Giriş sırası korunur. Yinelenen algoritma id'leri ya sırayı koruyarak dedupe edilir ya açık `422` döner; seçilen davranış testte ve API sözleşmesinde sabitlenir, aynı algoritma sessizce iki kez çalışmaz.
- [ ] `GET /jobs/{id}/events`: authenticated SSE; heartbeat, algoritma sonucu, warning/error ve terminal job event'leri şemalıdır.
  - Sonuç event'i dosya yolu/URL değil opaque kimlik taşır: `{"algorithm": ..., "result_id": ..., "duration_ms": ..., "host_peak_rss_mb": ..., "device_peak_mb": ...}`. Ölçülemeyen bellek alanı `null` olur.
  - Her job tam bir terminal `completed | failed | cancelled` event'i üretir; cancel ile yarışan geç result terminal durumdan sonra yayımlanmaz.
- [ ] `POST /jobs/{id}/cancel`: bekleyen/çalışan işi idempotent biçimde iptal eder. Bekleyen iş çalışmaz; aktif ORT run terminate edilir, preempt edilemeyen işin sonucu atılır; terminal `cancelled` event'i tam bir kez gelir.
- [ ] `GET /jobs/{id}/results/{result_id}` ve `DELETE /jobs/{id}`: yalnız doğrulanmış opaque id ile sonuç okuma ve **terminal** job temizleme; delete iptal yerine kullanılmaz ve istemciden dosya yolu kabul edilmez.
- [ ] Geçici sonuç deposu:
  - Her sidecar açılışında OS temp altında kullanıcıya özel, rastgele session root; her asset ve job için ayrı alt dizin.
  - Normal shutdown bütün session root'u siler. Başlangıçta TTL'yi aşmış ve aktif olmadığı doğrulanan eski PixelMend session dizinleri temizlenir.
  - Silme yalnız doğrulanmış temp root altında yapılır; disk kotası ve path traversal test edilir.
- [ ] `engine/tests/`: en az üç küçük görsel+maske ile adapter, I/O, auth, queue ve lifecycle testleri.
  - Asset import → normalize preview → aynı `asset_id` ile job akışında orientation uygulanmış görselle maskenin aynı koordinat sisteminde kaldığı; Display P3/ICC girişinin kontrollü sRGB dönüşümü; alfa round-trip; CMYK/16-bit warning'i.
  - Maske sözleşmesi: tek kanal `uint8`, aynı boyut, yalnız `0/255`.
  - Yapay yavaş adapter çalışırken `/health` ve SSE heartbeat cevap vermeye devam eder.
  - Cancel endpoint'i yinelendiğinde tek terminal event oluşur; iptal/kapanış sonrası kuyruktaki iş başlamaz, geç result yayımlanmaz, zombi process/thread ve temp sonucu kalmaz.
- [ ] `engine/bench/`: manifest tabanlı, lisansı açık ve sürümlenen 3–4 inpainting fixture'ı + runner.
  - İlk set: küçük leke, büyük nesne, tekstürlü arka plan, düz gradyan/gökyüzü. Real-ESRGAN stres görseli Faz 3'te; ağır motor vakaları Faz 5'te eklenir.
  - Kendi çekilmiş veya açıkça CC0 içerik tercih edilir. Unsplash/Pexels CC0 değildir; kullanılırsa kaynak, indirme tarihi ve özel lisans manifestte tutulur.
  - JSON: git commit; OS/arch; CPU/GPU/adapter/power mode; RAM; Python/ORT/OpenCV sürümleri; provider/options; model revision+SHA; fixture/mask SHA, boyut ve maske oranı; session-create/cold-run/warm median+p95; tekrar sayısı; host peak RSS; varsa kaynağıyla device peak.
  - Fixture/model SHA-256 bütünlük kapısıdır. Canonical raw RGB output SHA-256 yalnız fingerprint'tir; regresyon oracle'ı değildir. Regresyon, backend/algoritma bazlı toleranslı pixel/quality metrikleri ve insan onaylı golden baseline ile değerlendirilir.
  - Ham tarihli local/CI sonuçları artefakttır; yalnız onaylanmış baseline değişiklikleri commit edilir.

## Doğrulama

Komutların kesin biçimi uygulama iskeleti oluşunca kilitlenecek; beklenen akış:

```bash
cd engine
uv sync
uv run pytest
export PIXELMEND_SIDECAR_TOKEN="$(openssl rand -hex 32)"
uv run uvicorn pixelmend_engine.main:app --host 127.0.0.1 --port 8420

curl -H "Authorization: Bearer ${PIXELMEND_SIDECAR_TOKEN}" \
  -F "image=@test.jpg" \
  http://127.0.0.1:8420/assets

PIXELMEND_ASSET_ID=REPLACE_WITH_RETURNED_ASSET_ID
curl -H "Authorization: Bearer ${PIXELMEND_SIDECAR_TOKEN}" \
  -F "asset_id=${PIXELMEND_ASSET_ID}" -F "mask=@mask.png" \
  -F "algorithms=lama" -F "algorithms=opencv_telea" \
  http://127.0.0.1:8420/jobs

curl -N -H "Authorization: Bearer ${PIXELMEND_SIDECAR_TOKEN}" \
  http://127.0.0.1:8420/jobs/REPLACE_WITH_JOB_ID/events
uv run python -m bench
```

Geliştirme auth modu seçildiğinde her komut açık test token'ını/header'ını kullanır; prod davranışı auth'suz test edilmez. Entegrasyon testi iki farklı algoritma sonucu ile tek terminal event geldiğini doğrular.

### M4 Execution Provider doğrulaması

1. `get_available_providers()` ile CoreML EP'nin build'de bulunduğu kaydedilir; bu tek başına kullanım kanıtı değildir.
2. Aynı LaMa hash'i ve aynı tensorlerle yalnız CPU ile CoreML→CPU session'ları ayrı ölçülür. Session creation, ilk run, cache dolu yeni session ve en az beş warm run ayrı raporlanır.
3. CPU/CoreML çıktıları tanımlı toleransla eşdeğer olmalıdır. Profiling/log açık koşular timing'e katılmaz.
4. Normal fallback'li session için verbose placement/profiling artefaktı saklanır. Yalnız tanı amacıyla CPU EP listelenmeden `session.disable_cpu_ep_fallback=1` ile tam graph desteği sınanır.
5. CoreML `ModelCacheDirectory` açıkça belirlenir; macOS 14.4+ ve MLProgram durumunda `ProfileComputePlan=1` ile CoreML içindeki CPU/GPU/ANE dispatch'i incelenir.
6. CoreML ancak doğruluk kontrolünü geçer, representative end-to-end ölçümde gürültünün üzerinde tutarlı kazanç sağlar ve cold/warm bütçelerini karşılar ise varsayılan olur. Eşik ölçümden sonra ADR'ye yazılır; peşinen `%20` dayatılmaz.

Bitince: `DURUM.md` güncellenir, karar/ölçüm kanıtları eklenir; commit yalnız kullanıcı onayıyla atılır ve kutucuklar işaretlenir.
