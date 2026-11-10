# Jarvis kurulumu (Windows). kur-windows.bat dosyasına çift tıklayarak çalıştırın.
$ErrorActionPreference = 'Stop'
$jarvis = Split-Path -Parent $PSScriptRoot
Set-Location $jarvis

function Yaz($metin, $renk = 'White') { Write-Host $metin -ForegroundColor $renk }

function Bul-Python {
    foreach ($aday in @('py -3.12', 'py -3', 'python', 'python3')) {
        $parca = $aday.Split(' ')
        $exe = $parca[0]
        $ek = @($parca | Select-Object -Skip 1)
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
        try {
            $surum = & $exe @ek -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
            if ($LASTEXITCODE -eq 0 -and $surum) {
                $p = $surum.Trim().Split('.')
                if ([int]$p[0] -eq 3 -and [int]$p[1] -ge 10) { return $aday }
            }
        } catch { }
    }
    return $null
}

Yaz "`n=== Jarvis kurulumu ===`n" Cyan

# 1) Python
$python = Bul-Python
if (-not $python) {
    Yaz "Python 3.10 veya daha yenisi bulunamadı. Otomatik kurulmaya çalışılıyor..." Yellow
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
        $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
        $python = Bul-Python
    }
}
if (-not $python) {
    Yaz "Python kurulamadı. Lütfen https://www.python.org/downloads/ adresinden Python 3.12'yi kurun." Red
    Yaz "Kurulumda 'Add python.exe to PATH' kutucuğunu işaretlemeyi unutmayın, sonra bu dosyayı tekrar çalıştırın." Red
    exit 1
}
$pyParca = $python.Split(' ')
$pyExe = $pyParca[0]
$pyEk = @($pyParca | Select-Object -Skip 1)
Yaz "Python bulundu: $(& $pyExe @pyEk --version)" Green

# 2) Sanal ortam ve paketler
$vpy = Join-Path $jarvis '.venv\Scripts\python.exe'
if (-not (Test-Path $vpy)) {
    Yaz "Sanal ortam oluşturuluyor (.venv)..."
    & $pyExe @pyEk -m venv .venv
    if ($LASTEXITCODE -ne 0) { Yaz "Sanal ortam oluşturulamadı." Red; exit 1 }
}
Yaz "Gerekli paketler yükleniyor (birkaç dakika sürebilir)..."
& $vpy -m pip install --upgrade pip --quiet
& $vpy -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Yaz "Paketler yüklenemedi. İnternet bağlantınızı kontrol edip tekrar deneyin." Red; exit 1 }
Yaz "Paketler yüklendi." Green

# 3) Ayarlar (.env)
& $vpy kurulum\ayarla.py bos-mu ANTHROPIC_API_KEY
if ($LASTEXITCODE -eq 0) {
    Yaz "`nJarvis'in çalışması için bir Claude API anahtarı gerekiyor." Cyan
    Yaz "  1) https://console.anthropic.com adresine girin ve hesap açın"
    Yaz "  2) Billing bölümünden kredi yükleyin (kullandıkça ödersiniz)"
    Yaz "  3) Settings > API Keys bölümünden 'Create Key' ile anahtar oluşturun"
    $anahtar = (Read-Host "`nAPI anahtarınızı yapıştırın (sk-ant-... ile başlar, sonra Enter)").Trim()
    if ($anahtar) {
        & $vpy kurulum\ayarla.py ayarla ANTHROPIC_API_KEY $anahtar
        & $vpy kurulum\ayarla.py dogrula
    } else {
        Yaz "Anahtar girilmedi. Daha sonra .env dosyasına ANTHROPIC_API_KEY=... satırını ekleyebilirsiniz." Yellow
    }
}
& $vpy kurulum\ayarla.py bos-mu JARVIS_USER_NAME
if ($LASTEXITCODE -eq 0) {
    $isim = (Read-Host "Jarvis size nasıl hitap etsin? (örn. Ahmet; boş bırakırsanız 'efendim' der)").Trim()
    if ($isim) { & $vpy kurulum\ayarla.py ayarla JARVIS_USER_NAME $isim }
}

# 4) Masaüstü kısayolları
try {
    $masaustu = [Environment]::GetFolderPath('Desktop')
    $ws = New-Object -ComObject WScript.Shell
    $k = $ws.CreateShortcut((Join-Path $masaustu 'Jarvis.lnk'))
    $k.TargetPath = Join-Path $jarvis 'jarvis-baslat.bat'
    $k.WorkingDirectory = $jarvis
    $k.Description = 'Jarvis - sesli asistan'
    $k.Save()
    $k2 = $ws.CreateShortcut((Join-Path $masaustu 'Jarvis (Yazı).lnk'))
    $k2.TargetPath = Join-Path $jarvis 'jarvis-baslat.bat'
    $k2.Arguments = '--yazi'
    $k2.WorkingDirectory = $jarvis
    $k2.Description = 'Jarvis - yazarak konuşma'
    $k2.Save()
    Yaz "Masaüstüne 'Jarvis' ve 'Jarvis (Yazı)' kısayolları eklendi." Green
} catch {
    Yaz "Masaüstü kısayolu oluşturulamadı; Jarvis'i jarvis-baslat.bat ile açabilirsiniz." Yellow
}

Yaz "`n=== Kurulum tamamlandı! ===" Cyan
$cevap = Read-Host "Hoparlör ve mikrofon testi yapılsın mı? (E/H)"
if ($cevap -match '^[eEyY]') { & $vpy jarvis.py --ses-testi }
Yaz "`nJarvis'i başlatmak için masaüstündeki 'Jarvis' kısayoluna çift tıklayın." Green
