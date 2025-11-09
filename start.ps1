# Picture Frame Startup Script
# Maps Unraid share and starts services

Write-Host "=== Digital Picture Frame Startup ===" -ForegroundColor Cyan

# Map Unraid share with credentials
Write-Host "`nMapping Unraid share..." -ForegroundColor Yellow
$pass = ConvertTo-SecureString "a" -AsPlainText -Force
$cred = New-Object System.Management.Automation.PSCredential("a", $pass)

# Check if already mapped
if (Test-Path Z:\) {
    Write-Host "Z: already mapped" -ForegroundColor Green
} else {
    try {
        New-PSDrive -Name "Z" -PSProvider FileSystem -Root "\\192.168.68.42\stuff" -Credential $cred -Persist | Out-Null
        Write-Host "Z: mapped successfully" -ForegroundColor Green
    } catch {
        Write-Host "Failed to map Z: - $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Continuing anyway..." -ForegroundColor Yellow
    }
}

# Set working directory
Set-Location C:\PictureFrame

# Refresh PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "`nStarting Web UI on http://localhost:5000" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Gray

# Start Flask web UI
python app.py
