# Mac rc.4 — fotoğraf incelemesi

## Yöntem ve sınır

Kurulu rc.4, kendi Mac test başlatıcısı üzerinden kapsamlı/otomatik modda
çalıştırıldı. Rapor kimliği `ab6b7efa`; gerçek Apple M4/16 GB donanım ve dört
kurulu model kullanıldı. Kullanıcının kişisel fotoğrafları/profili kullanılmadı.

AI destekli inceleme, ilk tekrarın (`repeat=0`) 12 kaynak görüntüsünü,
OpenCV/MI-GAN/LaMa silme sonuçlarını ve Lanczos/iki RealESRGAN 4× sonuçlarını
karşılaştırır. Diğer ölçekler/tekrarlar teknik tanı tarafından doğrulanır;
her tekrarın her pikseli gözle incelenmiş değildir. Bu, kullanıcı tarafından
yapılmış insan kalite onayı veya tüm Mac modellerinin kabulü değildir.

## 12 fotoğraf gözlemleri

| Fotoğraf | Silme | 4× büyütme |
| --- | --- | --- |
| camera | Küçük düz gökyüzü dolgusu üç yöntemde de tutarlı. | AI kenarları belirginleştirir; General giysi/yüz dokusunu yumuşatır. |
| eagle | Küçük duvar dolgusu tutarlı; kuş nesnesi silinmiyor. | AI kuş/konstrüksiyon kenarlarını keskinleştirir; General daha pürüzsüz. |
| astronaut | Küçük arka plan dolgusu tutarlı. | Yüz/saç keskinleşir; General plastikleşebilir, ince giysi işaretleri değişir. |
| brick | OpenCV derzleri bozar; MI-GAN yer yer çizgiyi kaybeder; LaMa daha tutarlı sürdürür. | Derz çizgileri daha keskin, ancak geometrileri yeniden biçimlenebilir. |
| grass | OpenCV bulanık yama bırakır; AI dolgular dokuyla daha uyumlu. | Yapay keskinlik ve doku üretimi var; özgün detayın geri kazanımı değildir. |
| gravel | OpenCV yumuşak yama; AI dolgu daha dokulu. | AI taş kenarlarını yeniden biçimlendirir; General daha yumuşak. |
| chelsea | OpenCV alın/tüy çizgisini bulandırır; AI dolgular daha uyumlu. | Tüy/göz daha belirgin; ince tüy dokusu değişir, General daha pürüzsüz. |
| clock_motion | Maske düz arka planda, saati silmiyor. | Hareket bulanıklığı sürer; kayıp saat ayrıntısı geri gelmiyor. |
| coffee | OpenCV tabak kenarını dağıtır; LaMa çizgi/kenar devamını daha iyi korur. | Fincan keskinleşir; ahşap dokusu ve küçük parlama şekilleri değişebilir. |
| hubble_deep_field | Küçük maskeli ışık noktaları kaldırılır. | Yıldız/galaksi biçimleri değişebilir; bilimsel doğruluk kabulü değildir. |
| rocket | Küçük gökyüzü dolgusu; roketin tamamı silinmiyor. | x4plus daha dokulu, General daha yumuşak; kule/roket ayrıntıları değişebilir. |
| skin | OpenCV katman çizgisini bozar; AI dolgular daha tutarlı. | Mikroskobik doku değişir; klinik doğruluk kabulü değildir. |

Bu örneklerde boş/bozuk çıktı görülmedi. Doğal çözünürlükte tüm kareyi/tüm
karo sınırlarını incelemeden artefaktsızlık garantisi verilmez.

12 normal kaynak uzun kenarı en fazla 192 piksel olan thumbnaillerdir.
Büyük roket kaynakları küçük orijinalden boyutlandırılır. Sabit 20×20 maske
büyük görüntüde küçük bir gökyüzü alanını işler; büyük nesne silme kalitesi
bu setle kabul edilemez. GPU-only veya kontrollü hızlanma iddiası yoktur.

## Büyük kaynaklar ve teslim

1600×900 tekrarlı testleri geçti. Bu kaynağın iki RealESRGAN 4× çıktısı,
ekrana sığdırılmış tam görünümde kaynakla karşılaştırıldı: roket/kule kenarları
belirginleşiyor, küçük işaretler ve ışık şekilleri değişebiliyor. Boş/bozuk
çıktı gözlenmedi; doğal çözünürlükte tüm karo sınırları incelenmedi.
2400×1350 kaynak, Lanczos ve iki RealESRGAN 4× sonucu da ekrana sığdırılmış görünümde
incelendi. Kenarlar belirginleşirken gökyüzünde hafif ton/doku bantları
seçilebiliyor. Bunun küçük kaynağın boyutlandırılması, inference veya gösterim
ölçeklemesinden hangisine bağlı olduğu bu görünümden ayrıştırılamaz;
doğal çözünürlükte insan incelemesi gerekir. x4plus çizgilerde daha keskin,
General daha yumuşak görünür; küçük roket işaretleri yeniden biçimlenebilir.
Artefaktsızlık kabulü verilmedi.
2400×1350 tekrarlı testleri de geçti; en büyük çıktı 9600×5400 (51.84 MP).
Kapsamlı koşu 20:48:57–21:34:53 UTC, yaklaşık 46 dakika sürdü:
707 passed, 2 beklenen unsupported (SDXL/Swin2SR), başka durum yok.
672 fotoğraf işi ve 721 artefakt oluştu; 685 sonuç PNG'sinin başlık/ölçüleri
raporla ayrıca karşılaştırıldı. ZIP `unzip -tq` ile geçti. SHA-256:
`9d65c1b7928f83e1ad84bb3ea806f69aecbba531e620aa4299f996acb3bee228`.

| 4× büyütme | 1600×900 kaynak | 2400×1350 kaynak |
| --- | --- | --- |
| General x4v3 | 10.11–10.14 sn | 22.14–22.68 sn |
| x4plus | 50.94–51.24 sn | 108.41–108.95 sn |

Bunlar bu koşunun uçtan uca dört tekrar aralığıdır; soğuk başlangıç veya
kontrollü hızlanma ölçümü değildir. Örneklenen motor süreç ağacı tepe RSS
3.818 GiB; tüm uygulamanın mutlak tepe belleği iddiası yoktur.

Teknik kapsamlı koşu ve bu AI destekli inceleme tamamlandı. Kullanıcının kısa
günlük kullanım onayı alınmış olsa da kapsamlı görsellerin nihai insan onayı
ayrıdır ve henüz alınmadı. İptal kanıtı hâlâ sıradaki Lanczos işidir;
çalışan AI silme/büyütmenin ortasında iptal kanıtı bu raporda yoktur.

Yerel rapor/görseller:
`release/macos/1.0.0-rc.4/verification/comprehensive/PixelMend-Test-2026-10-03T20-48-57-928Z-ab6b7efa/`.
Üretilen görseller/ZIP git'e gönderilmez; sonuç JSON'u ve bu inceleme kaydı
metin kanıtı olarak korunur.
