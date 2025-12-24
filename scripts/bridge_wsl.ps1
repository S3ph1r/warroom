
$wsl_ip = (wsl hostname -I).Trim()
if (-not $wsl_ip) {
    Write-Host "Error: Could not detect WSL IP." -ForegroundColor Red
    exit 1
}

Write-Host "Found WSL IP: $wsl_ip" -ForegroundColor Green
Write-Host "Configuring PortProxy for 127.0.0.1:11434 -> $wsl_ip`:11434..."

# Remove old rule if exists
netsh interface portproxy delete v4tov4 listenaddress=127.0.0.1 listenport=11434 | Out-Null

# Add new rule
# Note: This requires Admin privileges. If it fails, we catch it.
try {
    Start-Process netsh -ArgumentList "interface portproxy add v4tov4 listenaddress=127.0.0.1 listenport=11434 connectaddress=$wsl_ip connectport=11434" -Verb RunAs -Wait
    Write-Host "✅ PortProxy Rule Updated." -ForegroundColor Green
}
catch {
    Write-Host "⚠️ Failed to set PortProxy. Ensure you are running as Admin." -ForegroundColor Yellow
}
