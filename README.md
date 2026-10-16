# 📧 Receipt Sweep

An MCP server + Claude skill that connects to your email inbox, finds receipts and invoices, and builds a categorized spending spreadsheet — all powered by AI.

## How it works

```
┌─────────────┐     IMAP      ┌──────────────────┐     MCP      ┌───────────┐
│  Your Email  │◄────────────►│  Receipt Sweep    │◄────────────►│  Claude   │
│  (Gmail,     │   App        │  MCP Server       │   tools      │  (AI)     │
│   Yahoo,     │   Password   │                   │              │           │
│   Outlook)   │              │  • search_emails  │              │ Extracts  │
└─────────────┘              │  • read_email     │              │ amounts,  │
                              │  • save_attachment│              │ categories│
                              └──────────────────┘              │ & builds  │
                                                                 │ .xlsx     │
                                                                 └───────────┘
```

1. **You install** the MCP server and skill
2. **You provide** your email address + an App Password (never stored)
3. **Claude connects** via IMAP and searches every folder for receipts
4. **Claude reads** each email, extracts dates, amounts, and store names
5. **Claude builds** a formatted Excel spreadsheet with categories and totals

## Supported email providers

| Provider | IMAP Host | Auth |
|---|---|---|
| **Gmail** | imap.gmail.com | [App Password](https://myaccount.google.com/apppasswords) |
| **Yahoo Mail** | imap.mail.yahoo.com | [App Password](https://login.yahoo.com/account/security) |
| **Outlook / Hotmail** | outlook.office365.com | Password or [App Password](https://account.live.com/proofs/manage) |
| **iCloud Mail** | imap.mail.me.com | [App-Specific Password](https://appleid.apple.com) |
| **Custom** | Any IMAP server | Password |

## Installation

The quickest path is the Claude plugin. The install scripts below are the manual route
for Claude Desktop.

### Install as a Claude plugin (recommended)

Requires [`uv`](https://docs.astral.sh/uv/) on your `PATH` (the plugin launches the
server with `uvx`). In Claude Code:

```
/plugin marketplace add saranya-ms/receipt-sweep
/plugin install receipt-sweep@receipt-sweep
```

This installs the MCP server **and** the `receipt-sweep` skill together. Start a new
session, then say *"Sweep my email for receipts."*

### Install scripts (Claude Desktop)

#### macOS / Linux

```bash
git clone https://github.com/saranya-ms/receipt-sweep.git
cd receipt-sweep
./install.sh
```

#### Windows

```powershell
git clone https://github.com/saranya-ms/receipt-sweep.git
cd receipt-sweep
.\install.ps1
```

#### What the installer does

1. Checks for Python 3.10+
2. Creates a virtual environment in `.venv/`
3. Installs the MCP server package
4. Registers the server in your Claude Desktop config

### Manual installation

If you prefer to install manually:

```bash
# Create and activate a venv
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install the package
pip install -e .

# Add to your Claude Desktop config (claude_desktop_config.json):
# {
#   "mcpServers": {
#     "receipt-sweep": {
#       "command": "/path/to/receipt-sweep/.venv/bin/receipt-sweep-mcp",
#       "args": []
#     }
#   }
# }
```

## Usage

After installation, restart Claude and say:

> **"Sweep my email for receipts"**

Claude will walk you through:
1. Choosing your email provider
2. Entering your App Password (shown in the provider's security settings)
3. Selecting a date range
4. Running the sweep

### The spreadsheet it produces

**Sheet 1 — Receipts:** Every transaction with Date, Store, Category, Amount, Currency

**Sheet 2 — Summary:** Spending totals by category

**Sheet 3 — Notes:** What was searched, what was excluded, PDF-only receipts to review manually

**Plus — an offline HTML dashboard:** a self-contained `.html` file with KPI tiles, a
spending-by-category chart, a month-by-month chart, top merchants, and a sortable
transaction table. It renders entirely in the browser with no internet connection — all
charts are inline SVG and there are no external requests.

### Incremental sweeps

Each run can save its state so the next run picks up where it left off — no duplicate scanning.

## MCP Tools provided

| Tool | Description |
|---|---|
| `list_email_providers` | Show supported providers and App Password instructions |
| `connect_email` | Connect to an inbox via IMAP |
| `disconnect_email` | Close the connection |
| `connection_status` | Check if connected |
| `list_folders` | List all mailbox folders |
| `search_emails` | Search one folder by sender, subject, date range |
| `read_email` | Read the full content of an email |
| `save_attachment` | Download a PDF or other attachment |
| `search_all_folders` | Search across every folder at once |

## Security & privacy

- **App Passwords only** — the server never sees your real password
- **No storage** — credentials are held in memory for the session only; nothing is written to disk
- **Read-only** — the server opens mailboxes in read-only mode; it never modifies, moves, or deletes emails
- **Local** — the MCP server runs on your machine; email data never leaves your computer except to Claude for AI processing
- **Revocable** — you can revoke the App Password at any time from your email provider's security settings

## Privacy Policy

Receipt Sweep runs entirely on your own machine.

- **Data collection** — The server reads only the mailbox data you ask it to: email
  headers, bodies, and attachments returned by your IMAP searches. It collects no
  analytics, telemetry, or usage data.
- **Usage & storage** — Your email address and App Password are held in memory for the
  session only and are never written to disk. Email content is passed to Claude solely to
  extract receipt data at your request.
- **Third-party sharing** — Nothing is sent to the author or any other third party. Data
  leaves your machine only to (a) your email provider over TLS/IMAP and (b) Claude, for
  the AI processing you initiate.
- **Data retention** — No credentials or email data are retained after the session ends.
  Spreadsheets and dashboards are written only to the location you choose.
- **Contact** — Questions or issues: <https://github.com/saranya-ms/receipt-sweep/issues>

## Requirements

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) (for the plugin install path)
- Claude Desktop or Claude Code
- An email account with IMAP enabled

## Distribute as a plugin

This repo is also a Claude plugin and its own marketplace (`.claude-plugin/`). Users
install it with the two `/plugin` commands in [Installation](#install-as-a-claude-plugin-recommended).

### Submit it to Anthropic's directory

To list it in the public [directory](https://claude.ai/directory) (installable from
claude.ai and Cowork, and synced into Claude Code):

1. Validate locally: `claude plugin validate ./ --strict`.
2. From a paid Claude plan, open [claude.ai/directory/manage](https://claude.ai/directory/manage)
   → **Submit new** → **Plugin**. The portal reads the listing fields from
   `.claude-plugin/plugin.json` and the Privacy Policy section above.
3. Anthropic auto-scans the submission for policy compliance and lists it as a
   **Community** plugin; some submissions also get a human review. Track status in the
   portal.

## License

MIT
