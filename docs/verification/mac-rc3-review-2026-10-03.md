# macOS rc.3 — kullanıcı koşuları ve görsel inceleme

Karar: dört temel model ve mevcut teknik testler bu M4 Mac'te geçti.
12 fotoğrafın AI destekli görsel incelemesi tamamlandı; kullanıcının kendi
fotoğrafıyla nesne silme, 2× büyütme ve kaydetme değerlendirmesi bekleniyor.
Bu kayıt tek başına tüm fotoğraflar ve tüm Mac modelleri için kalite kabulü değildir.

## Rapor kanıtı

İki koşu da 1.0.0-rc.3 / darwin / arm64, Apple M4, 16 GB RAM üzerindedir.
Kaynak ZIP ve açılmış rapor klasörleri kullanıcının Masaüstündedir.

| Koşu | Rapor kimliği | Geçti | Desteklenmiyor | Başarısız |
| --- | --- | ---: | ---: | ---: |
| Standart | f057d063 | 21 | 2 | 0 |
| Kapsamlı | 81cb6208 | 707 | 2 | 0 |

Kapsamlı koşu 17:05:49–17:51:46 UTC (yaklaşık 46 dakika), 709 rapor satırı,
672 fotoğraf işi ve 721 artefakt içerir. Her iki ZIP `unzip -tq` ile doğrulandı.
Raporun `incomplete` olmasının tek nedeni SDXL ve Swin2SR'nin beklenen
`unsupported` satırlarıdır; hiçbir temel model kurulum/çalışma hatası yoktur.

- Standart ZIP SHA-256: `f78878edcbda5cbe20c9922ffc38da9c5bec2a2984432233bd3929b6e73b4883`.
- Kapsamlı ZIP SHA-256: `314b047e66947d17d5340c44d4d800f46af59d8fd4ad1d42bcbf2dd94c6358e7`.

MI-GAN ve LaMa CPU'da; iki RealESRGAN otomatik yolunda Core ML, ayrıca
zorunlu CPU koşularında CPU'da geçti. Core ML seçimi GPU-only çalışmayı kanıtlamaz.
Boyut/alfa doğrulamalarında ve silmede maske dışı piksel eşitliğinde yanlış
sonuç yoktur. UI, PNG kayıt, proje kayıt/açma ve motor kapanması geçti.
İptal kanıtı sıradaki Lanczos işinin iptalidir; çalışan yerel AI silme/büyütme
işinin ortasında iptal edilmesine dair ayrı kanıt bu koşularda yoktur.

Örneklenen motor süreç ağacı tepe RSS: 2.734 GiB. Bu örneklemeli ölçümdür;
uygulamanın tüm süreçlerinin mutlak tepe belleği olarak yorumlanmamalıdır.

## Görsel yöntem ve bulgular

12 fotoğrafta kaynak ile OpenCV/MI-GAN/LaMa silme çıktıları, Lanczos ve iki
RealESRGAN'ın 1×/2×/4× çıktıları karşılaştırıldı. İlk ölçümün (`repeat=0`)
görselleri kullanıldı; diğer üç tekrarın tamamı teknik kontrolden geçti,
her tekrarın her pikseli ayrıca gözle incelenmedi.

Silmede sabit maskenin çevresi 60×60 kesitle, 4× büyütmeler tam görünüm ve
240×240 doğal çözünürlük kesitleriyle incelendi. Büyük roket çıktılarından
720×520 doğal kesitler de alındı. Karşılaştırma levhaları
[`visual-review`](../../release/macos/1.0.0-rc.3/verification/visual-review/)
altındadır. Orijinal rapor görüntüleri değiştirilmedi.

