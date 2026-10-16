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
5. **Check the server version.** A successful `connect_email` reply ends with
   a tag like `(receipt-sweep server v1.2.1)`; `connection_status` shows it
   too. If the tag is **missing**, the user's copy of the plugin is outdated:
   the same person can have one copy in the Claude desktop app or claude.ai
   and another in the Claude Code CLI, and they update separately. Old servers
   can't read totals that appear only in an email's HTML (Old Navy, Gap and
   others) and break when tool calls run in parallel. Then:
   - Tell the user in one line, and how to fix it: update or reinstall the
     Receipt Sweep plugin from where they installed it (in Claude Code, the
     `/plugin` menu; in the desktop app or claude.ai, the plugin settings),
     then start a new session.
   - If they want to go ahead anyway, make **every** mailbox tool call one at
     a time, never in parallel, and put any order whose body has only links
     and no amount on the **Needs review** list.
6. Call `list_folders`, then confirm in one line before searching:
   *"Connected to <email>. Sweeping <range> across <N> folders. Counting
   <out-of-pocket | full> amounts and saving to <folder>."*

Resolve relative ranges against today's date (e.g. "last 3 months" on
2026-10-16 → `since_date` 2026-07-16).

**IMPORTANT:** Never store, log, or write the App Password to any file or to
memory. It is used only for this IMAP session.

## Step 2 — Search for receipts

The server handles one mailbox command at a time. On a current server (see
Step 1c) concurrent tool calls are safe, but they queue and run one after
another, so issue searches one by one; that also makes progress easier to
follow. If calls start failing with socket or `EOF` errors, call
`connection_status`: it checks the session with the mail server and reopens
it if it dropped. If it says the connection was lost, call `connect_email`
again with the details the user already gave you, then continue.

Look at the folder list first. Many people file receipts into **custom
folders named after stores** (e.g. `old navy`, `Uber`, `timmy`). Search
those as well, and treat folders like `Promotions`, `Bulk` (Yahoo spam) and
`Shopping` as likely marketing.

### 2a. Store-specific searches (high precision)

For each of these common receipt senders, search by sender. IMAP's `FROM`
match is a substring match, so pass the **domain fragment** below rather than
a full address: stores send from several addresses that change by country and
over time (Old Navy Canada's confirmations come from
`orders@email.oldnavy.ca`, for example). One search per row; `subject_contains`
narrows it to receipts.

| Store | `from_address` | `subject_contains` |
|---|---|---|
| Old Navy | oldnavy | order |
| Gap | gapcanada.ca, then gap.com | order |
| Sephora | sephora.com | order |
| H&M | email.hm.com | order |
| Uber Eats | uber.com | receipt |
| Amazon | amazon.com, then amazon.ca | order |
| Tim Hortons | timhortons | receipt |
| Walmart | walmart.ca, then walmart.com | order |
| Target | target.com | order |
| IKEA | ikea.com | receipt |
| Apple | apple.com | receipt |
| Massage Addict | massageaddict | receipt |
| Spa / clinic bookings (Booker) | secure-booker.com | *(none)* |
| Stylevana | stylevana | order |
| American Eagle | aeo.com | order |
| Winners/HomeSense/Marshalls | tjxcanada | receipt |
| Ardene | ardene.com | order |
| la Vie en Rose | lavieenrose | *(none)* |
| DoorDash | doordash | receipt |
| SkipTheDishes | skipthedishes | receipt |

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
   included. If a body is only links and the version check in Step 1c failed,
   that's the outdated server, not a missing total: add the order to
   **Needs review**.
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

### Saving when the file is open or synced

If writing or even reading the workbook fails with a permission error or
"Device or resource busy", it is almost always open in Excel; files in a
OneDrive or Dropbox folder can also be briefly held while they sync.

- Work on a copy: copy the workbook to a temp folder, edit the copy, then copy
  it back over the original. Copying often works when opening the file in
  place doesn't.
- If copying back fails, ask the user to close the file in Excel, then retry.
  If it still fails, wait a few seconds for the sync to finish and try once
  more.
- If you still can't replace it, save the result next to it as
  `<name>-UPDATED.xlsx`, tell the user, and offer to swap it in once the
  original is closed. Delete the `-UPDATED` copy after a successful swap.

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

## Updating an earlier sweep

When the user asks to change a sweep that is already saved (fill in the
**Needs review** amounts, switch a row between out-of-pocket and full total,
fix a category), edit the existing files rather than sweeping again:

1. Read the existing workbook (see *Saving when the file is open or synced*)
   and the sweep state in memory.
2. For missing amounts, connect (Step 1c, including the version check),
   re-read just those emails with `read_email` in the folder recorded in the
   Notes sheet, and take each order's Total line.
3. Insert new rows in date order and update every formula that covers the data
   rows: the TOTAL `SUM`, and the `COUNTIFS`/`SUMIFS` ranges on the Summary
   sheet. Inserting rows past the end of a fixed range like `D4:D8` silently
   leaves them out of the totals.
4. Update the Notes sheet: move filled-in orders out of **Needs review** and
   record the amount basis for any row you switched.
5. Rebuild the dashboard's `DATA` object from the updated rows (categories,
   monthly, merchants and transactions all change), then update the sweep
   state in memory.

## Tips

- IMAP search is fast but basic — it doesn't support regex. Use simple terms.
- Some providers (Gmail) support searching `[Gmail]/All Mail` to search everything at once.
- Yahoo uses `Bulk` for spam and has custom folder names.
- Outlook uses folder paths like `Junk Email` for spam.
- Gmail and Yahoo show App Passwords in groups of four. Remove the spaces before connecting.
- Always disconnect when done: `disconnect_email()`.
- For very large mailboxes, search by sender first (faster) before broad searches.
