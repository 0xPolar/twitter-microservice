import pytest
from unittest.mock import patch

from bcrypt import hashpw, gensalt

from src.models import User


class TestUserModel:
    def test_password_survives_database_round_trip(self, test_db):
        user = User("roundtrip@example.com", "password123", "roundtrip")
        test_db.add(user)
        test_db.commit()
        user_id = user.id
        test_db.expunge_all()
        stored = test_db.get(User, user_id)
        assert isinstance(stored.password, str)
        assert stored.password.startswith("$argon2id$")
        assert stored.password != "password123"
        assert stored.verify_password("password123")
        assert not stored.verify_password("wrongpassword")
        assert "password" not in stored.to_dict()

    def test_long_unicode_password_is_not_truncated(self):
        password = "🔒" * 100
        user = User("long@example.com", password, "long")
        assert user.verify_password(password)
        assert not user.verify_password(password + "different")

    def test_password_hashes_use_distinct_salts(self):
        first = User("first@example.com", "same-password", "first")
        second = User("second@example.com", "same-password", "second")
        assert first.password != second.password
        assert first.verify_password("same-password")
        assert second.verify_password("same-password")

    @pytest.mark.parametrize("representation", ["text", "bytes", "postgres_hex"])
    def test_legacy_bcrypt_passwords(self, test_db, representation):
        encoded = hashpw(b"legacy-password", gensalt(rounds=4))
        legacy = {"text": encoded.decode("ascii"), "bytes": encoded,
                  "postgres_hex": "\\x" + encoded.hex()}[representation]
        user = User("legacy@example.com", "unused", "legacy")
        user.password = legacy
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        assert user.verify_password("legacy-password")
        assert not user.verify_password("wrong-password")
        assert not user.verify_password("x" * 100)
        assert user.password == legacy

    @pytest.mark.parametrize("stored_hash", ["broken", "$argon2id$broken", "\\xnothex", b"\xff"])
    def test_corrupt_hash_does_not_raise(self, stored_hash):
        user = User("corrupt@example.com", "unused", "corrupt")
        user.password = stored_hash
        assert not user.verify_password("password")

    def test_increment_followers(self):
        """Test incrementing follower count."""
        with patch("src.models.User._generate_password_hash") as mock_hashpw:
            mock_hashpw.return_value = "hashed"

            from src.models import User
            user = User("test@example.com", "pass", "testuser")
            user.num_followers = 5

            result = user.increment_followers()

            assert result == 6
            assert user.num_followers == 6

    def test_increment_followers_custom_count(self):
        """Test incrementing follower count by custom amount."""
        with patch("src.models.User._generate_password_hash") as mock_hashpw:
            mock_hashpw.return_value = "hashed"

            from src.models import User
            user = User("test@example.com", "pass", "testuser")
            user.num_followers = 5

            result = user.increment_followers(3)

            assert result == 8

    def test_increment_tweets(self):
        """Test incrementing tweet count."""
        with patch("src.models.User._generate_password_hash") as mock_hashpw:
            mock_hashpw.return_value = "hashed"

            from src.models import User
            user = User("test@example.com", "pass", "testuser")
            user.num_tweets = 10

            result = user.increment_tweets()

            assert result == 11

    def test_to_dict(self):
        """Test user serialization to dictionary."""
        with patch("src.models.User._generate_password_hash") as mock_hashpw:
            mock_hashpw.return_value = "hashed"

            from src.models import User
            user = User("test@example.com", "pass", "testuser")
            user.num_tweets = 5
            user.num_followers = 10

            result = user.to_dict()

            assert result["email"] == "test@example.com"
            assert result["username"] == "testuser"
            assert result["num_tweets"] == 5
            assert result["num_followers"] == 10
            assert "password" not in result  # Password should not be in dict


class TestFollowModel:
    """Tests for the Follow model."""

    def test_follow_creation(self):
        """Test that Follow can be instantiated."""
        from src.models import Follow

        follow = Follow(
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002"
        )

        assert str(follow.follower_id) == "550e8400-e29b-41d4-a716-446655440001"
        assert str(follow.following_id) == "550e8400-e29b-41d4-a716-446655440002"

    def test_follow_to_dict(self):
        """Test follow serialization to dictionary."""
        from src.models import Follow

        follow = Follow(
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002"
        )

        result = follow.to_dict()

        assert "id" in result
        assert result["follower_id"] == "550e8400-e29b-41d4-a716-446655440001"
        assert result["following_id"] == "550e8400-e29b-41d4-a716-446655440002"
