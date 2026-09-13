# Karar Günlüğü (ADR)

Bu dosya "neden böyle yaptık" sorusunun cevabını tutar. Yeni bir kalıcı mimari karar alındığında buraya bir madde eklenir — mevcut maddeler silinmez, gerekirse "değiştirildi" notu ile üstüne yenisi eklenir.

---

## 1. Çıkarım motoru: Hibrit ONNX Runtime + opsiyonel PyTorch

**Karar:** Uygulamayla birlikte paketlenen varsayılan motor ONNX Runtime olacak (OpenCV inpaint, LaMa, Real-ESRGAN, GFPGAN). Stable Diffusion / SDXL gibi ağır, prompt destekli modeller için ayrı, kullanıcı isteğe bağlı indirdiğinde kurulan bir PyTorch ortamı olacak.

**Neden:**
- ONNX Runtime tek bir model formatıyla CoreML (macOS), DirectML (Windows), CUDA (NVIDIA/Linux) execution provider'larını kapsıyor → çapraz platform GPU hızlandırma için tek kod yolu yeterli.
- Saf PyTorch yaklaşımı (IOPaint'in yaptığı gibi) her platform için ayrı, büyük (Windows'ta CUDA ile 3-5GB) paket demek.
- Saf ONNX yaklaşımı ise SD/SDXL'i tamamen dışarıda bırakır — "buraya X çiz" gibi üretken doldurma imkansız olur.
- Hibrit, tier sistemiyle birebir örtüşüyor: hafif/orta tier küçük kurulumla gelir, ağır tier isteyen ayrıca indirir.

**Bedeli:** İki ayrı çıkarım kod yolu bakımı (ONNX adapter'ları + PyTorch adapter'ları). Kabul edilebilir.

**2026-08-28 değişikliği:** Bu maddedeki GFPGAN'in varsayılan ONNX motorunda yer alacağı kısmı, aşağıdaki 9 numaralı kararla değiştirilmiştir. OpenCV + LaMa + Real-ESRGAN ONNX ve opsiyonel PyTorch omurgası korunur.

---

## 2. Masaüstü kabuğu: Electron (Tauri değil)

**Karar:** Electron + Vite + React + TypeScript.

