# Bu Mac için doğrulama — 2026-09-20

LaMa varsayılan nesne silme ve RealESRGAN x4plus yerel ONNX büyütme CPU üzerinde çalışır. OpenCV ve Lanczos ayrı seçimlerdir. AI işi başka algoritmaya sessizce dönmez.

## Kanıt ve kapsam

- Motor: `PIXELMEND_REAL_MODELS=1 engine/.venv/bin/python -m pytest engine/tests -q` → **126 passed, 0 skipped**, tek Starlette TestClient bağımlılık uyarısı. Gerçek iki model kuyruğu, LaMa maskesiz piksel/alpha koruması, RealESRGAN alpha/boyut, lease ve sonuç/event metadata dahildir.
- Masaüstü: **26 Vitest testi**, TypeScript/Vite production build ve **3 paketleme kanıt testi** geçti.
- PyInstaller motoru ve Electron arm64 `.app` üretildi. Paketli editörde boya/seçim silgileri, undo/redo, LaMa önizleme/vazgeç, açık OpenCV seçimi, PNG export, RealESRGAN 96×64 → 192×128, Lanczos özel ölçü, sonuçtan devam ve zoom geçti.
- Temiz model deposu ve temiz profil: iki model yerel dosya seçimiyle kuruldu, seçilen kaynak kopyaları silindi, uygulama yeniden açıldı; iki AI işlemi doğru algoritma/revision/CPU metadata ile tamamlandı. AI iptali geçti. Depo geçici export dizinine bağımlı değildir.
- Gerçek kartal fotoğrafı Lanczos ile 1826×2019 → 7304×8076 (**58.99 MP**) üretildi: 0.304 saniye, süreç tepe RSS 929 MiB; sınır üzerindeki AI isteği çıktı ayırmadan reddedildi. Bu büyük AI throughput testi değildir. [Ölçüm](large-image.json).
- Kaynak sınırı testleri 200 MP üzerini, AI doğal 4× ara çıktısını, kullanılabilir RAM, disk ve sonuç bütçesini reddeder. 200 MP bir güvenlik tavanıdır; bu boyutta hız/kalite kabulü veya her dosyada çalışma garantisi değildir.

## Model kökeni

LaMa: `a3ee2fca54baebec351b8fa7786154ffa7555aa6`, 208044816 byte, SHA-256 `1faef5301d78db7dda502fe59966957ec4b79dd64e16f03ed96913c7a4eb68d6`.

RealESRGAN: resmî v0.1.0 kaynak ağırlığı SHA-256 `4fa0d38905f75ac06eb49a7951b426670021be3018265fd191d2125df9d682f1`. BSD-3-Clause lisans dosyası kaydedildi. ONNX 67051639 byte, SHA-256 `3d05f9cecd652841eeb408ceb02c360e48115eaba33c807894a06e6a00218fbc`. Yerel revision, export aracını içeren kaynak commit `c4e5303b53044767c94bb78f49365cb710ee459e`; bu bir yayımlanmış model deposu revision'ı değildir.

[Export provenance](realesrgan-export.json): FP32 NCHW RGB, dinamik H/W, opset 17, doğal 4×. Dört asimetrik boyutta PyTorch/ONNX parity geçti; en büyük mutlak fark 9.36e-6. Model yöneticisi sabit manifest boyut/hash eşleşmesi olmadan yerel dosyayı etkinleştirmez. Yeniden açılışta gerçek CPU probe yapılır.

## Fotoğraf kalitesi ve ölçümleri

