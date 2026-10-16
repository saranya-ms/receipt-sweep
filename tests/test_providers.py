"""Tests for provider lookup and listing."""

import pytest

from receipt_sweep.providers import PROVIDERS, get_provider, list_providers


@pytest.mark.parametrize(
    "alias, expected_host",
    [
        ("gmail", "imap.gmail.com"),
        ("google", "imap.gmail.com"),
        ("googlemail", "imap.gmail.com"),
        ("yahoo", "imap.mail.yahoo.com"),
        ("yahoomail", "imap.mail.yahoo.com"),
        ("outlook", "outlook.office365.com"),
        ("hotmail", "outlook.office365.com"),
        ("live", "outlook.office365.com"),
        ("msn", "outlook.office365.com"),
        ("office365", "outlook.office365.com"),
        ("icloud", "imap.mail.me.com"),
        ("apple", "imap.mail.me.com"),
        ("me.com", "imap.mail.me.com"),
    ],
)
def test_aliases_resolve(alias, expected_host):
    provider = get_provider(alias)
    assert provider is not None
    assert provider["host"] == expected_host


def test_case_insensitive_and_whitespace():
    assert get_provider("  GMail ") == PROVIDERS["gmail"]
    assert get_provider("HOTMAIL") == PROVIDERS["outlook"]


def test_unknown_provider_returns_none():
    assert get_provider("not-a-provider") is None


def test_list_providers_count_and_shape():
    providers = list_providers()
    assert len(providers) == len(PROVIDERS)
    ids = {p["id"] for p in providers}
    assert ids == set(PROVIDERS)
    for p in providers:
        assert {"id", "name", "host", "port", "help"} <= set(p)
