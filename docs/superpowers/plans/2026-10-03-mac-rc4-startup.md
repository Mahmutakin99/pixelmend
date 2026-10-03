# Mac rc.4 hızlı açılış uygulama planı

Onaylı konuşma planı: pencere hemen açılır, dört kurulu model arka planda
sırayla doğrulanır/sınanır. AI dışı işler beklemez. Model güvenlik kapıları korunur.
Teknoloji: Electron, React/Vite, Python/FastAPI, ONNX Runtime.

- [x] 1. Motor: hafif keşif, takip edilen sıralı başlangıç görevleri; yarış,
  hata, iptal/kapanış ve HTTP erişilebilirliği regresyonları (RED → GREEN).
- [x] 2. Electron/UI: erken pencere/IPC, motor hazır olma kapısı, hazırlık
  açıklaması ve AI kontrol durumları, paket sürümünden Hakkında bilgisi.
- [x] 3. Tanı: model hazırlığı bitmeden test başlatma; 180 s üst sınır,
  hata ve kısmi raporun korunması. Mevcut E2E beklemelerini güncelle.
- [x] 4. Doğrulama: Python/desktop/CI-tools, native E2E, bağımsız kod incelemesi.
- [x] 5. rc.4 ARM64 DMG/ZIP/test kiti, checksum ve iki smoke; gerçek modellerle
  standart tanı, üç açılış ölçümü (etkileşimli pencere ≤5 s hedefi).
- [x] 6. Uygulama kapalıyken geri alınabilir kurulum, kısa kullanıcı testlerini belgeleyerek teslim.

## Sınırlar

rc.3 kanıtları ve indirilen modeller/profil korunur. Windows/Linux ertelenir.
İmzalama/notarizasyon kapsam dışıdır. rc.4 kapsamlı tanı ve insan görsel
incelemesi gelmeden nihai kalite kabulü beklemededir. Native işler zorla öldürülmez.

## Uygulama kaydı

- Başlangıç: feat/mac-local-ai; mevcut kullanıcı değişiklikleri korunuyor.
- Ruling: plan docs altında tutuluyor; .codex bu oturumda salt-okunur.
- Arayüz ön kontrolü: başlangıç görevleri mevcut ModelView durumlarını kullanır;
  tanı beklemesi aynı durumları tüketir. Yeni dış HTTP/IPC arayüzü gerekmiyor.
- Kurulu rc.3 ölçümü: port 318 ms, sağlık 25.555 ms; dört model ready.
- Model regresyonları önce 2 FAIL (start() sınamayı bekliyor), sonra 14 PASS.
- Pencere/IPC regresyonları önce 2 FAIL (pencere yok), sonra 2 PASS.
- Model kartı regresyonu önce FAIL (waiting → install), düzeltildi.
- Python tam suite: `PIXELMEND_MODELS_DIR=/private/tmp/pixelmend-rc4-unit-models uv run pytest -q`
  → 182 passed, 2 skipped, mevcut Starlette deprecation uyarısı.
- Önceki durumu koruyan ilk tam koşu: 179 passed, 2 skipped (191.63 s).
- Geçici pnpm sandbox indirmesi DNS engeline takıldı; sadece kendi test süreçleri
  durduruldu, izinli ağ ortamında yeniden çalıştırılıyor.
- Kullanıcı: mevcut klasörde devam et; yeni worktree oluşturulmadı.
- Desktop 12 node + 40 Vitest PASS; CI-tools 15 PASS; tsc/Vite build PASS.
- Bağımsız inceleme: Important tanı hatası native drain öncesinde raporlanmalı.
  Yeni entegrasyon regresyonu FAIL (rapor yok); sıralama düzeltildi. Başka önemli
  veya küçük bulgu yok; paket/native ölçümler inceleme kapsamı dışında, ayrıca doğrulanacak.
- İnceleme regresyonu RED → GREEN; desktop 14 node + 40 Vitest PASS;
  CI-tools 15 PASS; Python 184 PASS, 2 isteğe bağlı test SKIP, mevcut deprecation.
- `node e2e/startup.cjs` gerçek Electron/gerçek dört model: PASS.
  Etkileşimli pencere 306/296/292 ms; temel editör 1396/1322/1201 ms;
  modeller hazır 25465/25318/26003 ms. Her koşuda ayarlar, Hakkında rc.4,
  görsel/çizim/OpenCV/Lanczos/kayıt ve normal kapanış geçti; renderer hatası yok.
  Paketli sürüm henüz ayrıca ölçülecek.
- İlk mevcut editör E2E koşusu LaMa/çizim/kayıt/büyütmeyi geçti, eski testte
  çıkış onayı için yanlış `dialog` seçicisi nedeniyle FAIL. Ekran ve gerçek
  DOM `alertdialog` olduğunu doğruladı; yalnız test seçicisi düzeltildi.
- macOS paketleme PASS: PyInstaller 6.22.3/Python 3.12.13/Electron 40.10.6;
  ARM64 DMG/ZIP üretildi. İsteğe bağlı onnxruntime.quantization toplama uyarısı
  (onnx yok) ve beklenen Developer ID imzası yok uyarısı; paket smoke ile sınanacak.
