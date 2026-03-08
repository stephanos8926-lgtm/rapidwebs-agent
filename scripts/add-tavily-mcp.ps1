# Add Tavily MCP server to global Qwen settings
$globalSettingsPath = "C:\Users\Bratp\.qwen\settings.json"

$json = Get-Content $globalSettingsPath -Raw | ConvertFrom-Json

# Add tavily-search MCP server if not exists
if (-not $json.mcpServers.'tavily-search') {
    $tavilyConfig = [PSCustomObject]@{
        command = "npx"
        args = @("-y", "@tavily/mcp-server")
        timeout = 30000
        trust = $true
        env = [PSCustomObject]@{
            TAVILY_API_KEY = '${env:TAVILY_API_KEY}'
        }
    }
    $json.mcpServers | Add-Member -NotePropertyName 'tavily-search' -NotePropertyValue $tavilyConfig
}

# Add tavily-search to allowed MCP list if not exists
if ('tavily-search' -notin $json.mcp.allowed) {
    $json.mcp.allowed += 'tavily-search'
}

# Remove old webSearch section if exists (not needed with MCP)
if ($json.PSObject.Properties.Name -contains 'webSearch') {
    $json.PSObject.Properties.Remove('webSearch')
}

$json | ConvertTo-Json -Depth 10 | Set-Content $globalSettingsPath

Write-Host "Tavily MCP server added to global Qwen settings"
