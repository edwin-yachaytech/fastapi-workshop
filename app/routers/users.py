from fastapi import APIRouter, Depends

from app.models.user import User
from app.schemas.user import UserResponse
from app.security.dependencies import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current authenticated user",
    description="Requires `Authorization: Bearer <access-token>`. Never returns the password hash.",
    responses={401: {"description": "Missing, invalid or expired token"}},
)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
