#!/usr/bin/env pwsh
# New Project Scaffold Script
# Creates a new project directory with .qwenignore and optional git init

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Name,
    
    [Parameter(Position=1)]
    [string]$Path = ".",
    
    [switch]$NoGit,
    
    [switch]$Verbose
)

# Get script directory (where this script lives)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# Resolve full project path
$ProjectPath = Join-Path $Path $Name
if ($Path -eq ".") {
    $ProjectPath = (Resolve-Path $Path).Path + "\" + $Name
}
$ProjectPath = Resolve-Path -Path $ProjectPath -ErrorAction SilentlyContinue
if (-not $ProjectPath) {
    $ProjectPath = Join-Path (Get-Location) $Name
}

Write-Host "Creating project: $ProjectPath" -ForegroundColor Cyan

# Create directory
New-Item -ItemType Directory -Force -Path $ProjectPath | Out-Null

# Copy .qwenignore
$QwenIgnoreSource = Join-Path $ProjectRoot ".qwenignore"
$QwenIgnoreDest = Join-Path $ProjectPath ".qwenignore"
if (Test-Path $QwenIgnoreSource) {
    Copy-Item $QwenIgnoreSource $QwenIgnoreDest
    if ($Verbose) { Write-Host "  ✓ Copied .qwenignore" -ForegroundColor Green }
} else {
    Write-Host "  ⚠ .qwenignore not found at $QwenIgnoreSource" -ForegroundColor Yellow
}

# Initialize git (optional)
if (-not $NoGit) {
    Push-Location $ProjectPath
    git init --quiet
    if ($LASTEXITCODE -eq 0) {
        if ($Verbose) { Write-Host "  ✓ Initialized git repository" -ForegroundColor Green }
    }
    Pop-Location
}

Write-Host "✓ Project '$Name' created successfully!" -ForegroundColor Green
if (-not $NoGit) {
    Write-Host "  cd $Name" -ForegroundColor Gray
}
