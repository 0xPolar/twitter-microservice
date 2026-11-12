from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
import jwt
import pytest

from src.dependencies import auth
from src.routes.user_routes import router


@pytest.fixture(autouse=True)
def jwt_settings(monkeypatch):
    monkeypatch.setattr(auth, "JWT_SECRET", "test-secret-key-for-auth-tests-only")
    monkeypatch.setattr(auth, "JWT_ALGO", "HS256")


@pytest.fixture
def payload():
    now = datetime.now(timezone.utc)
    return {"user_id": "user-123", "username": "testuser", "iat": now,
            "exp": now + timedelta(hours=48)}


def encode(payload, secret=None, algorithm="HS256"):
    return jwt.encode(payload, secret or auth.JWT_SECRET, algorithm=algorithm)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        yield client


def test_signed_token_contains_identity_and_48_hour_expiry():
    token = auth.sign_jwt("user-123", "testuser")
    decoded = auth.decode_jwt(token)
    assert decoded["user_id"] == "user-123"
    assert decoded["username"] == "testuser"
    assert decoded["exp"] - decoded["iat"] == 48 * 60 * 60


def test_valid_token_authenticates(client):
    response = client.get("/hello", headers={"Authorization": "Bearer " + auth.sign_jwt("user-123", "testuser")})
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, testuser"}


@pytest.mark.parametrize("claim", ["user_id", "username", "exp", "iat"])
def test_missing_required_claim_is_rejected(client, payload, claim):
    del payload[claim]
    token = encode(payload)
    with pytest.raises(jwt.InvalidTokenError):
        auth.decode_jwt(token)
    assert client.get("/hello", headers={"Authorization": "Bearer " + token}).status_code == 403


@pytest.mark.parametrize("claim,value", [("user_id", 123), ("user_id", ""), ("username", []), ("username", 42)])
def test_malformed_identity_is_rejected(client, payload, claim, value):
    payload[claim] = value
    assert client.get("/hello", headers={"Authorization": "Bearer " + encode(payload)}).status_code == 403


def test_expired_token_is_rejected(client, payload):
    payload["iat"] = datetime.now(timezone.utc) - timedelta(hours=2)
    payload["exp"] = datetime.now(timezone.utc) - timedelta(hours=1)
    token = encode(payload)
    with pytest.raises(jwt.ExpiredSignatureError):
        auth.decode_jwt(token)
    response = client.get("/hello", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 403
    assert response.json()["detail"] == "Expired JWT Token"


@pytest.mark.parametrize("kind", ["wrong_signature", "wrong_algorithm", "malformed", "future_iat"])
def test_invalid_tokens_are_rejected(client, payload, kind):
    if kind == "wrong_signature":
        token = encode(payload, secret="a-different-signing-key-for-tests")
    elif kind == "wrong_algorithm":
        token = encode(payload, algorithm="HS512")
    elif kind == "future_iat":
        payload["iat"] = datetime.now(timezone.utc) + timedelta(hours=1)
        token = encode(payload)
    else:
        token = "invalid.token.here"
    with pytest.raises(jwt.InvalidTokenError):
        auth.decode_jwt(token)
    assert client.get("/hello", headers={"Authorization": "Bearer " + token}).status_code == 403


@pytest.mark.parametrize("header", [None, "Basic credentials", "Bearer"])
def test_missing_bearer_credentials_are_rejected(client, header):
    headers = {"Authorization": header} if header else {}
    assert client.get("/hello", headers=headers).status_code == 403
