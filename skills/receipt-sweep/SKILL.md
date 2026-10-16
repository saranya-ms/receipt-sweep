---
name: receipt-sweep
description: >
  Extract receipts from any email inbox and build a categorized spending
  spreadsheet. Uses the receipt-sweep MCP server for IMAP email access.
  Run this skill whenever the user wants to sweep their email for receipts,
  invoices, or order confirmations.
---

# Receipt Sweep — Email → Spending Spreadsheet

Searches the user's email inbox via IMAP for receipts, invoices, and order
confirmations, extracts transaction data, and builds a categorized xlsx
spreadsheet plus a self-contained offline HTML dashboard.

## Prerequisites

The **receipt-sweep MCP server** must be installed and running. Its tools
(`list_email_providers`, `connect_email`, `search_emails`, `read_email`,
`save_attachment`, `search_all_folders`) must be available.

If the tools are not available, tell the user:
> "The receipt-sweep MCP server isn't connected. Run `install.sh` (macOS/Linux)
> or `install.ps1` (Windows) from the receipt-sweep repo, then restart Claude."

## Step 1 — Connect to the inbox

1. Call `list_email_providers` to show the user the supported providers.
2. Ask the user for:
   - Their email provider (Gmail, Yahoo, Outlook, iCloud, or custom IMAP host)
   - Their email address
   - An **App Password** (not their regular password) — show them the provider-specific instructions
3. Call `connect_email(provider, email, app_password)` to authenticate.
4. Call `list_folders` to see all available mailbox folders.
5. Confirm the connection before proceeding.

**IMPORTANT:** Never store or log the App Password. It is used only for this
IMAP session and is not persisted anywhere.

## Step 2 — Determine the sweep range

Ask the user:
- What date range to search (e.g., "all of 2026", "last 3 months", "since my last sweep")
- Where to save the spreadsheet (a folder path, or default to the working directory)

If the user has a sweep state file in project memory, read it to get the last
sweep date and pick up from there.

## Step 3 — Search for receipts

### 3a. Store-specific searches (high precision)

For each of these common receipt senders, search by sender address:

| Store | Search `from_address` | Search `subject_contains` |
|---|---|---|
| Old Navy / Gap | oldnavy@gapcanada.ca OR oldnavy@gap.com | order |
| Sephora | customerservice@email.sephora.com | order |
| H&M | customerservice@email.hm.com | order |
| Uber Eats | uber.canada@uber.com OR receipts@uber.com | receipt |
| Amazon | auto-confirm@amazon.com OR auto-confirm@amazon.ca | order |
| Tim Hortons | timhortons@e.timhortons.ca | receipt |
| Walmart | help@walmart.ca OR account@walmart.com | order |
| Target | orders@target.com | order |
| IKEA | no.reply@ikea.com | receipt |
| Apple | no_reply@email.apple.com | receipt |
| Massage Addict | noreply@massageaddict.ca | receipt |
| Stylevana | info@stylevana.com | order |
| American Eagle | ae@aeo.com | order OR pickup |
| Winners/HomeSense/Marshalls | noreply@tjxcanada.ca | receipt |
| Ardene | noreply@ardene.com | order |
| DoorDash | no-reply@doordash.com | receipt |
| SkipTheDishes | noreply@skipthedishes.com | receipt |

Run each search with the `since_date` set to the start of the sweep range.
Use `search_emails` on INBOX first; if results are sparse, use
`search_all_folders` to catch receipts filed in custom folders, spam, or archive.

### 3b. Broad catch-all searches

After the targeted searches, run broader searches to catch unknown stores:

```
body_or_subject: "receipt"        since_date: <start>
body_or_subject: "order confirmed" since_date: <start>
body_or_subject: "invoice"        since_date: <start>
body_or_subject: "your order"     since_date: <start>
body_or_subject: "payment received" since_date: <start>
```

Use `search_all_folders` for these to cover spam, archive, and custom folders.

### 3c. De-duplicate

Track message IDs already processed. Skip duplicates across searches.

## Step 4 — Read and extract data

For each potential receipt email found:

1. Call `read_email(message_id, folder)` to get the full body text.
2. Parse the email body to extract:
   - **Date** — from the email date header
   - **Establishment Name** — from the sender or body content
   - **Category** — use the categorization table below
   - **Amount** — the total or order total from the email body
   - **Currency** — infer from store location / currency symbols
3. If the email body says "receipt attached" or similar with no amount in the
   body, note it as a **PDF-only receipt** — optionally use `save_attachment`
   to download the PDF for manual review.

### Categorization rules