**Neden:**
- Geliştirme makinesinde (ve kullanıcının genel stack'inde) Node/React/TS zaten var; Rust toolchain kurulu değil ve öğrenme eğrisi eklemek istemedik.
- Python sidecar process yönetimi (spawn/health-check/graceful-shutdown) Electron ekosisteminde çok daha olgun ve belgeli.
- Tauri'nin ~5-10MB kurulum avantajı burada anlamsız kalıyor çünkü uygulama zaten yanında yüzlerce MB - birkaç GB model taşıyacak; Electron'un ~100MB fazlası marjinal.

**Bedeli:** Daha yüksek bellek ayak izi (Electron ~150-300MB vs Tauri ~30-50MB). Kabul edildi.

---

## 3. IOPaint: referans, fork değil

**Karar:** github.com/Sanster/IOPaint (eski adıyla lama-cleaner, Apache-2.0, Ağustos 2025'te arşivlendi) neredeyse aynı problemi çözmüş bir proje. Kod tabanı fork edilmeyecek, sadece çözülmüş problemlere (maske harmanlama, tiling stratejisi, model yükleme sırası) referans olarak bakılacak.

**Neden:**
- Arşivlenmiş, artık bakımı yapılmıyor — üstüne inşa etmek teknik borç devralmak demek.
- Tamamen PyTorch'a bağlı, bizim hibrit ONNX-öncelikli motor stratejimizle örtüşmüyor.
- Sıfırdan yazmak, hafif tier'i (ONNX) IOPaint'in hiç yapmadığı şekilde önceliklendirmemizi sağlıyor.

---

## 4. Dış API yok, tamamen yerel çalışma

**Karar:** Uygulama hiçbir görsel işleme isteğini üçüncü parti bir API'ye (Replicate, Stability, vb.) göndermeyecek. Tüm çıkarım kullanıcının kendi cihazında çalışır.

**Neden:** Sıfır per-request maliyet, görsellerin cihazdan hiç çıkmaması (gizlilik), internet bağımlılığı olmadan çalışabilme.

**Bedeli:** Kullanıcının donanımı yetersizse bazı algoritmalar (özellikle SDXL) çalışmayabilir/çok yavaş olabilir — bu, tier sistemiyle yönetiliyor, API fallback'i yok.

---

## 5. Tier sistemi: ağır algoritmalar varsayılan kapalı

**Karar:** Algoritmalar RAM ihtiyacına göre Hafif/Orta/Yüksek/Maksimum tier'lerine ayrılır. Uygulama açılışta donanımı algılayıp bir tier önerir; sadece önerilen tier ve altındakiler varsayılan açık gelir. Kullanıcı ayarlardan istediği algoritmayı elle açıp kapatabilir.

**Neden:** Hem hız (daha az algoritma = daha hızlı sonuç), hem düşük RAM'de swap/çökme riskini azaltma, hem de "her şeyi indir" yerine "sadece kullanacağını indir" ile kurulum boyutunu küçük tutma (bkz. Faz 4 — lazy model indirme).

**2026-08-28 değişikliği:** Yalnız RAM'e dayalı öneri hesabı aşağıdaki 10 numaralı kararla değiştirilmiştir. Ağır algoritmaların varsayılan kapalı olması ve kullanıcının seçebilmesi kararı geçerlidir.

---

## 6. Renderer sidecar'a doğrudan bağlanmaz

**Karar:** Electron main sidecar'ın tek authenticated istemcisidir. Renderer sidecar portunu, oturum token'ını, mutlak dosya yolunu veya genel amaçlı ağ API'sini almaz. Preload yalnız görev bazlı, şeması doğrulanan IPC metotları sunar; sonuçlar opaque `result_id` ve kontrollü `pixelmend:` protokolüyle gösterilir.

**Neden:** Rastgele localhost portu kimlik doğrulama değildir. Token'ı renderer'a vermek renderer compromise durumunda güven sınırını yok eder; browser `EventSource` da özel auth header'ı taşımak için uygun değildir. Main proxy; CSP'yi dar tutar, sidecar olaylarını doğrular ve yerel path'leri UI'dan gizler.

**Bedeli:** Main süreçte HTTP/SSE proxy, IPC event yaşam döngüsü ve custom protocol bakımı gerekir. Buna karşılık güven modeli tek noktada kalır.

---

## 7. Model deposunun sahibi sidecar'dır

**Karar:** Varsayılan model deposu `platformdirs.user_cache_path("PixelMend", appauthor=False) / "models"`; `PIXELMEND_MODELS_DIR` yalnız açık override'dır. Electron/renderer path üretmez. Her model immutable revision, beklenen boyut, SHA-256 ve lisansla manifestte tanımlanır; download doğrulamadan sonra atomik etkinleştirilir.

**Neden:** Headless ve Electron çalıştırmalarının farklı dizinlere yazmasını engeller. Electron `userData` büyük tekrar indirilebilir dosyalar için uygun varsayılan değildir. Immutable revision/hash, hareketli model deposu ve bozuk/kısmi indirme riskini azaltır.

**Bedeli:** Model yönetimi için sidecar API'si, migration ve cache temizleme politikası gerekir. OS cache temizlenirse model yeniden indirilebilir; bu kullanıcıya açıkça anlatılır.

---

## 8. Tek görsel I/O ve maske sözleşmesi

**Karar:** Bütün adapter'lar orientation uygulanmış, renk yönetimli sRGB `RGB uint8` görsel alır; alfa ayrı taşınır. Canonical maske görselle aynı boyutta tek kanal `uint8`; `255=işlenecek`, `0=korunacak` ve yalnız binary değerlerdir. Adapter'lar dosyayı bağımsız açmaz.

**Neden:** Tarayıcı ile sidecar'ın EXIF orientation'ı farklı yorumlaması yanlış bölgenin silinmesine; ICC'nin düşmesi veya yanlış yeniden takılması renk kaymasına; farklı maske konvansiyonları ters bölgenin işlenmesine yol açar. Merkezi sözleşme bunları algoritmadan bağımsız test edilebilir hale getirir.

**Bedeli:** Renk dönüşümü ve metadata politikası ayrıca uygulanır. HEIF/HEIC, decoder binary lisansı çözülmeden dependency lock'a alınamaz. Çıktı EXIF/GPS/thumbnail politikası Faz 2'den önce açık karardır.

---

## 9. GFPGAN v1 kapsamı dışında

**Karar:** GFPGAN, Faz 3 veya v1 teslimatı değildir. Ayrı fizibilite kapısında uçtan uca pipeline, tekrarlanabilir ONNX artefakt, backend ölçümü ve dosya/ağırlık bazlı lisans provenance'ı onaylanmadan ürüne girmez.

**Neden:** Resmî kullanım yalnız tek GFPGAN inference değildir; RetinaFace/landmark, affine hizalama, yüz başına çıkarım, ParseNet/soft paste-back ve çoklu yüz akışı gerektirir. Resmî desteklenen uçtan uca ONNX artefakt yoktur. Üst seviye Apache-2.0 beyanı StyleGAN2, DFDNet ve diğer third-party NC/SA/provenance koşullarını ortadan kaldırmaz.

**Bedeli:** v1'de yüz iyileştirme özelliği yoktur. Karşılığında kapsam, lisans riski ve Faz 3 takvimi dürüst kalır.

---

## 10. Tier tek RAM sayısı değil, algoritma uygunluk özetidir

**Karar:** Tier önerisi; host RAM, seçili adapter'ın ölçülebilen device budget'ı, bellek türü, model+EP session probe'u ve ölçülmüş latency gereksinimlerini ayrı değerlendirir. RAM ve VRAM tek “etkin bellek” formülünde birleştirilmez; `unknown` değer uydurulmaz.

**Neden:** Host RAM ile device memory birbirinin alternatifi değildir. Aynı RAM'e sahip CUDA GPU, entegre GPU ve CPU-only makineler farklı davranır; Apple unified memory de ayrık GPU formülüyle temsil edilemez. Algoritma bazlı uygunluk, “donanımınıza göre uyarlanır” vaadini test edilebilir yapar.

**Bedeli:** Platforma özgü capability toplama, model probe ve kalibrasyon gerekir. Tier tablosu basit ama yaklaşık bir UX özeti olur; teknik kararın kaynağı olmaz.

---

## 11. v1 macOS hedefi Apple Silicon

**Karar:** v1 macOS paketi arm64/Apple Silicon'dur. Windows ve Linux v1 hedefleri x64'tür. macOS Intel daha sonra ayrı karar olmadan desteklenmiş sayılmaz.

**Neden:** 2026-08-28 itibarıyla GitHub'ın Intel runner'ı vardır; asıl sorun güncel ONNX Runtime'ın macOS x86_64 wheel yayımlamamasıdır. Intel'i korumak eski ORT pin'i veya kaynaktan native build, ayrı dependency hattı ve gerçek x64 smoke test getirir.

**Bedeli:** Intel Mac kullanıcıları v1'i çalıştıramaz. Buna karşılık ana inference bağımlılığında eski/sapmış platform hattı taşınmaz.

---

## 12. Repo üst lisansı Apache-2.0

**Karar:** PixelMend kaynak deposu Apache License 2.0 ile lisanslanır.

**Neden:** Açık katkılar için patent lisansı ve katkı koşullarını açıkça tanımlar; OpenCV ve LaMa gibi çekirdek bileşenlerin Apache-2.0 ekosistemiyle uyumludur.

**Bedeli:** Dağıtımda Apache-2.0 bildirim koşulları izlenir. Bu üst lisans; model, codec, native binary veya diğer üçüncü parti bileşenlerin kendi lisanslarının yerine geçmez.

---

## 13. HEIF/HEIC v1 kapsamı dışında

**Karar:** v1 giriş formatları JPEG, PNG, WebP ve TIFF'tir. HEIF/HEIC için v1 paketine decoder eklenmez ve format destekleniyor gibi sunulmaz.

**Neden:** Güncel `pillow-heif` binary wheel'i GPLv2 bileşen taşır; bakımı sona eren `pi-heif` yeni proje için uygun değildir. Platformlar arası sürdürülen, dağıtım lisansı doğrulanmış bir decoder yolu seçilmeden HEIF desteği taahhüt etmek lisans ve bakım riski yaratır.

**Bedeli:** HEIF/HEIC kullanıcıları v1'de görsellerini önce desteklenen bir formata dönüştürmelidir. Gelecekte destek eklenmesi yeni codec/provenance incelemesi ve ayrı ADR gerektirir.

---

## Değerlendirilip reddedilen alternatifler

- **Sadece PyTorch (IOPaint tarzı):** Reddedildi — paket boyutu ve platform başına ayrı derleme yükü çok fazla.
- **Sadece ONNX (SD/SDXL yok):** Reddedildi — üretken doldurma (prompt'lu inpainting) tamamen dışarıda kalırdı, bu bir özellik kaybı.
- **Native Swift/SwiftUI (sadece macOS):** Değerlendirilmedi bile — kullanıcı açıkça çapraz platform istedi (Mac + Windows + Linux).
- **Tauri:** Reddedildi — Rust toolchain eksikliği ve Python sidecar entegrasyonunun Electron'a göre daha az olgun olması.
