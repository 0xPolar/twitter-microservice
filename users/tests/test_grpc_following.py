from datetime import datetime, timezone
from uuid import UUID, uuid4

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
import pytest

from src.grpc import server as user_server
from src.grpc import user_service_pb2 as pb2
from src.models import Follow


@pytest.mark.parametrize("transport", ["direct", "grpc"])
@pytest.mark.parametrize("populated", [False, True])
def test_get_following_returns_outgoing_relationships(grpc_database, user_grpc_stub, transport, populated):
    # A valid UUID1 also detects accidental rewriting of UUID version bits.
    user_id = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    created_at = datetime(2026, 11, 13, 10, 20, tzinfo=timezone.utc)
    expected = {}
    if populated:
        for _ in range(2):
            follow = Follow(user_id, uuid4())
            follow.created_at = created_at
            grpc_database.add(follow)
            grpc_database.flush()
            expected[str(follow.id)] = str(follow.following_id)
    # Incoming follows and another user's outgoing follows must be excluded.
    grpc_database.add(Follow(uuid4(), user_id))
    grpc_database.add(Follow(uuid4(), uuid4()))
    grpc_database.commit()

    request = pb2.GetFollowingReq(user_id=str(user_id))
    if transport == "direct":
        response = user_server.UserService().GetFollowing(request, None)
    else:
        response = user_grpc_stub.GetFollowing(request, timeout=5)

    assert isinstance(response, pb2.GetFollowingRes)
    assert {follow.id: follow.following_id for follow in response.following} == expected
    for follow in response.following:
        assert follow.follower_id == str(user_id)
        assert follow.created_at == int(created_at.timestamp())


def test_field_rename_preserves_binary_compatibility():
    assert pb2.GetFollowingRes.DESCRIPTOR.fields_by_name["following"].number == 1
    descriptor = descriptor_pb2.FileDescriptorProto.FromString(pb2.DESCRIPTOR.serialized_pb)
    message = next(message for message in descriptor.message_type if message.name == "GetFollowingRes")
    message.field[0].name = "follwing"
    message.field[0].json_name = "follwing"
    pool = descriptor_pool.DescriptorPool()
    pool.Add(descriptor)
    legacy_type = message_factory.GetMessageClass(pool.FindMessageTypeByName("user_service.GetFollowingRes"))
    current = pb2.GetFollowingRes(following=[pb2.FollowStruct(id="relationship", follower_id="source", following_id="target")])
    legacy = legacy_type.FromString(current.SerializeToString())
    assert legacy.follwing[0].id == "relationship"
    assert legacy.follwing[0].follower_id == "source"
    assert legacy.follwing[0].following_id == "target"
