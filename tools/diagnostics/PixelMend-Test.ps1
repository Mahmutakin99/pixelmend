$ErrorActionPreference = 'Stop'
$desktop = [Environment]::GetFolderPath('DesktopDirectory')
if ($env:PIXELMEND_DIAGNOSTIC_OUTPUT) { $desktop = $env:PIXELMEND_DIAGNOSTIC_OUTPUT }
$fallback = $null
try {
    $stamp = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + $PID
    $fallback = Join-Path $desktop ("PixelMend-Test-Baslangic-" + $stamp + '.txt')
    'PixelMend testi baslatiliyor. Bu dosya kalirsa ayni zamandaki ZIP veya kismi rapor klasorunu da kontrol edin.' | Set-Content -LiteralPath $fallback -Encoding UTF8
    $app = $env:PIXELMEND_TEST_APP
    if (-not $app) {
        $candidates = @(
            (Join-Path $env:LOCALAPPDATA 'Programs\pixelmend\PixelMend.exe'),
            (Join-Path $env:LOCALAPPDATA 'Programs\PixelMend\PixelMend.exe'),
            (Join-Path $env:ProgramFiles 'PixelMend\PixelMend.exe')
        )
        $app = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    }
    if (-not $app -or -not (Test-Path -LiteralPath $app -PathType Leaf)) {
        Add-Type -AssemblyName System.Windows.Forms
        $picker = New-Object System.Windows.Forms.OpenFileDialog
        $picker.Title = 'PixelMend.exe dosyasini secin'
        $picker.Filter = 'PixelMend|PixelMend.exe'
        if ($picker.ShowDialog() -ne 'OK') { throw 'Application selection cancelled' }
        $app = $picker.FileName
    }
    $env:PIXELMEND_DIAGNOSTIC_OUTPUT = $desktop
    $process = Start-Process -FilePath $app -ArgumentList '--self-test' -PassThru -Wait
    $code = $process.ExitCode
    $created = (Get-Item -LiteralPath $fallback).LastWriteTimeUtc
    $zip = Get-ChildItem -LiteralPath $desktop -Filter 'PixelMend-Test-*.zip' | Where-Object { $_.LastWriteTimeUtc -gt $created } | Select-Object -First 1
    if (($code -eq 0 -or $code -eq 2) -and $zip) { Remove-Item -LiteralPath $fallback }
    else { "Uygulama cikis kodu: $code. Varsa ZIP/kismi raporu da paylasin." | Add-Content -LiteralPath $fallback -Encoding UTF8 }
    if (-not $zip) { 'Bu calistirmada ZIP bulunamadi. Uygulama surumu test paketini desteklemiyor olabilir.' | Add-Content -LiteralPath $fallback -Encoding UTF8; $code=1 }
    Write-Host 'Rapor Masaustu klasorune kaydedildi. Dosyalar otomatik gonderilmez.'
    exit $code
} catch {
    if ($fallback) {
        try { 'Uygulama baslatilamadi. Kurulumu, calistirma izinlerini ve Masaustu yazma iznini kontrol edin.' | Add-Content -LiteralPath $fallback -Encoding UTF8 } catch {}
    }
    Write-Host 'Test baslatilamadi. Masaustu yazilabilir degilse PIXELMEND_DIAGNOSTIC_OUTPUT ile yazilabilir bir rapor klasoru belirtin.'
    Read-Host 'Kapatmak icin Enter'
    exit 1
}