| Fotoğraf | Silme gözlemi | Büyütme gözlemi |
| --- | --- | --- |
| camera | Düz arka planda üç yöntem de kullanılabilir. | AI kenarları temizler; General giysi/saç dokusunu daha çok yumuşatır. |
| eagle | Küçük duvar alanı kabul edilebilir; zor nesne seçimi değil. | Kuş ve konstrüksiyon sınırları belirginleşir, duvar/zemin dokusu değişir. |
| astronaut | Küçük arka plan alanı düzgün tamamlanır. | Yüz, saç ve kıyafet daha keskin; General daha plastik, x4plus daha dokulu. |
| brick | OpenCV derzleri dağıtır; MI-GAN çizgiyi kısmen kaybeder; LaMa en iyi devamı sağlar. | Derzler keskinleşir; doğrusal kenarlar yeniden biçimlenebilir. |
| grass | OpenCV belirgin bulanık yama; LaMa/MI-GAN daha iyi doku. | İki AI da yapay keskinlik/doku üretir; birebir detay geri kazanımı değildir. |
| gravel | OpenCV yumuşak yama; AI silmeler daha doğal doku. | Taş sınırları çok keskinleşir; şekillerin özgünlüğü garanti edilmez. |
| chelsea | OpenCV alın/tüy çizgisini bulandırır; LaMa/MI-GAN daha iyi fakat ince tüy değişebilir. | Göz/tüy daha belirgin; General daha yumuşak, x4plus daha dokulu. |
| clock_motion | Maske düz arka plandadır, saat nesnesini silmez. | Hareket bulanıklığı sürer; AI kayıp saat detayını geri getirmiyor. |
| coffee | OpenCV tabak kenarını bozar; LaMa ahşap çizgisi ve kenarı daha iyi sürdürür. | Fincan/ahşap daha keskin; General ahşap dokusunu yumuşatır. |
| hubble_deep_field | Maskedeki yıldız/ışık noktaları kaldırılır. | Yıldız şekli/parlaklığı değişebilir; bilimsel ayrıntı doğruluğu kabulü değildir. |
| rocket | Thumbnail maskesi çoğunlukla gökyüzündedir. | Kule/roket kenarları belirgin; küçük işaretler şekil değiştirebilir. |
| skin | OpenCV katman sınırını bozar; LaMa/MI-GAN daha tutarlı küçük dolgu. | Mikroskopik doku yeniden biçimlenir; klinik doğruluk kabulü değildir. |

İncelenen kesitlerde belirgin sert karo birleşim çizgisi ya da bozuk/boş çıktı
görülmedi. Bütün büyük çıktı piksellerinde artefakt olmadığı veya tam-kare
inference ile sayısal eşdeğerlik iddiası yoktur.

## Büyük iş kanıtı ve sınırlar

1600×900 ve 2400×1350 roket kaynakları bütün yöntemler, ölçekler ve dört
tekrar boyunca geçti. En büyük 4× çıktı 9600×5400 (51.84 MP).

| 4× büyütme | 1600×900 kaynak | 2400×1350 kaynak |
| --- | --- | --- |
| RealESRGAN General x4v3 | 10.33–10.35 sn | 22.42–22.69 sn |
| RealESRGAN x4plus | 49.75–51.07 sn | 106.45–106.77 sn |

Bunlar bu koşunun uçtan uca süreleridir; bağımsız soğuk başlangıç veya
kontrollü CPU/Core ML hızlanma karşılaştırması değildir.

Önemli kapsam sınırları:

- 12 normal kaynak uzun kenarı en fazla 192 piksel olan thumbnaillerdir.
- Büyük roket kaynakları 640×427 orijinalden Lanczos ile büyütülmüştür;
  doğal yüksek çözünürlüklü bir fotoğrafın ayrıntı kabulü değildir.
- Silme maskesi her boyutta `x=38..57, y=22..41` (20×20 piksel) kalır.
  Büyük kaynakta küçük bir gökyüzü bölgesidir. Büyük nesne silme kalitesi bu
  rapordan çıkarılamaz; tam roket nesnesi silinmemiştir.

Bu nedenle kullanıcının kendi fotoğrafında gerçek bir nesne seçimi ve 2×
büyütme sonucu, mevcut testleri tamamlayan son günlük kullanım kanıtıdır.

## Teslim kararı

rc.3 yerel test sürümü için dört temel modelin çalışma ve mevcut fotoğraf
karşılaştırmaları olumlu. Kullanıcı normal kullanım sonucu gelene kadar
nihai ortak kabul beklemede. Developer ID imzası/notarization da mevcut değil.
Bu incelemede uygulama veya model dosyaları değiştirilmedi.
