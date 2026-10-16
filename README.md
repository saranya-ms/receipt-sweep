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
2. **You pick** your provider, date range and options, then give your email address and an App Password (never stored)
3. **Claude connects** via IMAP and searches every folder for receipts
4. **Claude reads** each email, including HTML-only and PDF receipts, and extracts dates, amounts and store names
5. **Claude builds** a formatted Excel spreadsheet and an offline dashboard with categories and totals

## Supported email providers

| Provider | IMAP Host | Auth |
|---|---|---|
| **Gmail** | imap.gmail.com | [App Password](https://myaccount.google.com/apppasswords) |
| **Yahoo Mail** | imap.mail.yahoo.com | [App Password](https://login.yahoo.com/account/security) |
| **Outlook / Hotmail** | outlook.office365.com | Password or [App Password](https://account.live.com/proofs/manage) |
| **iCloud Mail** | imap.mail.me.com | [App-Specific Password](https://appleid.apple.com) |
| **Custom** | Any IMAP server | Password |

## Before you start

Do these once, before installing:

1. **Install `uv`.** The plugin starts its server with `uv`, a small Python tool
   runner. It also downloads a suitable Python for you if needed.

   macOS / Linux:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   Windows (PowerShell):
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   Open a new terminal and check it with `uv --version`.

2. **Fully quit and reopen Claude** (Desktop or Claude Code) after installing `uv`.
   Apps read your `PATH` when they start, so a Claude that was already running
   can't find `uv`, and the server fails with a *"Connection closed"* error.

3. **Create an App Password** for the email account you want to sweep, using the
   links in [Supported email providers](#supported-email-providers). It's a
   separate password just for this tool, not your normal login. Gmail needs
   2-Step Verification turned on first.

## Installation

The quickest path is the Claude plugin. The install scripts further down are the
manual route for Claude Desktop.

### Install as a Claude plugin (recommended)

**In the Claude desktop app:** open **Settings → Plugins**, click **+ Add**, add the
marketplace `saranya-ms/receipt-sweep`, then install **Receipt Sweep** from
*From marketplaces you added*.

**In Claude Code (terminal):**

```
/plugin marketplace add saranya-ms/receipt-sweep
/plugin install receipt-sweep@receipt-sweep
```

Either way this installs the MCP server **and** the `receipt-sweep` skill together.
Plugins load when a session starts, so **start a new session**, then say
*"Sweep my email for receipts."*

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

The script route needs Python 3.10+ and `git`, but not `uv`.

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

After installation, start a new session and say:

> **"Sweep my email for receipts"**

Claude sets things up in two quick steps:
1. **A few choices in one go**: your email provider, how far back to look (last 30
   days, last 3 months, this year, or since your last sweep), whether to count
   **out-of-pocket** spending or full receipt totals, and where to save the files.
2. **Your email address and App Password.** Claude shows the steps to create an
   App Password for your provider. Spaces in it are fine; Claude removes them.

Then it connects, sweeps every folder, and confirms what it's doing before it starts.

### The spreadsheet it produces

**Sheet 1 — Receipts:** Every transaction with Date, Store, Category, Amount, Currency, and Notes

**Sheet 2 — Summary:** Spending totals by category

**Sheet 3 — Notes:** What was searched, what was excluded, and a **Needs review** list
of any orders whose amount couldn't be read automatically

**Plus — an offline HTML dashboard:** a self-contained `.html` file with KPI tiles, a
spending-by-category chart, a month-by-month chart, top merchants, and a sortable
transaction table. It renders entirely in the browser with no internet connection — all
charts are inline SVG and there are no external requests.

### Out-of-pocket amounts

By default, amounts are **what you actually paid**. When a receipt is split, for example a
massage billed partly to an insurance or benefits plan, only your own payment is counted,
and the full total and who covered the rest go in the Notes column. Choose *full receipt
totals* at the start if you'd rather track the gross amount.

### Receipts it can read

- **Plain-text and HTML emails.** Some stores (Old Navy, Gap and others) put the order
  total only in the HTML version of the email; Claude reads whichever version has it.
- **PDF receipts.** When the email just says *"your receipt is attached"*, Claude reads
  the total straight from the PDF.

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
| `read_pdf_attachment` | Read the text of a PDF receipt attached to an email |
| `save_attachment` | Download a PDF or other attachment |
| `search_all_folders` | Search across every folder at once |

## Security & privacy

- **App Passwords only** — the server never sees your real password
- **No storage** — credentials are held in memory for the session only (so a dropped connection can reconnect automatically); nothing is written to disk. The App Password you type is visible in your Claude conversation, so revoke it after a sweep if you prefer
- **Read-only** — the server opens mailboxes in read-only mode; it never modifies, moves, or deletes emails
- **Local** — the MCP server runs on your machine; email data never leaves your computer except to Claude for AI processing
- **Revocable** — you can revoke the App Password at any time from your email provider's security settings

## Privacy Policy

Receipt Sweep runs entirely on your own machine.

- **Data collection** — The server reads only the mailbox data you ask it to: email
  headers, bodies, and attachments returned by your IMAP searches. It collects no
  analytics, telemetry, or usage data.
- **Usage & storage** — Your email address and App Password are held in memory for the
  session only (to reconnect automatically if the connection drops) and are never
  written to disk. Email content is passed to Claude solely to
  extract receipt data at your request.
- **Third-party sharing** — Nothing is sent to the author or any other third party. Data
  leaves your machine only to (a) your email provider over TLS/IMAP and (b) Claude, for
  the AI processing you initiate.
- **Data retention** — No credentials or email data are retained after the session ends.
  Spreadsheets and dashboards are written only to the location you choose.
- **Contact** — Questions or issues: <https://github.com/saranya-ms/receipt-sweep/issues>

## Requirements

- [`uv`](https://docs.astral.sh/uv/) for the plugin install path (it provides Python
  automatically), or Python 3.10+ for the install scripts
- Claude Desktop or Claude Code
- An email account with IMAP access and an App Password

## Troubleshooting

| Symptom | Fix |
|---|---|
| Server shows **"Connection closed"** / the tools aren't available | `uv` isn't installed or Claude can't see it. Install `uv`, **fully quit and reopen Claude**, then start a new session. |
| Plugin installed but Claude doesn't use it | Plugins load at session start. Start a new session. |
| **"Login failed"** | Use an App Password, not your regular password. Check for typos, or create a new one. Gmail needs 2-Step Verification on first. |
| Plugin manager shows an old name, icon, or *"no plugin in this marketplace"* right after an update | The app cached the marketplace. Remove and re-add the marketplace, or wait a few minutes (GitHub caches the files briefly) and restart Claude. |
| An order shows up under **Needs review** | Its amount wasn't readable in the email or its PDF. Open the email, then add the amount yourself or tell Claude. |

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
