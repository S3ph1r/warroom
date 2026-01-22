
$source = "d:\Download\Progetto WAR ROOM\warroom"
$dest = "g:\Il mio Drive\WAR_ROOM_DATA\Backup_Code_2025_12_22"

Write-Host "🚀 Starting Backup from $source to $dest"

# Create destination folder
if (!(Test-Path -Path $dest)) {
    New-Item -ItemType Directory -Path $dest | Out-Null
    Write-Host "Created destination directory."
}

# Define exclusion list
$exclude = @("node_modules", "venv", "__pycache__", ".git", ".svelte-kit", ".env")

# Function to copy with exclusion
Get-ChildItem -Path $source -Recurse | Where-Object {
    $path = $_.FullName
    $skip = $false
    foreach ($ex in $exclude) {
        if ($path -match "\\$ex\\?" -or $path -match "\\$ex$") {
            $skip = $true
            break
        }
    }
    if (-not $skip) {
        return $true
    }
} | Copy-Item -Destination {
    $relativePath = $_.FullName.Substring($source.Length)
    $targetPath = Join-Path $dest $relativePath
    $targetDir = Split-Path $targetPath
    if (!(Test-Path $targetDir)) {
        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    }
    return $targetPath
} -Force

Write-Host "✅ Backup Complete!"
