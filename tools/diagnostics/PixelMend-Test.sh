#!/bin/sh
set -u
test_app=${1:-}
test_desktop=${PIXELMEND_DIAGNOSTIC_OUTPUT:-}
test_system=$(uname -s)
test_launcher_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -z "$test_desktop" ]; then
  if [ "$test_system" = Darwin ]; then test_desktop="$HOME/Desktop"
  elif command -v xdg-user-dir >/dev/null 2>&1; then test_desktop=$(xdg-user-dir DESKTOP)
  else test_desktop="$HOME/Desktop"; fi
fi
if [ ! -d "$test_desktop" ] || [ ! -w "$test_desktop" ]; then
  printf 'Masaüstü yazılabilir değil. Rapor klasörünün tam yolunu yazın: '
  IFS= read -r test_desktop
fi
if [ ! -d "$test_desktop" ] || [ ! -w "$test_desktop" ]; then printf 'Rapor klasörüne yazılamıyor. Test başlatılmadı.\n' >&2; exit 1; fi
test_stamp=$(date '+%Y%m%d-%H%M%S')-$$
test_fallback="$test_desktop/PixelMend-Test-Baslangic-$test_stamp.txt"
printf 'PixelMend testi başlatılıyor. Bu dosya kalırsa uygulama başlamamış veya beklenmeden kapanmış olabilir. Aynı zamandaki PixelMend-Test klasöründe kısmi sonuçları kontrol edin.\n' > "$test_fallback"
nearby_appimages() { find "$test_launcher_dir" "$(dirname "$test_launcher_dir")" -maxdepth 1 -type f -name '*.AppImage' -print 2>/dev/null | sort -u; }
if [ -z "$test_app" ]; then test_app=${PIXELMEND_TEST_APP:-}; fi
if [ -z "$test_app" ]; then
  if [ "$test_system" = Darwin ]; then
    test_app=/Applications/PixelMend.app/Contents/MacOS/PixelMend
    if [ ! -x "$test_app" ]; then test_app="$HOME/Applications/PixelMend.app/Contents/MacOS/PixelMend"; fi
  else
    test_app=$(command -v pixelmend 2>/dev/null || true)
    if [ -z "$test_app" ] && [ -x /opt/PixelMend/pixelmend ]; then test_app=/opt/PixelMend/pixelmend; fi
    if [ -z "$test_app" ]; then
      test_appimages=$(nearby_appimages); test_appimage_count=$(printf '%s\n' "$test_appimages" | sed '/^$/d' | wc -l | tr -d ' ')
      if [ "$test_appimage_count" = 1 ]; then test_app=$(printf '%s\n' "$test_appimages")
      elif [ "$test_appimage_count" -gt 1 ]; then printf 'Birden fazla AppImage bulundu; otomatik seçim yapılmadı. Tam yolu yazın:\n%s\n' "$test_appimages" >&2; fi
    fi
  fi
fi
if [ -d "$test_app" ] && [ "$test_system" = Darwin ]; then test_app="$test_app/Contents/MacOS/PixelMend"; fi
if [ -z "$test_app" ] || [ ! -f "$test_app" ]; then printf 'PixelMend çalıştırılabilir dosyasının tam yolunu yazın (Linux: AppImage veya kurulu uygulama): '; IFS= read -r test_app; fi
printf 'Seçilen uygulama: %s\nİşletim sistemi: %s\n' "${test_app:-belirlenemedi}" "$test_system" >> "$test_fallback"
if [ ! -f "$test_app" ] || [ ! -x "$test_app" ]; then
  if [ -n "$test_app" ] && [ -f "$test_app" ] && [ "$test_system" = Linux ]; then test_quoted=$(printf '%s' "$test_app" | sed "s/'/'\\\\''/g"); printf "Uygulama çalıştırılabilir değil. İzin: %s. Çözüm: chmod +x -- '%s'\n" "$(ls -ld "$test_app" 2>/dev/null || true)" "$test_quoted" >> "$test_fallback"
  else printf 'Uygulama bulunamadı. PixelMend kurulumu ve seçilen dosyanın izinleri kontrol edilmeli.\n' >> "$test_fallback"; fi
  printf 'Başlangıç raporu: %s\n' "$test_fallback"; exit 1
fi
printf 'Test penceresinde kapsamı seçin. Sonuçlar Masaüstü’ne kaydedilecek.\n'
if [ "${PIXELMEND_DIAGNOSTIC_NO_SANDBOX:-}" = 1 ]; then PIXELMEND_DIAGNOSTIC_OUTPUT="$test_desktop" "$test_app" --self-test --no-sandbox
else PIXELMEND_DIAGNOSTIC_OUTPUT="$test_desktop" "$test_app" --self-test; fi
test_code=$?
test_zip=$(find "$test_desktop" -maxdepth 1 -type f -name 'PixelMend-Test-*.zip' -newer "$test_fallback" -print -quit)
if { [ "$test_code" -eq 0 ] || [ "$test_code" -eq 2 ]; } && [ -n "$test_zip" ]; then rm -f "$test_fallback"
else
  printf 'Uygulama çıkış kodu: %s. Varsa aynı zamandaki ZIP/kısmi rapor klasörünü de paylaşın. Kişisel fotoğraflarınızı göndermeyin.\n' "$test_code" >> "$test_fallback"
  if [ -z "$test_zip" ]; then printf 'Bu çalıştırmada ZIP raporu bulunamadı. Uygulama sürümü test paketini desteklemiyor olabilir.\n' >> "$test_fallback"; test_code=1; fi
fi
printf 'Rapor klasörü: %s\n' "$test_desktop"; exit "$test_code"
