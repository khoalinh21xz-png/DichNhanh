$ErrorActionPreference = "Continue"
Write-Host "== Cài đặt DichNhanh ==" -ForegroundColor Cyan
$ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue) -and -not (Test-Path $ollama)) {
  Write-Host "Chưa có Ollama, đang cài..."
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    winget install -e --id Ollama.Ollama --accept-source-agreements --accept-package-agreements
  } else {
    $f = "$env:TEMP\OllamaSetup.exe"
    Invoke-WebRequest "https://ollama.com/download/OllamaSetup.exe" -OutFile $f
    Start-Process $f -ArgumentList "/VERYSILENT" -Wait
  }
} else { Write-Host "Đã có Ollama." }
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { $env:Path += ";$env:LOCALAPPDATA\Programs\Ollama" }
Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue
Start-Sleep 3
$vram = 0
try { $q = Get-ItemProperty "HKLM:\SYSTEM\ControlSet001\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0*" -ErrorAction SilentlyContinue | Where-Object { $_."HardwareInformation.qwMemorySize" } | ForEach-Object { [int64]$_."HardwareInformation.qwMemorySize" }; if ($q) { $vram = [math]::Round((($q | Measure-Object -Maximum).Maximum) / 1GB) } } catch {}
Write-Host "VRAM card đồ họa: $vram GB"
$model = "gemma3:12b"
if ($vram -gt 0 -and $vram -lt 8) {
  $a = Read-Host "Card dưới 8GB, nên dùng bản nhẹ gemma3:4b. Tải bản 4b? (Y/n)"
  if ($a -ne "n") { $model = "gemma3:4b" }
}
Write-Host "Đang tải model $model (vài GB, chờ chút)..."
ollama pull $model
if ($model -eq "gemma3:4b") {
  $cfgDir = "$env:APPDATA\DichNhanh"; New-Item -ItemType Directory -Force $cfgDir | Out-Null
  '{"model": "gemma3:4b"}' | Set-Content "$cfgDir\config.json" -Encoding ASCII
}
Write-Host "Xong! Mở DichNhanh.exe là dùng được. Đọc HuongDan.txt để biết phím tắt." -ForegroundColor Green
