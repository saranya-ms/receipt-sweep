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
(`list_email_providers`, `connect_email`, `list_folders`, `search_emails`,
`search_all_folders`, `read_email`, `read_pdf_attachment`, `save_attachment`)
must be available.

If the tools are not available, tell the user:
> "The receipt-sweep server isn't connected yet. It's launched with `uv`, so:
> 1. Install uv — see https://docs.astral.sh/uv/getting-started/installation/
> 2. Fully quit Claude and reopen it (so it picks up uv on your PATH).
> 3. Start a new session and ask me again.
>
> If you installed with `install.sh` / `install.ps1` instead, just restart Claude."

## Step 1 — Set up the sweep (one short exchange)

Collect everything up front, in at most two turns, instead of asking one
question at a time. First call `list_email_providers` (you'll need its App
Password instructions below).

**Returning user:** if project memory has a sweep state (last sweep date,
email address, provider, output folder), offer to reuse it: *"Pick up where we
left off — <email>, from <last sweep date> to today, saving to <folder>?"*
You still need the App Password; it is never stored.

### 1a. The choices

If a structured question tool is available (for example `AskUserQuestion` in
Claude Code), ask these in **one** call. Otherwise ask them as one short
numbered list.

| Question | Options (recommended first) |
|---|---|
| Which email account should I sweep? | Gmail · Yahoo Mail · Outlook / Hotmail · iCloud *(other = a custom IMAP host)* |
| How far back should I look? | Last 3 months · Last 30 days · This year so far · Since my last sweep *(only if a sweep state exists; other = custom dates)* |
| Which amount should I count? | What I paid out of pocket · Full receipt totals |
| Where should I save the spreadsheet and dashboard? | This folder (the working directory) *(other = a folder path)* |

Explain the amount choice in one line: *out of pocket* leaves out whatever
insurance, a benefits plan or an employer paid directly, so the totals show
what actually left your account.

### 1b. Email address and App Password

Then send one message asking for the email address and an App Password,
using the provider-specific steps from `list_email_providers`:

> **Almost ready.** Please send:
> 1. Your **<Provider> email address**
> 2. An **App Password**. It's a separate password just for this tool, not your
>    normal login. To create one: <provider steps and link>.
>
> The App Password is used only for this session. It isn't saved anywhere and
> you can revoke it any time in your <Provider> security settings. It will be
> visible in this conversation, so revoke it afterwards if you'd like.

### 1c. Connect

1. Tidy the input before connecting: trim whitespace and **remove spaces from
   the App Password** (Gmail and Yahoo show it in groups of four, e.g.
   `abcd efgh ijkl mnop`).
2. If the address doesn't match the chosen provider (for example a
   `@hotmail.com` address with Yahoo chosen), ask which one they meant before
   connecting.
3. Call `connect_email(provider, email, app_password)`. **Never repeat the App
   Password back** in your messages.
4. If login fails, say what usually causes it: the regular password was used
   instead of an App Password, the App Password was typed with a mistake, or
   (for Gmail) 2-Step Verification is not turned on. Ask for a new App Password
   and try again. Don't ask for their regular password.
5. Call `list_folders`, then confirm in one line before searching:
   *"Connected to <email>. Sweeping <range> across <N> folders. Counting
   <out-of-pocket | full> amounts and saving to <folder>."*

Resolve relative ranges against today's date (e.g. "last 3 months" on
2026-10-16 → `since_date` 2026-07-16).

**IMPORTANT:** Never store, log, or write the App Password to any file or to
memory. It is used only for this IMAP session.

## Step 2 — Search for receipts

The server handles one mailbox command at a time. Concurrent tool calls are
safe, but they queue and run one after another, so issue searches one by one;
that also makes progress easier to follow. If a dropped connection can't be
restored, tools return an error that says to call `connect_email` again. Do
that with the details the user already gave you, then continue.

Look at the folder list first. Many people file receipts into **custom
folders named after stores** (e.g. `old navy`, `Uber`, `timmy`). Search
those as well, and treat folders like `Promotions`, `Bulk` (Yahoo spam) and
`Shopping` as likely marketing.

### 2a. Store-specific searches (high precision)

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

### 2b. Broad catch-all searches

After the targeted searches, run broader searches to catch unknown stores.
Search the **subject** first. Body searches also match newsletters and
promotions that just mention these words:

