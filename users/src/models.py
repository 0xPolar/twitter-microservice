from sqlalchemy import (
    INT,
    Column,
    UUID,
    DateTime,
    Index,
    String,
    UniqueConstraint,
    false,
    func,
)

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from bcrypt import checkpw
from src.dependencies.db import Base

from uuid import uuid4


password_hasher = PasswordHasher()


class User(Base):
    __tablename__ = "actors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    username = Column(String, nullable=False, unique=True)
    num_tweets = Column(INT, default=0)
    num_followers = Column(INT, default=0)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_users_created_at", "created_at"),
    )

    def __init__(self, email, plaintext_password, username) -> None:
        self.email = email
        self.password = self._generate_password_hash(plaintext_password)
        self.username = username

    def to_dict(self):
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "num_tweets": self.num_tweets,
            "num_followers": self.num_followers,
            "created_at": self.created_at,
        }

    def increment_followers(self, count=1):
        self.num_followers += count
        return self.num_followers

    def verify_password(self, plaintext_password: str) -> bool:
        try:
            stored_hash = self.password
            if isinstance(stored_hash, bytes):
                stored_hash = stored_hash.decode("ascii")
            # Older psycopg2 inserts supplied bytes to the text column, which
            # PostgreSQL can represent as a hex-encoded bytea string.
            if stored_hash.startswith("\\x"):
                stored_hash = bytes.fromhex(stored_hash[2:]).decode("ascii")
            if stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
                return checkpw(plaintext_password.encode("utf-8"), stored_hash.encode("ascii"))
            return password_hasher.verify(stored_hash, plaintext_password)
        except (InvalidHashError, VerificationError, ValueError, UnicodeError):
            return False

    @staticmethod
    def _generate_password_hash(plaintext_password: str) -> str:
        return password_hasher.hash(plaintext_password)

    def increment_tweets(self, count=1):
        self.num_tweets += count
        return self.num_tweets


class Follow(Base):
    __tablename__ = "follows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    follower_id = Column(UUID(as_uuid=True), nullable=False)
    following_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="unique_follow"),
        Index("ix_follows_following_id", "following_id"),
        Index("ix_follows_follower_id", "follower_id"),
        Index("ix_follows_created_at", "created_at"),
    )

    def __init__(self, follower_id, following_id) -> None:
        self.follower_id = follower_id
        self.following_id = following_id

    def to_dict(self):
        return {
            "id": str(self.id),
            "follower_id": str(self.follower_id),
            "following_id": str(self.following_id),
            "created_at": self.created_at,
        }
