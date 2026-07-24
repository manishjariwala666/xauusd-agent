from services import production_agents


class FakeMappings:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class FakeResult:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return FakeMappings(self._row)


class FakeSession:
    def __init__(self, row):
        self._row = row

    def execute(self, statement, params=None):
        return FakeResult(self._row)


class FakeSessionScope:
    def __init__(self, row):
        self._row = row

    def __enter__(self):
        return FakeSession(self._row)

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeWhatsAppService:
    def __init__(self):
        self.calls = []

    def send_text(self, recipient, message):
        self.calls.append((recipient, message))
        return "wamid.test-123"


def test_send_client_welcome_returns_sent_proof(monkeypatch):
    fake_service = FakeWhatsAppService()

    monkeypatch.setattr(
        production_agents,
        "session_scope",
        lambda: FakeSessionScope(
            {
                "id": 11,
                "name": "Dilipbhai Devmorari",
                "whatsapp": "919999999999",
            }
        ),
    )
    monkeypatch.setattr(
        production_agents,
        "WhatsAppService",
        lambda: fake_service,
    )

    result = production_agents.run_whatsapp_reply_agent(
        {
            "master_ai_action": "send_client_welcome",
            "client_name": "Dilipbhai Devmorari",
        }
    )

    assert "Status: SENT" in result
    assert "Message reference: wamid.test-123" in result
    assert "Delivery confirmation pending." in result
    assert fake_service.calls
    assert fake_service.calls[0][0] == "919999999999"
    assert "Welcome to VenusRealm, Dilipbhai Devmorari" in fake_service.calls[0][1]