- Paket checksum/ZIP bütünlüğü/DMG verify PASS; salt-okunur DMG'den ve ZIP'ten
  çıkarılmış uygulamalar ayrı OpenCV/PNG smoke: exit 0/0.
- Paketli native açılış: PASS; 272/277/271 ms, temel editör 1299/1265/1267 ms,
  dört model 25257/25159/25255 ms. Hazırlık sırasında native güvenli kapanış 595 ms.
- Kurulum: /Applications/PixelMend.app rc.4; rc.3 yedeği
  /Users/gladius/.Trash/PixelMend-rc4-update.7k6DYd/PixelMend-rc.3.app.
  İki kontrolle uygulamanın kapalı olduğu doğrulandı; modeller/profil korunuyor.
- Geçici pnpm sandbox önbelleği kayıpsız /private/tmp/pixelmend-rc4-pnpm-cache.KRq0cl
  altına taşındı; kaynak ağacı temiz tutuldu. Commit/push/merge yapılmadı.
- Gerçek model alfa/kaynak/çıktı testi `PIXELMEND_REAL_MODELS=1 uv run pytest -q tests/test_real_models.py`
  → 1 PASS (40.67 s).
- Kurulu editör ilk koşusu FAIL (AI işini başlatırken hata); aynı cache kullanan
  gerçek model testiyle eşzamanlı koşuyordu. ModelManager lease() başka sürecin
  sınama kilidini busy olarak reddediyor. Ruling: gerçek model kullanan kabul
  koşularını seri çalıştır; güvenlik kilidini kaldırma. İzole tekrar koşusu sürüyor.
- rc.4 kendi Mac başlatıcısı + geçici auto bayrağı sarmalayıcısı: exit 2,
  standart ZIP oluştu; 21 PASS + beklenen 2 unsupported, diğer durum yok.
- Kurulu editör izole tekrar koşusu PASS; eski zoom pasif dinleyici console
  uyarısı var, renderer pageerror yok. Tekerlek davranışı bu görevde değiştirilmedi.
- Nihai kanıt: docs/verification/mac-rc4-startup-2026-10-03.md. Kullanıcının
  günlük kontrolü/kapsamlı rc.4 ZIP/insan görsel incelemesi kabul için hâlâ beklemede.
- Son çalışma ağacı testleri: 14 Node + 40 Vitest + 15 CI-tools PASS;
  Python 184 PASS/2 SKIP/mevcut Starlette uyarısı. ZIP/DMG SHA256 tekrar PASS.
- Ruling: native/paket/gerçek performans kanıtlarını incelemeciden bağımsız,
  yerel gerçek donanım koşularıyla sağla; kapsamlı insan kalite kabulünü beklemede bırak.
  Maliyet: günlük gerçek fotoğraf UX/kalite sorunları kullanıcı kontrolünde ortaya çıkabilir.
- Plan yerleşim kararı maliyeti: yalnız planın dizini farklı; uygulama davranışı etkilenmez.
- Seri model kabul koşuları kararı maliyeti: test toplam süresi uzar;
  normal tek uygulama kullanımına ek kısıtlama getirilmez.
- Kullanıcı kısa günlük kontrolü "tamamdır sorun yok" ile onayladı.
- Kullanıcı kalan testleri tamamlama ve mevcut dala commit/push yetkisi verdi.
  Kapsamlı rc.4 tanısı kurulu uygulama/kendi test-kiti ile başlatıldı; kişisel
  fotoğraf/profil kullanılmıyor. İnsan kalite kabulü ayrı tutulacak.
- Commit öncesi güncel suite: Python 184 PASS/2 SKIP (2.63 s),
  desktop 14 Node + 40 Vitest, CI-tools 15 PASS; tsc/Vite build PASS.
- Kapsamlı rc.4 koşusu tamamlandı: 707 PASS + beklenen 2 unsupported,
  exit 2; 12 fotoğraf/672 iş/721 artefakt, 1600×900 ve 2400×1350 dört tekrar
  dahil. 685 sonuç PNG başlık/ölçü kontrolü ve ZIP bütünlüğü PASS.
  20:48:57–21:34:53 UTC (46 dakika); motor/uygulama kapanışı doğrulandı.
- AI destekli görsel inceleme docs/verification/mac-rc4-visual-review-2026-10-03.md
  altında tamamlandı. Nihai insan kalite onayı ayrı ve beklemede; küçük kaynak/
  sabit maske, gökyüzü ton/doku değişimleri, GPU-only ve çalışan AI iptali
  kanıtı sınırları açıkça kaydedildi.
- Entegrasyon kararı kullanıcıya ait: mevcut feature dalına commit/push;
  merge, PR, release tag veya paket yayımlama yok. Kaynak/test-kiti/seçili JSON
  ve checksum kanıtları git'e; büyük kurulum/test görselleri yerelde kalır.
- Kapsamlı koşu sonrasında commit ağacı tekrar sınandı: Python 184 PASS/2 SKIP
  (2.40 s, mevcut Starlette uyarısı); 14 Node + 40 Vitest + 15 CI-tools PASS;
  tsc/Vite build ve staged/unstaged whitespace kontrolü PASS.
