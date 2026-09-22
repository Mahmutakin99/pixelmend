# PixelMend test paketi

1. Bu test paketiyle aynı sürüm PixelMend'i kurun. Açık çalışmanızı kaydedip
   PixelMend'i kapatın. Eski sürümler `--self-test` modunu desteklemez.
2. Windows'ta **PixelMend-Test.cmd**, Mac'te **PixelMend-Test.command** dosyasını
   açın. Linux'ta terminalden `sh PixelMend-Test.sh /tam/yol/PixelMend.AppImage`
   çalıştırın. AppImage'in çalıştırma izni olmalıdır.
3. Standart testi seçin. Eksik modellerin indirilmesi isteğe bağlıdır; boyut
   pencerede gösterilir. Kapsamlı fotoğraf karşılaştırmaları uzun sürebilir.
4. Testin sonunda isteğe bağlı görüşünüzü yazın, **Notları rapora ekle** ve
   **Raporu klasörde göster** düğmelerini kullanın.
5. Masaüstü'ndeki `PixelMend-Test-….zip` dosyasını testi isteyen kişiye iletin.
   Dosya kendiliğinden internete gönderilmez.

ZIP üretilemez veya uygulama çökerse aynı zamandaki `PixelMend-Test-…` klasörünü
ve varsa `PixelMend-Test-Baslangic-….txt` dosyasını paylaşın. Raporunuzun içinde
kişisel bilgi olmadığını kontrol edin. Ekran görüntüleri yalnız test örneklerinin
açıldığı uygulama penceresinden alınır; masaüstünüz görüntülenmez.

macOS/Linux test dosyasını terminalden `sh /tam/yol/PixelMend-Test.command`
ile de çalıştırabilirsiniz. İşletim sisteminin güvenlik ayarlarını topluca
devre dışı bırakmanız gerekmez. Kurulum engelleniyorsa gördüğünüz uyarıyı bildirin.

Çıkış kodları: 0 = seçilen testler geçti, 1 = hata, 2 = eksik/iptal edilmiş
doğrulama, 3 = başka PixelMend oturumu açık. Eksik modeller başarı sayılmaz.

## Arayüzü ayrıca değerlendirin

- Görsel açma, çizim, nesne seçimi, önizleme ve kaydetme anlaşılır mı?
- Küçük pencerede ve açık/koyu temada taşan, kesilen veya okunmayan alan var mı?
- Fare/fırça halkası görünüyor mu? Klavyeyle kontrollere erişilebiliyor mu?
- Önce/sonra sonuçlarında doku, yüz, yazı, renk, kenar veya karo izi sorunu var mı?

Hangi adımı yaptığınızı, ne beklediğinizi ve ne olduğunu notlara yazın.
Otomatik teknik testler insanın görsel kalite değerlendirmesinin yerine geçmez.
