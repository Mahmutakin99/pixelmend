# Faz 2 — Electron Kabuğu + Maskeleme

Amaç: Uçtan uca “yükle → çiz → sil → kaydet” akışı tek algoritmayla (LaMa) çalışsın; renderer ayrıcalıksız kalsın ve kullanıcı etkileşimi büyük görselde de hızlı, geri alınabilir ve erişilebilir olsun.

## Faz kapıları

- [ ] Yayıncı kimliği ve reverse-DNS `appId` ilk paketli smoke build'den önce karara bağlanmış olmalı. Ürün adı `PixelMend`, paket adı `pixelmend`.
- [ ] Çıktı EXIF/GPS/thumbnail saklama veya temizleme politikası kaydetme akışından önce karara bağlanmış olmalı.

## Görevler

- [ ] `apps/desktop/`: Vite + React + TypeScript + Electron iskeleti; `contextIsolation: true`, `sandbox: true`, `nodeIntegration: false`, web güvenliği açık.
- [ ] Electron main, sidecar'ın tek istemcisi ve güven sınırıdır:
  - Açılışta en az 256-bit rastgele oturum token'ı üretir; token komut satırına veya loga yazılmaz, sidecar'a env ile aktarılır.
  - Sidecar yalnız `127.0.0.1` üzerinde port `0` ile dinler ve seçtiği portu kontrollü başlangıç mesajıyla main'e bildirir. Port rastgeleliği yalnız çakışma önlemidir.
  - Main, token'lı `/health` polling ile hazır olmasını bekler; timeout/hata kullanıcıya eyleme dönük biçimde gösterilir.
  - Main authenticated HTTP/SSE istemcisidir; olay şemasını doğruladıktan sonra renderer'a dar, görev bazlı IPC event'leri yollar.
  - Renderer sidecar portunu, token'ı, dosya yollarını veya genel bir `request(url, options)` yetkisini hiçbir zaman almaz.
  - Kapanışta önce kontrollü queue shutdown; grace süresi aşılırsa platforma özgü process-tree sonlandırma. `before-quit`/`window-all-closed` yolları ve crash recovery test edilir.
- [ ] `electron/preload.ts`: `contextBridge` üzerinden yalnız ihtiyaca özel API'ler (`openImage`, `disposeAsset`, `startInpaint`, `cancelJob`, `subscribeJob`, `readResult`, `saveResult`, `disposeJob`) sunar.
  - Her IPC çağrısında sender frame/origin ve payload şeması main tarafından doğrulanır.
  - Callback abonelikleri unsubscribe döndürür; renderer'a ham Electron event nesnesi sızdırılmaz.
- [ ] Kontrollü sonuç protokolü:
  - `openImage` native seçimden sonra dosyayı main üzerinden `POST /assets` ile sidecar'a verir; renderer yalnız opaque `asset_id`, boyut/warning bilgisi ve kontrollü `pixelmend://asset/<opaque-id>` önizlemesi alır.
  - Sidecar event'i yalnız `result_id` taşır; main sonucu authenticated endpoint'ten alır.
  - Asset ve sonuç önizlemeleri `pixelmend://asset/<opaque-id>` / `pixelmend://result/<opaque-id>` gibi ayrıcalıksız, allowlist'li custom protocol ile yapılır. Handler yalnız aktif ve kayıtlı opaque id kabul eder; kullanıcı URL'sini veya dosya yolunu proxy etmez; `bypassCSP` açılmaz.
  - Kaydetme main'de `dialog.showSaveDialog` ve kontrollü sidecar sonucu üzerinden yapılır.
- [ ] CSP:
  - Prod renderer sidecar localhost'una bağlanmadığı için `connect-src` içinde loopback wildcard yoktur.
  - `img-src` yalnız `'self'`, kontrollü `pixelmend:` scheme'i ve gerçekten gerekiyorsa `blob:` içerir.
  - Vite dev CSP'si prod politikasından ayrı tanımlanır; inline script/eval prod'da açılmaz.
- [ ] Görsel içe aktarma:
  - Dosya seçme ve drag-and-drop aynı doğrulanmış main/preload yolundan geçer.
  - Sidecar `imageio.py` ile orientation/renk normalizasyonunu bir kez yapar; canvas, maske ve inference aynı normalize edilmiş piksel koordinat sistemini kullanır. Renderer ham dosyayı bağımsız biçimde yeniden decode edip farklı orientation/ICC davranışı üretmez.
  - Maske, import cevabındaki normalize `width×height` koordinatında üretilir; job ham image yerine `asset_id` ile başlatılır.
  - İçe aktarmada boyut, format, alfa ve dönüşüm warning'leri kullanıcıya işlemden önce açıkça gösterilir.
