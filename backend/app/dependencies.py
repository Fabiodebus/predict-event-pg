import logging
from functools import lru_cache
from typing import Literal
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, ValidationError

from app.config import settings
from app.middleware.cognito import CognitoTokenValidator, InvalidTokenError

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=True)


class UserContext(BaseModel):
    user_id: UUID
    workspace_id: UUID
    email: EmailStr
    role: Literal["customer", "gtm_engineer"]


@lru_cache(maxsize=1)
def get_token_validator() -> CognitoTokenValidator:
    return CognitoTokenValidator(
        user_pool_id=settings.cognito_user_pool_id,
        client_id=settings.cognito_client_id,
        region=settings.cognito_region,
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    validator: CognitoTokenValidator = Depends(get_token_validator),
) -> UserContext:
    try:
        claims = validator.validate(token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        return UserContext(
            user_id=claims["sub"],
            workspace_id=claims["custom:workspace_id"],
            email=claims["email"],
            role=claims["custom:role"],
        )
    except (KeyError, ValueError, ValidationError) as exc:
        # Don't leak claim values back in the 401 body — log server-side instead.
        logger.warning("Token claims invalid", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
