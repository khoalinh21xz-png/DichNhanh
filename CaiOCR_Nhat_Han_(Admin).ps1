# Chay bang chuot phai > Run with PowerShell (Admin) de cai goi OCR Nhat/Han
Add-WindowsCapability -Online -Name "Language.OCR~~~ja-JP~0.0.1.0"
Add-WindowsCapability -Online -Name "Language.OCR~~~ko-KR~0.0.1.0"
Add-WindowsCapability -Online -Name "Language.OCR~~~zh-TW~0.0.1.0"
Write-Host "Xong. Khoi dong lai DichNhanh." ; pause
