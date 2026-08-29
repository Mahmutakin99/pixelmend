# DURUM — PixelMend

Son güncelleme: 2026-08-29

## Şu an neredeyiz

**Faz 1 — Hafif/headless motor** başladı. Faz 0 M4 kurulumu tamamlandı; kullanıcı 2026-08-29 tarihinde açık kodlama onayı verdi. Repo üst lisansı Apache-2.0 olarak seçildi, HEIF/HEIC v1 kapsamından çıkarıldı.

İlk iki TDD diliminde Python proje omurgası, sidecar'ın model dizinini çözen `paths.py` ve çevrimdışı manifest/dosya bütünlüğü çekirdeği eklendi. Henüz model indirilmedi; FastAPI, görsel I/O, adapter, kuyruk veya UI koduna başlanmadı.

## Ortam

- **Bu klasörün oluşturulduğu makine:** MacBook, Apple M1, 8GB RAM, macOS 26.6.1. Sadece planlama/doküman üretimi için kullanıldı, hiç kurulum yapılmadı.
- **Etkin geliştirme makinesi:** Mac Mini, Apple M4, 16GB unified memory, macOS 26.6 (25G72), arm64.
- **Araçlar:** Node 25.9.0, pnpm 11.24.0, uv 0.11.25, uv-managed CPython 3.12.13, Apple Git 2.50.1.
- **v1 hedef dağıtım platformları:** macOS Apple Silicon (arm64), Windows x64, Linux x64. macOS Intel güncel ONNX Runtime'ın x64 wheel yayımlamaması nedeniyle v1 kapsamı dışında; bkz. `docs/karar-gunlugu.md` madde 11.
- Faz 0 araç doğrulaması tamamlandı. Sistem `python3` komutu macOS Python 3.9.6'yı gösterdiği için proje komutları `uv` üzerinden Python 3.12 kullanır.

## Yapılanlar (tarihli, en yeni üstte)

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

1. Kanonik LaMa manifestinin immutable revision ve byte boyutunu birincil kaynaktan doğrula; ağırlığı indirmeden manifest sabitini test-first ekle.
2. Aynı dosya sisteminde geçici adayın doğrulama sonrası atomik etkinleştirilmesini ve eşzamanlı edinim kilidini test-first uygula.
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