```
subject_contains: "order"         since_date: <start>
subject_contains: "receipt"       since_date: <start>
subject_contains: "confirmation"  since_date: <start>
subject_contains: "invoice"       since_date: <start>
body_or_subject: "payment received" since_date: <start>
```

Use `search_all_folders` for these to cover spam, archive, and custom folders.
If its result includes `folders_not_searched`, retry those folders with
`search_emails`, or list them in the Notes sheet. Don't treat them as empty.

Also list each **store-named custom folder** with only `since_date` set, to
catch receipts whose subjects don't use these words. Ignore promotional
subjects such as "Extra 20% off your order".

### 2c. De-duplicate

Track message IDs already processed. Skip duplicates across searches.

## Step 3 — Read and extract data

For each potential receipt email found:

1. Call `read_email(message_id, folder)`. The body comes from whichever
   plain-text or HTML part holds the order details, so totals that only appear
   in the HTML version (common for Old Navy, Gap and other retailers) are
   included.
2. If the body has no amount and `has_pdf` is true (e.g. "your receipt is
   attached"), call `read_pdf_attachment(message_id, filename, folder)` and
   take the total from the PDF text. Note it as a PDF receipt.
3. Extract:
   - **Date**: the transaction date from the body, otherwise the email date
   - **Establishment Name**: from the sender or body content
   - **Category**: use the categorization table below
   - **Amount**: see *Which amount to record* below
   - **Currency**: infer from the store location or currency symbols
   - **Notes**: anything the reader needs, e.g. "Gross $139.53; $109.43 paid by Manulife"
4. If you still can't find an amount, **don't guess.** Add the order (date,
   merchant, order number, folder) to a **Needs review** list for the Notes
   sheet and tell the user.

### Which amount to record

Use the choice from Step 1. The default is **out of pocket**.

- **Insurance, benefits plan, or employer direct billing**: when the payment
  section is split (e.g. "Manulife $109.43 · Visa $30.10"), out of pocket is
  the user's own payment only ($30.10). Put the gross total and who covered
  the rest in Notes. With *full totals*, record the grand total and note the
  coverage.
- **Discounts, coupons, points or rewards redeemed**: use the net amount
  charged, which is the receipt's Total line.
- **Tips, taxes, delivery and service fees**: include them; they were paid.
- **Paid from a gift card or stored balance** (e.g. a Tim Hortons card): count
  the purchase. Card top-ups ("Balance Load") are excluded below, so the money
  is counted once.
- **Refunds and returns**: record a negative amount in the original category
  so that totals stay net.

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

## Step 4 — Build the spreadsheet

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
| Notes | Text: coverage, PDF receipt, etc. |

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
- Amount basis: out of pocket or full receipt totals, with any insurance or benefit splits
- **Needs review**: orders found without a readable amount (date, merchant, order #, folder)
- List of PDF receipts (filename, date, sender)
- List of exclusions applied
- Any folders that could not be searched
- Timestamp of when the sweep was run

Run `recalc.py` to verify all formulas.

## Step 5 — Build the HTML dashboard

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

## Step 6 — Deliver results

1. Send **both** files to the user with `SendUserFile`: the spreadsheet, and the
   dashboard with `display: "render"` so it opens inline.
2. If a device folder is connected, also write them there via `device_commit_files`.
3. Report:
   - Total transactions found
   - Total spending amount
   - Breakdown by category
   - Whether amounts are out of pocket or full totals, and any insurance splits
   - Anything in **Needs review**, with a request for the missing amounts
   - Any new stores discovered

## Step 7 — Save sweep state (optional)

If the user wants incremental sweeps, save the state to project memory:
- Last sweep date, email address, provider, and amount basis (never the App Password)
- Known stores and sender addresses discovered, and which custom folders hold receipts
- Output file location

This way, the next run can pick up from where this one left off.

## Tips

- IMAP search is fast but basic — it doesn't support regex. Use simple terms.
- Some providers (Gmail) support searching `[Gmail]/All Mail` to search everything at once.
- Yahoo uses `Bulk` for spam and has custom folder names.
- Outlook uses folder paths like `Junk Email` for spam.
- Gmail and Yahoo show App Passwords in groups of four. Remove the spaces before connecting.
- Always disconnect when done: `disconnect_email()`.
- For very large mailboxes, search by sender first (faster) before broad searches.
