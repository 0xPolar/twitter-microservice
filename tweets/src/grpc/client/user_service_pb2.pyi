from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FollowStruct(_message.Message):
    __slots__ = ("id", "follower_id", "following_id", "created_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    FOLLOWER_ID_FIELD_NUMBER: _ClassVar[int]
    FOLLOWING_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    follower_id: str
    following_id: str
    created_at: int
    def __init__(self, id: _Optional[str] = ..., follower_id: _Optional[str] = ..., following_id: _Optional[str] = ..., created_at: _Optional[int] = ...) -> None: ...

class UserStruct(_message.Message):
    __slots__ = ("id", "email", "username", "numTweets", "numFollowers", "created_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    NUMTWEETS_FIELD_NUMBER: _ClassVar[int]
    NUMFOLLOWERS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    email: str
    username: str
    numTweets: int
    numFollowers: int
    created_at: int
    def __init__(self, id: _Optional[str] = ..., email: _Optional[str] = ..., username: _Optional[str] = ..., numTweets: _Optional[int] = ..., numFollowers: _Optional[int] = ..., created_at: _Optional[int] = ...) -> None: ...

class GetUserReq(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class GetUserRes(_message.Message):
    __slots__ = ("valid", "user")
    VALID_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    valid: bool
    user: UserStruct
    def __init__(self, valid: bool = ..., user: _Optional[_Union[UserStruct, _Mapping]] = ...) -> None: ...

class IncrementTweetsReq(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class IncrementTweetsRes(_message.Message):
    __slots__ = ("success",)
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    def __init__(self, success: bool = ...) -> None: ...

class GetFollowersReq(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class GetFollowersRes(_message.Message):
    __slots__ = ("followers",)
    FOLLOWERS_FIELD_NUMBER: _ClassVar[int]
    followers: _containers.RepeatedCompositeFieldContainer[FollowStruct]
    def __init__(self, followers: _Optional[_Iterable[_Union[FollowStruct, _Mapping]]] = ...) -> None: ...

class GetFollowingReq(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class GetFollowingRes(_message.Message):
    __slots__ = ("following",)
    FOLLOWING_FIELD_NUMBER: _ClassVar[int]
    following: _containers.RepeatedCompositeFieldContainer[FollowStruct]
    def __init__(self, following: _Optional[_Iterable[_Union[FollowStruct, _Mapping]]] = ...) -> None: ...