[12 fotoğraf manifesti](photograph-manifest.json) orijinal hash, kaynak, lisans, yerel hazırlama ve ölçüleri içerir. Lisans kayıtları [scikit-image birincil veri belgelerinde](https://scikit-image.org/docs/0.25.x/api/skimage.data.html) yer alır. Fotoğraflar CC0 veya kamu malıdır. Yerel pikseller `engine/bench/fixtures/`, karşılaştırmalar `apps/desktop/test-results/mac-acceptance/` içindedir.

LaMa dört gerçek fotoğrafta OpenCV ile karşılaştırıldı: düz duvar (astronaut), ahşap dokusu (coffee), yapı çizgileri (brick), kenara yakın tüy (chelsea). Tüm maskesiz pikseller birebir korundu. Son koşuda inference 1.22–1.24 saniye. Görsel incelemede duvarda iki yöntem de kabul edilebilir; LaMa ahşap çizgilerini ve tuğla derzlerini OpenCV'den belirgin iyi tamamlıyor. Kedi tüyünde kenar izi daha az, ancak ince tüy/bıyık yumuşaması var. [Ayrıntılı ölçümler](lama-measurements.json).

RealESRGAN benchmarkı 12 fotoğrafın **uzun kenarı en fazla 192 piksel olan** RGB sürümlerinde 2× ve 4× çalıştırıldı; her hedef için bir yeni oturum/soğuk ve bir sıcak ölçüm alındı. CPU soğuk süre 2.22–5.82 saniye, sıcak süre 2.22–5.64 saniye; 10 ms aralıkla örneklenen en yüksek süreç RSS 666.4 MiB. Oturum yükleme süresi ayrı alandadır. Aynı Mac'te eşzamanlı test/build çalışmaları bu süreleri etkileyebilir. [Ham ölçümler](upscale-measurements.json).

2× ve 4× karşılaştırmaları görsel olarak incelendi. Yüz/giysi, tuğla, kamera, kedi, fincan, kartal ve roket kenarları Lanczos'tan daha belirgin. Çim/çakıl daha keskin ama biçimlendirilmiş doku üretir; saat hareket bulanıklığını geri getirmez. Hubble yıldızları ve mikroskopik skin ayrıntıları değişebilir; çıktı özgün ayrıntının birebir rekonstrüksiyonu değildir. İncelenen karo örtüşme bölgelerinde belirgin sert birleşim çizgisi görülmedi; bu, tek-karo/tam-kare sayısal eşdeğerlik iddiası değildir. Alfa ayrı gerçek kuyruk testiyle doğrulandı.

## Denetimde bulunan ve giderilen kusurlar

1. Electron nesne silmeyi OpenCV'ye sabitliyordu; açık yöntem ve LaMa varsayılanı eklendi.
2. LaMa ortak model deposu lease/probe yolunu kullanmıyordu; iş boyunca aynı doğrulanmış dosya tutuluyor.
3. AI kabulünde `shutil.disk_usage(None)` gerçek paketli büyütmeyi HTTP 500 ile durduruyordu; gerçek geçici dizinle regresyon ve düzeltme eklendi.
4. Model admission hataları genel 422'ye dönüşüyordu; kod/mesaj/status artık korunuyor.
5. İngilizce seçeneği çevirmiyordu; tamamlanmamış seçenek kaldırıldı. Sistem teması artık OS renk tercihini izler.
6. Native pencere kapatmada kaydetme koruması yoktu; mevcut kaydet/vazgeç diyaloğuna bağlandı. Motor, onaylanmış çıkıştan sonra kapanır.

## Kurulum ve temizlik

Yeni uygulama `/Applications/PixelMend.app` konumuna 19:51 yerel saatte kuruldu; eski kopya `.Trash/PixelMend-20260920-195117/PixelMend.app` altında. Kurulum sonrası `e2e/editor.cjs`, temiz depo ile `e2e/models.cjs` ve `PIXELMEND_CI_SMOKE=1` geçti (exit 0). Testlerin ardından PixelMend/sidecar süreci kalmadığı süreç listesinde doğrulandı. Çöp'e taşıma geri alınabilir; Çöp boşaltılmadıkça fiziksel disk alanı serbest kalmış sayılmaz. Git geçmişi korunur.

`engine/build`, `engine/dist`, Python test önbelleği, yinelenen export ONNX ve eski `:memory:.ses` dosyası Çöp'e taşındı: çalışma ağacından, yinelenen test paketi dahil **896838037 byte (855.3 MiB)** çıkarıldı. Aktif iki model, kaynak checkpoint, lisans/provenance, fixture/sonuç kanıtları ve bağımlılıklar korundu. [Kesin yollar](cleanup.json), [gizli dosyalar dahil envanter](tree-inventory.json). Artık bulunmayan `/private/tmp/pixelmend-desktop-mvp` worktree kaydı temizlendi; `.git` geçmişi değiştirilmedi.

Native kapatma regresyonu: değişiklik varken kapatma → Kaydet/Vazgeç diyaloğu; Vazgeç belgeyi korur. Sonuç önizlemesi varken kapatma → önce Uygula/Vazgeç yönlendirmesi; sonuç kaybolmaz. Proje kaydet/aç gerçek paket üzerinden roundtrip sınandı.
