# PixelMend bilgisayar testi — Linux

Bu test dört zorunlu modeli, “yakında” modelleri, AI silme/büyütme iptalini, kaynak bırakmayı, maske/alfa ile proje/kaydetme akışlarını ve rapor görsellerini doğrular. Kişisel fotoğraf açmayın.

## AppImage

1. `PixelMend-....AppImage` ve `test-kit` klasörünü aynı klasöre indirin.
2. Terminalde şunları çalıştırın:

```sh
chmod +x PixelMend-*.AppImage test-kit/PixelMend-Test.sh
sh test-kit/PixelMend-Test.sh
```

Betik tek AppImage'ı bulur; birden fazlası varsa tam yolu argüman olarak verin.

## DEB

1. `PixelMend-....deb` paketini dağıtımınızın paket yükleyicisiyle kurun.
2. `test-kit` klasöründe `sh PixelMend-Test.sh` çalıştırın.

Önce **Standart test**i çalıştırın. Ardından bilgisayar boşta iken **Kapsamlı test**i ayrı çalıştırın: bu koşu 12 lisanslı fotoğraf, 1×/2×/4× büyütme ile 1600×900 ve izin varsa 2400×1350 görselleri kapsar ve saatler sürebilir. Her iki koşunun ZIP dosyasını gönderin. Kapsamlı ZIP içindeki görsellerin insan tarafından incelenmesi, Linux kalite kabulü için zorunludur.

ZIP oluşmazsa aynı tarih-saatli ZIP (varsa), kısmi `PixelMend-Test-...` klasörü ve `PixelMend-Test-Baslangic-....txt` dosyasını birlikte gönderin. Rapor kendiliğinden internete gönderilmez.
