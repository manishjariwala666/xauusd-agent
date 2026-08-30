from contextlib import contextmanager

import services.signal_channel_delivery as delivery


class FakeMappings:
    def __init__(self, rows=None, first=None):
        self._rows = rows or []
        self._first = first

    def all(self):
        return self._rows

    def first(self):
        return self._first


class FakeResult:
    def __init__(self, rows=None, first=None):
        self._rows = rows or []
        self._first = first

    def mappings(self):
        return FakeMappings(self._rows, self._first)


class FakeDB:
    def __init__(self):
        self.signal = {
            "id": 101,
            "signal_type": "BUY",
            "signal_time": "2026-08-18T10:00:00+00:00",
        }
        self.ledger = {}
        self.next_id = 1
        self.legacy_marked = False
        self.claimed_recipients = []
        self.signal_select_sql = []

    @contextmanager
    def session_scope(self):
        yield FakeSession(self)


class FakeSession:
    def __init__(self, db):
        self.db = db

    def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}

        if "SELECT *" in sql and "FROM public.market_signals" in sql:
            self.db.signal_select_sql.append(sql)
            return FakeResult(rows=[self.db.signal])

        if "INSERT INTO public.signal_channel_deliveries" in sql:
            key = (
                params["signal_id"],
                params["channel"],
                params["recipient_hash"],
            )
            if key not in self.db.ledger:
                self.db.ledger[key] = {
                    "id": self.db.next_id,
                    "attempts": 0,
                    "sent": False,
                    "claimed": False,
                    "error": None,
                }
                self.db.next_id += 1
            return FakeResult()

        if "UPDATE public.signal_channel_deliveries" in sql and "RETURNING id" in sql:
            key = (
                params["signal_id"],
                params["channel"],
                params["recipient_hash"],
            )
            row = self.db.ledger[key]
            if row["sent"] or row["attempts"] >= params["max_attempts"] or row["claimed"]:
                return FakeResult(first=None)
            row["attempts"] += 1
            row["claimed"] = True
            self.db.claimed_recipients.append(params["recipient_hash"])
            return FakeResult(first={"id": row["id"]})

        if "UPDATE public.signal_channel_deliveries" in sql and "WHERE id = :delivery_id" in sql:
            delivery_id = params["delivery_id"]
            row = next(value for value in self.db.ledger.values() if value["id"] == delivery_id)
            if params["sent"]:
                row["sent"] = True
            else:
                row["claimed"] = False
            row["error"] = params["error_category"]
            return FakeResult()

        if "UPDATE public.market_signals" in sql:
            channel = params["channel"]
            pending = any(
                key[0] == params["signal_id"]
                and key[1] == channel
                and not row["sent"]
                for key, row in self.db.ledger.items()
            )
            if not pending:
                self.db.legacy_marked = True
            return FakeResult()

        raise AssertionError(f"Unexpected SQL: {sql}")


def _hash(recipient):
    return delivery._recipient_hash(recipient)


def test_delivery_query_matches_website_publication_contract(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(delivery, "session_scope", db.session_scope)

    assert delivery.deliver_pending_signal_recipients(
        channel="telegram",
        recipients=["chat-1"],
        send=lambda recipient, message: "ok",
        format_message=lambda signal: "BUY",
        verify_signal=lambda signal: (True, "verified"),
    ) == (1, 0)

    assert len(db.signal_select_sql) == 1
    sql = db.signal_select_sql[0]
    assert "publication_status = 'PUBLISHED'" in sql
    assert "deleted_at IS NULL" in sql


def test_partial_failure_retries_only_failed_recipient(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(delivery, "session_scope", db.session_scope)

    sends = []
    failures_remaining = {"222": 1}

    def send(recipient, message):
        sends.append(recipient)
        if failures_remaining.get(recipient, 0):
            failures_remaining[recipient] -= 1
            raise RuntimeError("temporary")
        return f"msg-{recipient}"

    kwargs = dict(
        channel="whatsapp",
        recipients=["111", "222"],
        send=send,
        format_message=lambda signal: "BUY",
        max_attempts=3,
        verify_signal=lambda signal: (True, "verified"),
    )

    assert delivery.deliver_pending_signal_recipients(**kwargs) == (1, 1)
    assert sends == ["111", "222"]
    assert db.legacy_marked is False
    assert db.ledger[(101, "whatsapp", _hash("111"))]["sent"] is True
    assert db.ledger[(101, "whatsapp", _hash("222"))]["sent"] is False

    assert delivery.deliver_pending_signal_recipients(**kwargs) == (1, 0)
    assert sends == ["111", "222", "222"]
    assert db.legacy_marked is True
    assert db.ledger[(101, "whatsapp", _hash("222"))]["sent"] is True


def test_successful_recipient_is_not_resent(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(delivery, "session_scope", db.session_scope)

    sends = []

    def send(recipient, message):
        sends.append(recipient)
        return "ok"

    kwargs = dict(
        channel="telegram",
        recipients=["chat-1"],
        send=send,
        format_message=lambda signal: "BUY",
        verify_signal=lambda signal: (True, "verified"),
    )

    assert delivery.deliver_pending_signal_recipients(**kwargs) == (1, 0)
    assert delivery.deliver_pending_signal_recipients(**kwargs) == (0, 0)
    assert sends == ["chat-1"]


def test_verification_block_creates_no_delivery_claim(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(delivery, "session_scope", db.session_scope)

    sends = []
    result = delivery.deliver_pending_signal_recipients(
        channel="telegram",
        recipients=["chat-1"],
        send=lambda recipient, message: sends.append(recipient),
        format_message=lambda signal: "SELL",
        verify_signal=lambda signal: (False, "Captain WAIT"),
    )

    assert result == (0, 0)
    assert sends == []
    assert db.ledger == {}
    assert db.legacy_marked is False
