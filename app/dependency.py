from typing import Annotated
from fastapi import Depends, Header, HTTPException
from models import Session, Token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid, datetime
from config import TOKEN_TTL_SEC
import models


async def get_session() -> AsyncSession:
    async with Session() as session:
        yield session


SessionDependency = Annotated[AsyncSession, Depends(get_session)]


async def get_token(
    x_token: Annotated[uuid.UUID, Header()], session: SessionDependency
) -> Token:
    query = select(Token).where(
        Token.token == x_token,
        Token.creation_time
        >= (datetime.datetime.now() - datetime.timedelta(seconds=TOKEN_TTL_SEC)),
    )
    token = await session.scalar(query)
    if token is None:
        raise HTTPException(401, "Token not found")
    return token


TokenDependency = Annotated[Token, Depends(get_token)]


async def get_current_user(token: TokenDependency, session: SessionDependency) -> models.User:
    user_id = token.user_id
    user = await session.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail='user not found')
    return user


CurrentUserDependency = Annotated[models.User, Depends(get_current_user)]