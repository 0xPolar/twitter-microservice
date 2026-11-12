import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.dependencies.auth import UserToken, VerifyToken, sign_jwt
from src.dependencies.db import get_db, is_unique_conflict
from src.models import User
from src.schemas import CreateUserRequest, LoginUserRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
def health_check():
    """Health check endpoint for load balancers and k8s probes."""
    return {"status": "healthy", "service": "users-service"}


@router.get("/hello")
async def hello(user: UserToken = Depends(VerifyToken)):
    return {"message": f"Hello, {user.username}"}


@router.post("/users/register")
async def register(
    req: CreateUserRequest,
    db: Session = Depends(get_db),
):
    user = User(req.email, req.password, req.username)

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as e:
        db.rollback()
        if is_unique_conflict(e, ("actors_email_key", "actors_username_key")):
            raise HTTPException(
                status_code=409, detail="Email or username already registered"
            ) from e
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="internal server error") from e
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="internal server error")

    try:
        token = sign_jwt(str(user.id), str(user.username))
        return {"user": user.to_dict(), "token": token}
    except Exception as e:
        logger.error(f"Token generation error: {e}")
        raise HTTPException(status_code=500, detail="internal server error")


@router.post("/users/login")
async def login(
    req: LoginUserRequest,
    db: Session = Depends(get_db),
):
    user: User = db.query(User).filter_by(email=req.email).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid Login")

    if not user.verify_password(req.password):
        raise HTTPException(status_code=400, detail="Incorrect Password")

    try:
        token = sign_jwt(str(user.id), str(user.username))
        return {"user": user.to_dict(), "token": token}
    except Exception as e:
        logger.error(f"Token generation error: {e}")
        raise HTTPException(status_code=500, detail="internal server error")
