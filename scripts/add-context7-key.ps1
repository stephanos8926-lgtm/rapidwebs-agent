# Add Context7 API key to PowerShell profile
$profilePath = "C:\Users\Bratp\OneDrive\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1"

# Check if the line already exists
$content = Get-Content $profilePath -Raw
if ($content -notmatch 'CONTEXT7_API_KEY') {
    $newLine = "`n`n# Context7 API Key`n`$env:CONTEXT7_API_KEY = 'ctx7sk-015f4b7e-4048-47dc-8d04-09ca6d77b45d'"
    Add-Content -Path $profilePath -Value $newLine
    Write-Host "Context7 API key added to PowerShell profile"
} else {
    Write-Host "Context7 API key already exists in PowerShell profile"
}
