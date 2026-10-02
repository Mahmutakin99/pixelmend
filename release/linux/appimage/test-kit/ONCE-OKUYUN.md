# PixelMend bilgisayar testi — testçiye gönderilecek yönerge

Bu klasör PixelMend uygulamasını test eder. **Önce PixelMend’i kurun**, sonra bu klasördeki test dosyasını çalıştırın. Kişisel fotoğraf açmayın; test kendi örnek görsellerini kullanır.

## Windows

1. `PixelMend-...-Setup.exe` dosyasını çalıştırın ve kurulumu bitirin.
2. Uygulama açıksa kapatın.
3. Bu klasördeki **`PixelMend-Test.cmd`** dosyasına çift tıklayın.
4. Uygulama bulunamazsa açılan pencereden kurduğunuz `PixelMend.exe` dosyasını seçin. Bu normaldir.
5. Açılan **PixelMend · Bilgisayar testi** penceresinde:
   - **Standart test** seçili kalsın.
   - **Eksik modelleri indir** kutusunu işaretleyin.
   - **Testi başlat** düğmesine basın.
6. Test bitene kadar pencereyi kapatmayın. Bitince not alanına varsa hata, ekran kartı adı ve ne yaptığınızı yazın; **Notları rapora ekle** düğmesine basın. Sonra **Raporu klasörde göster** düğmesine basın.
7. Test penceresini kapatın. Masaüstünde şu dosya oluşur: `PixelMend-Test-YYYY-AA-GG....zip`
8. Bu ZIP dosyasını testi isteyen kişiye gönderin. WhatsApp, e-posta veya Drive bağlantısı kullanılabilir. Dosya büyükse Drive bağlantısı gönderin.

## Linux — AppImage

1. `PixelMend-....AppImage` ve bu `test-kit` klasörünü aynı bilgisayara indirin.
2. Terminal açın ve iki dosyanın bulunduğu klasöre gidin.
3. Şunları çalıştırın:

```sh
chmod +x PixelMend-*.AppImage test-kit/PixelMend-Test.sh
sh test-kit/PixelMend-Test.sh "$(pwd)"/PixelMend-*.AppImage
```

4. Açılan test penceresinde Windows bölümündeki 5–8. adımları uygulayın. Rapor Masaüstünde `PixelMend-Test-....zip` adıyla oluşur.

## Linux — DEB

1. `PixelMend-....deb` dosyasını dağıtımınızın paket yükleyicisiyle kurun.
2. Terminalde `test-kit` klasörüne gidin ve çalıştırın:

```sh
sh PixelMend-Test.sh
```

3. Uygulama bulunamazsa betik PixelMend çalıştırılabilir dosyasının tam yolunu ister. Sonra yukarıdaki test adımlarını izleyin.

## ZIP oluşmadıysa veya test hata verirse

Masaüstünde aynı tarih-saatli şu öğeleri bulun ve **üçünü birlikte** gönderin:

1. `PixelMend-Test-....zip` varsa onu,
2. `PixelMend-Test-....` klasörünü,
3. `PixelMend-Test-Baslangic-....txt` dosyasını.

Ayrıca kısa bir mesajla işletim sistemi sürümünü, RAM miktarını, ekran kartı adını ve görülen hata ekranının görüntüsünü gönderin. Güçlü modellerin “yakında/desteklenmiyor” görünmesi bu sürüm için beklenen durumdur; rapor kullanılabilir temel modellerin gerçekten çalışıp çalışmadığını gösterir.

Rapor kendiliğinden internete gönderilmez. ZIP, test görsellerini ve teknik sonuçları içerir; kişisel fotoğraf veya tam dosya yolu içermez.
