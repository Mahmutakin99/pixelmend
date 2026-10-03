# PixelMend 1.0.0-rc.4 — Mac Apple Silicon

DMG ve ZIP aynı ARM64 uygulamayı içerir. Developer ID imzası ve notarizasyon
yoktur; macOS engellerse bu uygulama için Gizlilik ve Güvenlik bölümündeki
açma seçeneğini kullanın. Genel sistem güvenliğini kapatmayın.

Normal pencere model sınamalarını beklemeden açılır. Modeller arka planda
sırayla hazırlanırken görsel açma, çizim, OpenCV ve Lanczos kullanılabilir.
Her AI modeli yalnız kendi sınaması tamamlandığında kullanılabilir.
Modellerinizi tekrar indirmeniz gerekmez.

## Kısa kullanıcı kontrolü

1. Uygulamayı kapatıp yeniden açın. Pencere hızlı geliyor mu?
2. Modeller hazırlanırken bir fotoğraf açın ve üzerine çizim yapın.
3. LaMa hazır olunca gerçek bir nesneyi işaretleyip silin; sonucu inceleyin.
4. 2× büyütme deneyin; hangi yöntemi seçtiğinizi not edin.
5. PNG kaydedin ve kaydedilen dosyayı açın; uygulamayı kapatıp tekrar açın.

Takılma, hata veya görüntü bozulması varsa hangi adımda olduğunu bildirin.
Kapsamlı test: `test-kit/PixelMend-Test.command` ile bilgisayar boşta iken
Kapsamlı modu çalıştırın. Yeni rc.4 ZIP'ini ve görsel değerlendirmenizi paylaşın.
rc.3 raporları rc.4 nihai kalite kabulü yerine geçmez.
