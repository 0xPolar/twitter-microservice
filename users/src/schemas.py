from pydantic import BaseModel, EmailStr
from uuid import UUID


# User Schemas
class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: EmailStr


class LoginUserRequest(BaseModel):
    email: EmailStr
    password: str


# Follower Schemas
class CreateFollowerRequset(BaseModel):
    following_id: UUID
