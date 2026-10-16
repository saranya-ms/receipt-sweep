"""Connection handling: concurrent calls, dropped sessions, and surfaced errors."""

import imaplib
import threading
import time

import pytest

from receipt_sweep.imap_client import ConnectionLost, IMAPClient


class _OverlapDetectingConn:
    """Fake connection that records whether two commands ever ran at once."""

    def __init__(self):
        self.active = 0
        self.overlapped = False
        self._guard = threading.Lock()

    def _enter(self):
        with self._guard:
            self.active += 1
            if self.active > 1:
                self.overlapped = True
        time.sleep(0.01)  # widen the window for interleaving
        with self._guard:
            self.active -= 1

    def select(self, mailbox, readonly=True):
        self._enter()
        return ("OK", [b"1"])

    def search(self, charset, criteria):
        self._enter()
        return ("OK", [b""])


def test_concurrent_calls_are_serialized():
    # Parallel tool calls used to interleave on the one IMAP socket and kill it.
    client = IMAPClient()
    conn = _OverlapDetectingConn()
    client._conn = conn

    threads = [
        threading.Thread(target=client.search_emails, kwargs={"query": f"q{i}"})
        for i in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert conn.overlapped is False


class _DroppingConn:
    """Fake connection whose search fails as if the socket was closed."""

    def select(self, mailbox, readonly=True):
        return ("OK", [b"1"])

    def search(self, charset, criteria):
        raise imaplib.IMAP4.abort("socket error: EOF occurred in violation of protocol")

    def logout(self):
        pass


class _HealthyConn:
    def select(self, mailbox, readonly=True):
        return ("OK", [b"1"])

    def search(self, charset, criteria):
        return ("OK", [b""])


def test_dropped_connection_reconnects_and_retries(monkeypatch):
    client = IMAPClient()
    client._conn = _DroppingConn()
    client._creds = ("imap.example.com", 993, "me@example.com", "app-password")
    opened = []

    def fake_open(*creds):
        opened.append(creds)
        return _HealthyConn()

    monkeypatch.setattr(IMAPClient, "_open", staticmethod(fake_open))

    assert client.search_emails(query="receipt") == []
    assert opened == [("imap.example.com", 993, "me@example.com", "app-password")]
    assert isinstance(client._conn, _HealthyConn)


def test_dropped_connection_without_credentials_raises_clear_error():
    client = IMAPClient()
    client._conn = _DroppingConn()

    with pytest.raises(ConnectionLost, match="connect_email again"):
        client.search_emails(query="receipt")
    assert client.connected is False


class _NoSuchFolderConn:
    def select(self, mailbox, readonly=True):
        return ("NO", [b"Mailbox does not exist"])


def test_unopenable_folder_is_an_error_not_an_empty_result():
    client = IMAPClient()
    client._conn = _NoSuchFolderConn()
    with pytest.raises(ValueError, match="could not be opened"):
        client.search_emails(folder="Nope")


class _RejectingConn:
    def select(self, mailbox, readonly=True):
        return ("OK", [b"1"])

    def search(self, charset, criteria):
        raise imaplib.IMAP4.error("BAD Could not parse command")


def test_rejected_search_raises_instead_of_returning_everything():
    # The old fallback re-ran the search as ALL, returning unfiltered mail.
    client = IMAPClient()
    client._conn = _RejectingConn()
    with pytest.raises(ValueError, match="rejected the search"):
        client.search_emails(query="receipt")


def test_bad_date_is_rejected_rather_than_ignored():
    client = IMAPClient()
    client._conn = _HealthyConn()
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        client.search_emails(since="16/07/2026")


class _DeadSocketConn:
    """Looks connected, but the server has already closed the socket."""

    def noop(self):
        raise imaplib.IMAP4.abort("socket error: EOF")

    def logout(self):
        pass


class _AliveConn:
    def noop(self):
        return ("OK", [b"NOOP completed"])


def test_ping_reopens_a_silently_dropped_session(monkeypatch):
    # `connected` stayed True after the socket died, so every later call
    # failed with EOF while the status still said "Connected".
    client = IMAPClient()
    client._conn = _DeadSocketConn()
    client._creds = ("imap.example.com", 993, "me@example.com", "app-password")
    monkeypatch.setattr(IMAPClient, "_open", staticmethod(lambda *c: _AliveConn()))

    assert client.ping() is True
    assert isinstance(client._conn, _AliveConn)


def test_ping_without_credentials_reports_lost_connection():
    client = IMAPClient()
    client._conn = _DeadSocketConn()
    with pytest.raises(ConnectionLost):
        client.ping()
    assert client.connected is False


def test_disconnect_forgets_credentials():
    client = IMAPClient()
    client._conn = _HealthyConn()
    client._creds = ("imap.example.com", 993, "me@example.com", "app-password")
    client.disconnect()
    assert client._creds is None
    assert client.connected is False
