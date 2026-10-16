#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Receipt Sweep MCP Server — Installer for macOS / Linux
# ──────────────────────────────────────────────────────────────
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER_NAME="receipt-sweep"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   Receipt Sweep MCP Server — Installer           ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── 1. Check Python ──────────────────────────────────────────
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "❌ Python 3.10+ is required but not found."
    echo "   Install it from https://python.org/downloads"
    exit 1
fi
echo "✓ Found $PYTHON ($($PYTHON --version))"

# ── 2. Create a virtual environment ─────────────────────────
VENV_DIR="$REPO_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "→ Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
fi
echo "✓ Virtual environment at $VENV_DIR"

# ── 3. Install the package ──────────────────────────────────
echo "→ Installing receipt-sweep-mcp..."
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -e "$REPO_DIR"
echo "✓ Package installed"

SERVER_BIN="$VENV_DIR/bin/receipt-sweep-mcp"

# ── 4. Register as an MCP server with Claude Desktop ────────
# Locate the Claude Desktop config file
CLAUDE_DESKTOP_CONFIG=""
if [ "$(uname)" = "Darwin" ]; then
    CLAUDE_DESKTOP_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
else
    # Linux — XDG default
    CLAUDE_DESKTOP_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/Claude/claude_desktop_config.json"
fi

register_mcp_server() {
    local config_file="$1"
    local config_dir
    config_dir="$(dirname "$config_file")"

    mkdir -p "$config_dir"

    if [ -f "$config_file" ]; then
        # Check if already registered
        if "$VENV_DIR/bin/python" -c "
import json, sys
with open(sys.argv[1]) as f:
    cfg = json.load(f)
sys.exit(0 if sys.argv[2] in cfg.get('mcpServers', {}) else 1)
" "$config_file" "$SERVER_NAME" 2>/dev/null; then
            echo "  ✓ Already registered in $(basename "$config_dir") config"
            return
        fi
    fi

    # Use Python for safe JSON manipulation (handles paths with special chars)
    "$VENV_DIR/bin/python" -c "
import json, sys, os

config_file = sys.argv[1]
server_name = sys.argv[2]
server_bin  = sys.argv[3]

if os.path.isfile(config_file) and os.path.getsize(config_file) > 0:
    with open(config_file) as f:
        config = json.load(f)
else:
    config = {}

config.setdefault('mcpServers', {})[server_name] = {
    'command': server_bin,
    'args': []
}

with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
" "$config_file" "$SERVER_NAME" "$SERVER_BIN"

    echo "  ✓ Registered in $(basename "$config_dir") config"
}

echo "→ Registering MCP server..."
register_mcp_server "$CLAUDE_DESKTOP_CONFIG"

# ── 5. Skill info ──────────────────────────────────────────
SKILL_SRC="$REPO_DIR/skill/SKILL.md"
echo ""
echo "→ Skill file is at: $SKILL_SRC"
echo "  To install it in Claude, either:"
echo "    • Copy skill/SKILL.md into your Claude skills folder"
echo "    • Or add it as a project skill in Claude.ai"

# ── Done ─────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   ✅ Installation complete!                       ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║                                                  ║"
echo "║   Restart Claude to load the MCP server.         ║"
echo "║                                                  ║"
echo "║   Then ask Claude:                               ║"
echo "║     \"Sweep my email for receipts\"                ║"
echo "║                                                  ║"
echo "║   Claude will:                                   ║"
echo "║     1. Ask for your email provider + app password ║"
echo "║     2. Search all folders for receipts            ║"
echo "║     3. Extract amounts and build a spreadsheet    ║"
echo "║                                                  ║"
echo "╚══════════════════════════════════════════════════╝"
