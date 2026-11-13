from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.grpc import user_service_pb2 as pb2
from src.models import User


@pytest.mark.parametrize("user_id", [UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"), uuid4()])
@pytest.mark.parametrize("count", [None, 7])
def test_user_lookup_preserves_identity_and_fields(grpc_database, user_grpc_stub, user_id, count):
    created_at = datetime(2026, 11, 13, 12, 30, tzinfo=timezone.utc)
    user = User("lookup@example.com", "password", "lookup")
    user.id = user_id
    user.created_at = created_at
    grpc_database.add(user)
    grpc_database.commit()
    # Assign NULL after insertion so column defaults do not replace it.
    user.num_tweets = count
    user.num_followers = count
    grpc_database.commit()

    response = user_grpc_stub.GetUser(pb2.GetUserReq(user_id=str(user_id)), timeout=5)
    assert response.valid
    assert response.HasField("user")
    assert response.user.id == str(user_id)
    assert response.user.email == "lookup@example.com"
    assert response.user.username == "lookup"
    assert response.user.numTweets == (count or 0)
    assert response.user.numFollowers == (count or 0)
    assert response.user.created_at == int(created_at.timestamp())


def test_missing_user_responses_do_not_create_accounts(grpc_database, user_grpc_stub):
    user_id = str(uuid4())
    lookup = user_grpc_stub.GetUser(pb2.GetUserReq(user_id=user_id), timeout=5)
    assert not lookup.valid
    assert not lookup.HasField("user")
    increment = user_grpc_stub.IncrementsTweets(pb2.IncrementTweetsReq(user_id=user_id), timeout=5)
    assert not increment.success
    assert grpc_database.query(User).count() == 0


@pytest.mark.parametrize("initial_count", [None, 0, 9])
def test_increment_persists_and_is_visible_to_lookup(grpc_database, user_grpc_stub, initial_count):
    target = User("target@example.com", "password", "target")
    other = User("other@example.com", "password", "other")
    # This detects UUID version rewriting in the counter RPC too.
    target.id = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    grpc_database.add_all([target, other])
    grpc_database.commit()
    target.num_tweets = initial_count
    other.num_tweets = 12
    grpc_database.commit()

    for _ in range(3):
        response = user_grpc_stub.IncrementsTweets(pb2.IncrementTweetsReq(user_id=str(target.id)), timeout=5)
        assert response.success
    grpc_database.refresh(target)
    grpc_database.refresh(other)
    assert target.num_tweets == (initial_count or 0) + 3
    assert other.num_tweets == 12
    lookup = user_grpc_stub.GetUser(pb2.GetUserReq(user_id=str(target.id)), timeout=5)
    assert lookup.user.numTweets == target.num_tweets


@pytest.mark.parametrize("operation", ["query", "commit"])
def test_increment_database_failure_rolls_back(grpc_database, user_grpc_stub, operation):
    user = User("rollback@example.com", "password", "rollback")
    user.num_tweets = 4
    grpc_database.add(user)
    grpc_database.commit()
    user_id = str(user.id)
    with patch(f"sqlalchemy.orm.Session.{operation}", side_effect=SQLAlchemyError("database failure")):
        response = user_grpc_stub.IncrementsTweets(pb2.IncrementTweetsReq(user_id=user_id), timeout=5)
    assert not response.success
    grpc_database.refresh(user)
    assert user.num_tweets == 4
    response = user_grpc_stub.IncrementsTweets(pb2.IncrementTweetsReq(user_id=user_id), timeout=5)
    assert response.success
    grpc_database.refresh(user)
    assert user.num_tweets == 5
