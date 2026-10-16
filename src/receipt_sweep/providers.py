"""Email provider IMAP configurations."""

PROVIDERS: dict[str, dict] = {
    "gmail": {
        "name": "Gmail",
        "host": "imap.gmail.com",
        "port": 993,
        "help": (
            "Use an App Password (not your regular password). "
            "Go to https://myaccount.google.com/apppasswords to create one. "
            "You need 2-Step Verification enabled first."
        ),
    },
    "yahoo": {
        "name": "Yahoo Mail",
        "host": "imap.mail.yahoo.com",
        "port": 993,
        "help": (
            "Use an App Password. Go to https://login.yahoo.com/account/security "
            "→ Generate app password → select 'Other App' and create one."
        ),
    },
    "outlook": {
        "name": "Outlook / Hotmail",
        "host": "outlook.office365.com",
        "port": 993,
        "help": (
            "Use your regular password if you don't have 2FA, "
            "or create an App Password at https://account.live.com/proofs/manage"
        ),
    },
    "icloud": {
        "name": "iCloud Mail",
        "host": "imap.mail.me.com",
        "port": 993,
        "help": (
            "Use an app-specific password. Go to https://appleid.apple.com → "
            "Sign-In and Security → App-Specific Passwords."
        ),
    },
}


def get_provider(name: str) -> dict | None:
    """Look up a provider by name (case-insensitive, with common aliases)."""
    key = name.lower().strip()
    aliases = {
        "google": "gmail",
        "googlemail": "gmail",
        "yahoo": "yahoo",
        "yahoomail": "yahoo",
        "outlook": "outlook",
        "hotmail": "outlook",
        "live": "outlook",
        "msn": "outlook",
        "office365": "outlook",
        "icloud": "icloud",
        "apple": "icloud",
        "me.com": "icloud",
    }
    resolved = aliases.get(key, key)
    return PROVIDERS.get(resolved)


def list_providers() -> list[dict]:
    """Return all supported providers with setup instructions."""
    return [
        {"id": pid, **pinfo}
        for pid, pinfo in PROVIDERS.items()
    ]
