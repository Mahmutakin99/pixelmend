# PixelMend Windows ve Linux test yönergesi

Bu metni test edecek kişiye olduğu gibi gönderin. Kişisel fotoğraf kullanmayın;
uygulama kendi örnek görselleriyle test yapar.

## Gönderilecek dosyalar

Her testçiye iki şey gönderin:

1. İşletim sistemine uygun PixelMend kurulum paketi.
2. Aynı sürümün `test-kit` klasörü. Bu klasörde `PixelMend-Test.cmd` (Windows)
   ve `PixelMend-Test.sh` (Linux) bulunur.

Model dosyalarını ayrıca göndermeyin. Test ekranındaki **Eksik modelleri indir**
seçeneği, kullanılabilir modelleri resmi kaynaktan indirir ve doğrular.

## Windows

1. `PixelMend-...-Setup.exe` dosyasını kurun.
2. `test-kit` klasöründeki `PixelMend-Test.cmd` dosyasına çift tıklayın.
3. Açılan PixelMend test penceresinde **Eksik modelleri indir** kutusunu işaretleyin.
4. **Standart testi başlat** seçeneğine basın ve bitmesini bekleyin.
5. Test bitince not alanına bilgisayarın ekran kartını ve görülen sorunu yazın.
6. **Notları rapora ekle** düğmesine basın.
7. Masaüstündeki yeni `PixelMend-Test-....zip` dosyasını bana gönderin.

## Linux

AppImage gönderildiyse terminal açın ve dosyaların bulunduğu klasörde şunları çalıştırın:

```sh
chmod +x PixelMend-*.AppImage test-kit/PixelMend-Test.sh
sh test-kit/PixelMend-Test.sh "$(pwd)"/PixelMend-*.AppImage
```

Sonra açılan test penceresinde Windows'taki 3–7. adımları uygulayın. Rapor
Masaüstüne `PixelMend-Test-....zip` olarak kaydedilir.

`.deb` gönderildiyse önce paketi dağıtımın yazılım yükleyicisiyle kurun; sonra:

```sh
sh test-kit/PixelMend-Test.sh
```

Uygulama bulunamazsa betik PixelMend çalıştırılabilir dosyasının tam yolunu ister.

## Bana ne gönderecekler?

- Önce yalnız `PixelMend-Test-....zip` raporu.
- ZIP oluşmadıysa, aynı tarih-saatli `PixelMend-Test-...` klasörünü ve
  `PixelMend-Test-Baslangic-....txt` dosyasını birlikte göndersinler.
- Ayrıca kısa mesaj olarak: işletim sistemi sürümü, RAM miktarı, varsa ekran
  kartı adı ve gördükleri hata ekranının görüntüsü.

ZIP raporu kişisel fotoğrafları veya tam dosya yollarını içermez. Test başarısız
olursa raporu yine gönderin; başarısızlık nedeni orada bulunur.
