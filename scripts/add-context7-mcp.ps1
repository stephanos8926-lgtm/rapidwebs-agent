# Add Context7 MCP server to global Qwen settings
$globalSettingsPath = "C:\Users\Bratp\.qwen\settings.json"

$json = Get-Content $globalSettingsPath -Raw | ConvertFrom-Json

# Add context7 MCP server if not exists
if (-not $json.mcpServers.context7) {
    $context7Config = [PSCustomObject]@{
        command = "npx"
        args = @("-y", "@context7/mcp-server")
        timeout = 30000
        trust = $true
        env = [PSCustomObject]@{
            CONTEXT7_API_KEY = '${env:CONTEXT7_API_KEY}'
        }
    }
    $json.mcpServers | Add-Member -NotePropertyName 'context7' -NotePropertyValue $context7Config
}

# Add context7 to allowed MCP list if not exists
if ('context7' -notin $json.mcp.allowed) {
    $json.mcp.allowed += 'context7'
}

$json | ConvertTo-Json -Depth 10 | Set-Content $globalSettingsPath

Write-Host "Context7 MCP server added to global Qwen settings"
