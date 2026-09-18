"""Payment instructions and submission preserve paid member access."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services import member_auth_api as api
from services.member_auth_dependency import require_authenticated_member
from services.member_auth_service import MemberIdentity


@pytest.fixture
def payment_client(monkeypatch):
    identity = MemberIdentity(123, 'member@example.test', 'USER', True, 'PENDING', 'NOT_STARTED')
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[require_authenticated_member] = lambda: identity
    settings = SimpleNamespace(usdt_wallet_address='configured-wallet', usdt_network='TRC20', subscription_price_usdt='50')
    monkeypatch.setattr(api, 'get_settings', lambda: settings)
    monkeypatch.setattr(api, 'get_user_payment', lambda _: {'payment_status': identity.payment_status})
    submit = Mock()
    monkeypatch.setattr(api, 'submit_payment', submit)
    return TestClient(app), app, settings, submit


def test_member_gets_complete_payment_instructions(payment_client):
    client, _, _, _ = payment_client
    response = client.get('/api/v1/member/payment')
    assert response.status_code == 200
    assert response.json()['instructions'] == {
        'wallet_address': 'configured-wallet', 'network': 'TRC20', 'amount_usdt': '50'
    }


def test_payment_submits_for_review_without_granting_access(payment_client):
    client, _, _, submit = payment_client
    response = client.post('/api/v1/member/payment/submit', json={'transaction_id': 'valid-txid'})
    assert response.status_code == 200
    assert response.json()['payment_status'] == 'PENDING'
    submit.assert_called_once_with(user_id=123, transaction_id='valid-txid', amount_usdt='50', network='TRC20')


@pytest.mark.parametrize('status', ['VERIFIED', 'PENDING', 'UNDER_REVIEW'])
def test_existing_membership_cannot_be_resubmitted(payment_client, status):
    client, app, _, submit = payment_client
    identity = MemberIdentity(123, 'member@example.test', 'USER', True, 'APPROVED', status)
    app.dependency_overrides[require_authenticated_member] = lambda: identity
    # The payment record is authoritative for pending reviews.
    from unittest.mock import patch
    with patch.object(api, 'get_user_payment', return_value={'payment_status': status}):
        response = client.post('/api/v1/member/payment/submit', json={'transaction_id': 'valid-txid'})
    assert response.status_code == 409
    submit.assert_not_called()


def test_missing_wallet_cannot_accept_payment(payment_client):
    client, _, settings, submit = payment_client
    settings.usdt_wallet_address = ''
    response = client.post('/api/v1/member/payment/submit', json={'transaction_id': 'valid-txid'})
    assert response.status_code == 503
    submit.assert_not_called()


def test_invalid_transaction_returns_actionable_client_error(payment_client):
    client, _, _, submit = payment_client
    submit.side_effect = ValueError('Enter a valid transaction ID.')
    response = client.post('/api/v1/member/payment/submit', json={'transaction_id': '        '})
    assert response.status_code == 400