| Pattern | Category |
|---|---|
| Clothing stores (Old Navy, H&M, Gap, AE, Ardene, Zara, etc.) | Apparel |
| Sephora, Ulta, beauty brands | Beauty |
| Stylevana, skincare brands | Beauty/Skincare |
| Uber Eats, DoorDash, SkipTheDishes | Food Delivery |
| Tim Hortons, Starbucks, restaurants | Food & Beverage |
| Chiropractor, physiotherapy | Medical/Chiropractic |
| Massage therapy | Medical/Massage |
| Pharmacy, medical | Medical |
| Walmart, Target, Costco (general) | Household |
| IKEA, home stores | Home Furnishing |
| Amazon (categorize by item if clear) | Various |
| Grocery stores | Groceries |
| Gas stations | Transportation |
| Unknown | Ask the user or use best judgment |

### Exclusion rules

Skip these — they are not purchase receipts:
- **Promotional / marketing emails** with no actual order
- **Card reload / top-up** emails (e.g., Tim Hortons "Balance Load")
- **$0.00 transactions** or free events
- **Canceled orders**
- **Shipping notifications** that duplicate an order confirmation
- **Pharmacy pickup notifications** with no dollar amount
- **Obvious spam** invoices from unknown senders

## Step 5 — Build the spreadsheet

Load the **xlsx skill** before building.

Create the workbook with three sheets:

### Sheet 1: "[Year] Receipts"
| Column | Format |
|---|---|
| Date | YYYY-MM-DD |
| Establishment Name | Text |
| Category | Text |
| Amount | $#,##0.00 |
| Currency | Text (CAD, USD, etc.) |

- Sort by date ascending
- Auto-filter on all columns
- Freeze the header row
- SUM formula in the total row
- Professional formatting (Arial, blue headers, borders)

### Sheet 2: "Summary by Category"
| Column | Format |
|---|---|
| Category | Text |
| Number of Transactions | Number |
| Total Amount | $#,##0.00 |

- Sort by total descending
- SUM formulas for totals

### Sheet 3: "Notes"
- Data source (email address, folders searched)
- Date range of the sweep
- Currency note
- List of PDF-only receipts (filename, date, sender)
- List of exclusions applied
- Timestamp of when the sweep was run

Run `recalc.py` to verify all formulas.

## Step 6 — Build the HTML dashboard

In addition to the spreadsheet (which still ships), generate a self-contained HTML
dashboard from the **same extracted rows** — do not re-read any emails.

1. Load the **dataviz skill** for color and chart conventions.
2. Start from the bundled template `assets/dashboard-template.html` in this skill's
   folder (when running as a plugin, it is at
   `${CLAUDE_PLUGIN_ROOT}/skills/receipt-sweep/assets/dashboard-template.html`). Copy it,
   then replace **only** the `DATA` object near the bottom with the real sweep results:
   - `title`, `subtitle` — e.g. "2026 Spending Dashboard" and "<email> · <date range>"
   - `currency` — ISO code (CAD, USD, …) used for all formatting
   - `kpis.dateRange` — human-readable range
   - `categories` — `[{name, amount}]`, one per category (total spend)
   - `monthly` — `[{month: "YYYY-MM", amount}]`, chronological
   - `merchants` — `[{name, amount}]`, top merchants by spend, sorted descending
   - `transactions` — `[{date: "YYYY-MM-DD", merchant, category, amount}]`, every row
   - `footer` — `{source, folders, generated}`
3. Keep the file **fully offline**: never add a `<script src>`, CDN link, web font, or
   any external request. The KPI tiles, SVG charts, and sortable table all render in the
   browser from `DATA` alone. Light and dark are handled by the template.
4. Save it next to the spreadsheet, e.g. `<Year>-spending-dashboard.html`.

## Step 7 — Deliver results

1. Send **both** files to the user with `SendUserFile`: the spreadsheet, and the
   dashboard with `display: "render"` so it opens inline.
2. If a device folder is connected, also write them there via `device_commit_files`.
3. Report:
   - Total transactions found
   - Total spending amount
   - Breakdown by category
   - Any PDF-only receipts the user may want to review manually
   - Any new stores discovered

## Step 8 — Save sweep state (optional)

If the user wants incremental sweeps, save the state to project memory:
- Last sweep date
- Known stores and sender addresses discovered
- Output file location

This way, the next run can pick up from where this one left off.

## Tips

- IMAP search is fast but basic — it doesn't support regex. Use simple terms.
- Some providers (Gmail) support searching `[Gmail]/All Mail` to search everything at once.
- Yahoo uses `Bulk` for spam and has custom folder names.
- Outlook uses folder paths like `Junk Email` for spam.
- Always disconnect when done: `disconnect_email()`.
- For very large mailboxes, search by sender first (faster) before broad searches.