- [ ] Canvas fırça maskeleme bileşeni:
  - Ham `<canvas>` yeterliyse ek kütüphane kurulmaz; seçim gerçek cihaz profilinden sonra yapılır.
  - Undo/redo tam-canvas `getImageData()` snapshot yığınıyla değil, orijinal görsel koordinatlarında **stroke journal** ile yapılır: nokta listesi, radius, `paint | erase`, pressure varsa normalize edilmiş değer.
  - Undo son darbeyi geri alır ve maskeyi yeniden oynatır; uzun oturumda replay süresini sınırlamak için ölçülmüş, seyrek ve bellek bütçeli tek-kanal checkpoint kullanılabilir. 4 kanallı tam görsel snapshot'ı tutulmaz.
  - Pointer down anında görsel fırça geri bildirimi; `setPointerCapture` ile kesintisiz çizim; ekran ölçeği/zoom/pan'den bağımsız orijinal koordinat dönüşümü.
  - Fırça boyutu, paint/erase, temizle, undo/redo için görünür kontroller ve standart `Cmd/Ctrl+Z`, `Cmd/Ctrl+Shift+Z` kısayolları; klavye odağı ve erişilebilir adlar.
  - Undo/redo sırasında input kilitlenmez; kullanıcı yeni darbe başlatırsa redo kolu öngörülebilir biçimde temizlenir. İşlem durumu ve tamamlanma ekran okuyucuya canlı ama rahatsız etmeyen duyurulur.
- [ ] Maske export'u `docs/mimari.md` sözleşmesine uyar: normalize görselle aynı en-boy, tek kanallı `uint8`, `255=işlenecek`, `0=korunacak`; canonical inference maskesi yalnız `0/255` içerir.
- [ ] İş akışı: yalnız `lama`; progress/heartbeat, cancel, warning/error ve sonuç durumları görünür. Sonuç geldiği anda yer tutucunun yerine geçer; kullanıcı tüm akışı yeniden başlatmadan önce/sonra görünümüne dönebilir.
  - `cancelJob` main üzerinden `POST /jobs/{id}/cancel` çağırır; `disposeJob` yalnız terminal job'ı siler. İptal ve temizleme aynı eylem değildir.
- [ ] Kaydetme: seçilen formatın ICC/alfa/metadata kabiliyeti doğrulanır; kayıplı veya metadata düşüren dönüşüm açıkça belirtilir. Kullanıcıya başarı/konum geri bildirimi verilir.
- [ ] **Erken paketleme riski testi (zorunlu):** macOS arm64 üzerinde PyInstaller `onedir` sidecar smoke paketi.
  - Paketli binary ile authenticated `/health`, `/capabilities`, küçük OpenCV işi, bir LaMa ONNX session açılışı, sonuç okuma, temp cleanup ve kontrollü shutdown doğrulanır.
  - Önce mevcut `pyinstaller-hooks-contrib` hook'ları kullanılır; eksik varlık kanıtlanırsa dar custom hook eklenir. Körlemesine `--collect-all` varsayılmaz.
  - PyInstaller, hooks-contrib ve native dependency sürümleri kilitlenir; aynı smoke test Faz 6'da her OS/arch artefaktında çalışır.

## Etkileşim kabul kriterleri

- Fırça pointer'a 1:1 bağlı hissedilir; basış anında feedback verir ve canvas dışına taşan sürüklemede kopmaz.
- 4000×3000 görselde 100 darbeli undo/redo belleği tam RGBA snapshot yaklaşımına dönmez; replay süresi ve peak renderer belleği kaydedilir.
- Undo/redo, temizle, paint/erase ve kaydetme hem görünür kontrol hem klavye ile çalışır; odak kaybolmaz.
- `prefers-reduced-motion` durumunda büyük slide/spring yerine kısa fade veya anlık durum değişimi kullanılır; feedback tamamen kaldırılmaz.

## Doğrulama

- Uygulama açılır; sidecar'ın authenticated `/health` cevabı main üzerinden teyit edilir. Renderer DevTools'tan token, port veya genel sidecar istemcisi elde edilemez.
- EXIF orientation'lı ve Display P3 profilli fotoğraf yüklenir; çizilen maskenin inference'ta tam aynı bölgede kaldığı, çıktının sRGB görüntüsünün beklenen renkte olduğu doğrulanır.
- Fotoğraf yüklenir, alan çizilir, “Sil” denince LaMa sonucu görünür; iptal ve hata akışları da denenir.
- Sonuç `result_id` üzerinden önizlenir/kaydedilir; renderer'a mutlak dosya yolu düşmez.
- İş ekranından çıkınca terminal job için `DELETE /jobs/{id}` çağrılır; editör kapanınca kullanılmayan asset `DELETE /assets/{id}` ile bırakılır. Uygulama kapanınca session root ve sidecar process/thread kalmaz.
- Paketli `onedir` smoke testi geliştirme `uvicorn` sürecinden bağımsız geçer.

Bitince: `DURUM.md` doğrulama kanıtlarıyla güncellenir; commit yalnız kullanıcı onayıyla atılır.
