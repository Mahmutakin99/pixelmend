# Faz 4 — Tier Sistemi, Ayarlar, Model Yöneticisi

Amaç: Hafif cihaz kullanıcısı ağır modeli indirmeden güvenli varsayılanlarla çalışsın; güçlü cihazda uygun algoritmalar ölçüme dayanarak önerilsin. Tier bir donanım gerçeği değil, algoritma uygunluklarının kullanıcıya sade sunumudur.

## Görevler

- [ ] İlk açılış önerisi `capabilities.py` + algoritma manifestlerinden türetilir:
  - Her algoritmanın minimum host RAM, varsa seçili adapter device budget, doğrulanmış model+backend probe'u ve latency sınıfı bağımsız değerlendirilir.
  - Host RAM ve VRAM/unified/shared budget tek “etkin bellek” sayısında birleştirilmez.
  - Ölçülemeyen alan `unknown` kalır; temkinli varsayılan seçilir ve neden kullanıcıya açıklanır.
  - Sabit donanım profili ilk öneriyi belirler; anlık host/device headroom her iş öncesi admission guard'dır. Açık uygulamalar yüzünden tier açılıştan açılışa rastgele değişmez.
- [ ] Kurulum akışı önerilen modu, etkinleşecek algoritmaları, toplam indirme boyutunu ve gerekçeyi tek ekranda gösterir. Kullanıcı onaylayabilir veya değiştirebilir; ağır model sessizce indirilmez.
- [ ] Ayarlar → Performans:
  - Algoritmalar hafiften ağıra, iş türüne göre gruplanır.
  - Her satırda: measured/estimated ayrımıyla süre; host ve device bellek ayrı; doğrulanmış backend; model boyutu; açık/kapalı durum; “neden önerilmedi” açıklaması.
  - Tier dışına çıkmak mümkündür; çökme riski olan kesin kaynak yetersizliği ile yalnız “yavaş olabilir” uyarısı birbirinden ayrılır.
  - Toggle değişimi anında ve yerinde feedback verir; download/probe sürerken kontrolün durumu ve iptal yolu görünür, klavye ve ekran okuyucuyla kullanılabilir.
- [ ] Faz 1'deki güvenli model edinim çekirdeği kullanıcıya dönük sidecar model yöneticisine genişletilir:
  - Model ağırlıkları pakete ve git'e gömülmez.
  - Varsayılan depo `paths.py` ile platform cache yoludur; Electron path birleştirmez. `PIXELMEND_MODELS_DIR` yalnız açık override'dır.
  - Manifest her dosya için repo id, immutable revision/commit, filename, lisans kimliği/linki, beklenen byte boyutu ve SHA-256 taşır. Üretim hareketli `main` dalına bağlı kalmaz.
  - İndirme geçici dosyaya yapılır; boyut+hash doğrulandıktan sonra atomik biçimde etkin konuma alınır. Bozuk/kısmi dosya inference'a açılmaz.
  - Disk alanı ön kontrolü, iptal/retry ve mümkünse güvenli resume; progress authenticated sidecar → main → renderer event akışıyla gösterilir.
  - Renderer model yolu veya genel silme yetkisi almaz. “İndirileni sil” model id/revision üzerinden sidecar'a gider ve yalnız manifestte kayıtlı hedefi temizler.
- [ ] Model deposu görünürlüğü:
  - Toplam ve model bazlı boyut, aktif revision, son kullanım, indirme/doğrulama durumu.
  - Kullanılmayan eski revision'lar açıkça listelenir; otomatik temizleme ancak tanımlı politika ve geri bildirimle yapılır.
  - Varsayılan OS cache yolu tekrar indirilebilir veri olarak kabul edilir. Kullanıcı kalıcı/özel konum seçerse override doğrulanır ve taşınma akışı kesintiye dayanıklı olur.
- [ ] Süre/bellek gösterimleri yalnız `engine/bench/` onaylı baseline'larından gelir; makine/backend/model hash'i uyuşmuyorsa “ölçülmedi” veya yaklaşık olarak işaretlenir, sahte kesinlik verilmez.
- [ ] Windows inference backend'i bu fazda yeniden doğrulanır: DirectML'in mevcut durumu, Python sidecar uyumu ve alternatif Windows ML yolu benchmark/ADR ile değerlendirilir; eski varsayım sessizce sürdürülmez.

## Doğrulama

- Temiz profilde uygulama açılır; klasik hafif algoritmalarla iş yapılır ve hiçbir model kendiliğinden indirilmez.
- Accelerator bilinmiyor, device budget ölçülemiyor ve model probe'u başarısız senaryoları temkinli ama açıklanabilir öneri üretir.
- LaMa/Real-ESRGAN ilk kez açıldığında revision, boyut ve SHA doğrulamasıyla indirme tamamlanır; kısmi/bozuk indirme kullanılmaz.
- Progress, iptal, retry, disk-dolu ve hash uyuşmazlığı durumları UI'da eyleme dönük hata verir.
- “İndirileni sil” yalnız seçilen model revision'ını kaldırır; ayarlar, temp job sonuçları ve diğer modeller etkilenmez.
- Gösterilen süre/bellek değerinin ilgili benchmark baseline/model/backend kimliğine dayandığı izlenebilir.

Bitince: `DURUM.md` güncellenir; kalıcı backend/tier kararları ADR'ye eklenir; commit yalnız kullanıcı onayıyla atılır.
