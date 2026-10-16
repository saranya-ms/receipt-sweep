# ──────────────────────────────────────────────────────────────
# Receipt Sweep MCP Server — Installer for Windows
# ──────────────────────────────────────────────────────────────
#Requires -Version 5.1

$ErrorActionPreference = "Stop"
$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerName = "receipt-sweep"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Receipt Sweep MCP Server — Installer           ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── 1. Check Python ──────────────────────────────────────────
$Python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $version = & $cmd --version 2>&1
        if ($version -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 10) {
                $Python = $cmd
                break
            }
        }
    } catch { }
}

if (-not $Python) {
    Write-Host "❌ Python 3.10+ is required but not found." -ForegroundColor Red
    Write-Host "   Install it from https://python.org/downloads"
    exit 1
}
Write-Host "✓ Found $Python ($(& $Python --version))" -ForegroundColor Green

# ── 2. Create a virtual environment ─────────────────────────
$VenvDir = Join-Path $RepoDir ".venv"
if (-not (Test-Path $VenvDir)) {
    Write-Host "→ Creating virtual environment..."
    & $Python -m venv $VenvDir
}
Write-Host "✓ Virtual environment at $VenvDir" -ForegroundColor Green

$PipExe    = Join-Path $VenvDir "Scripts\pip.exe"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$ServerExe = Join-Path $VenvDir "Scripts\receipt-sweep-mcp.exe"

# ── 3. Install the package ──────────────────────────────────
Write-Host "→ Installing receipt-sweep-mcp..."
& $PipExe install --quiet --upgrade pip
& $PipExe install --quiet -e $RepoDir
Write-Host "✓ Package installed" -ForegroundColor Green

# ── 4. Register as an MCP server with Claude Desktop ────────
$ClaudeConfigDir = Join-Path $env:APPDATA "Claude"
$ClaudeConfig    = Join-Path $ClaudeConfigDir "claude_desktop_config.json"

Write-Host "→ Registering MCP server..."

if (-not (Test-Path $ClaudeConfigDir)) {
    New-Item -ItemType Directory -Path $ClaudeConfigDir -Force | Out-Null
}

# Use Python for safe JSON manipulation (handles edge cases better)
& $PythonExe -c @"
import json, sys, os

config_file = sys.argv[1]
server_name = sys.argv[2]
server_bin  = sys.argv[3]

if os.path.isfile(config_file) and os.path.getsize(config_file) > 0:
    with open(config_file, encoding='utf-8') as f:
        config = json.load(f)
else:
    config = {}

if server_name in config.get('mcpServers', {}):
    print('  Already registered')
    sys.exit(2)

config.setdefault('mcpServers', {})[server_name] = {
    'command': server_bin.replace('\\', '/'),
    'args': []
}

with open(config_file, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
"@ $ClaudeConfig $ServerName $ServerExe

if ($LASTEXITCODE -eq 2) {
    Write-Host "  ✓ Already registered in Claude Desktop config" -ForegroundColor Green
} elseif ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Registered in Claude Desktop config" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Could not register — add manually (see README)" -ForegroundColor Yellow
}

# ── 5. Skill info ──────────────────────────────────────────
$SkillSrc = Join-Path $RepoDir "skill\SKILL.md"
Write-Host ""
Write-Host "→ Skill file is at: $SkillSrc"
Write-Host "  To install it in Claude, either:"
Write-Host "    • Copy skill\SKILL.md into your Claude skills folder"
Write-Host "    • Or add it as a project skill in Claude.ai"

# ── Done ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   ✅ Installation complete!                       ║" -ForegroundColor Green
Write-Host "╠══════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║                                                  ║" -ForegroundColor Green
Write-Host "║   Restart Claude to load the MCP server.         ║" -ForegroundColor Green
Write-Host "║                                                  ║" -ForegroundColor Green
Write-Host "║   Then ask Claude:                               ║" -ForegroundColor Green
Write-Host '║     "Sweep my email for receipts"                ║' -ForegroundColor Green
Write-Host "║                                                  ║" -ForegroundColor Green
Write-Host "║   Claude will:                                   ║" -ForegroundColor Green
Write-Host "║     1. Ask for your email provider + app password ║" -ForegroundColor Green
Write-Host "║     2. Search all folders for receipts            ║" -ForegroundColor Green
Write-Host "║     3. Extract amounts and build a spreadsheet    ║" -ForegroundColor Green
Write-Host "║                                                  ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor Green
