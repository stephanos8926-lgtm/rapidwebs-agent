# Update token budget in global Qwen settings
$globalSettingsPath = "C:\Users\Bratp\.qwen\settings.json"

$json = Get-Content $globalSettingsPath -Raw | ConvertFrom-Json

# Update token budget to 50000
if ($json.context.optimization) {
    $json.context.optimization.tokenBudget = 50000
}

$json | ConvertTo-Json -Depth 10 | Set-Content $globalSettingsPath

Write-Host "Token budget updated to 50000 in global settings"
