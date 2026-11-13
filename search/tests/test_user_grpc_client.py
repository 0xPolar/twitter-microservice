from unittest.mock import MagicMock

import grpc
import pytest

from src.grpc import client
from src.grpc.client import user_service_pb2 as pb2


@pytest.fixture
def stub(monkeypatch):
    stub = MagicMock()
    monkeypatch.setattr(client.grpc, "insecure_channel", MagicMock())
    monkeypatch.setattr(client, "UserStub", lambda channel: stub)
    return stub


@pytest.mark.parametrize("valid", [False, True])
def test_user_lookup_honors_valid_flag(stub, valid):
    stub.GetUser.return_value = pb2.GetUserRes(valid=valid, user=pb2.UserStruct(id="user-id", username="name"))
    result = client.GetUser("user-id")
    request = stub.GetUser.call_args.args[0]
    assert isinstance(request, pb2.GetUserReq)
    assert request.user_id == "user-id"
    if valid:
        assert result.id == "user-id"
        assert result.username == "name"
    else:
        assert result is None


class Unavailable(grpc.RpcError):
    def code(self):
        return grpc.StatusCode.UNAVAILABLE

    def details(self):
        return "Users unavailable"


def test_user_lookup_transport_failure(stub):
    stub.GetUser.side_effect = Unavailable()
    assert client.GetUser("user-id") is None


@pytest.mark.parametrize("success", [False, True])
def test_increment_uses_declared_request_type(stub, success):
    stub.IncrementsTweets.return_value = pb2.IncrementTweetsRes(success=success)
    response = client.IncrementTweets("user-id")
    request = stub.IncrementsTweets.call_args.args[0]
    assert isinstance(request, pb2.IncrementTweetsReq)
    assert request.user_id == "user-id"
    assert response.success is success


def test_increment_transport_failure(stub):
    stub.IncrementsTweets.side_effect = Unavailable()
    assert client.IncrementTweets("user-id") is None
