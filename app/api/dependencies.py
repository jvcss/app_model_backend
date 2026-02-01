from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import SessionAsync, SessionSync
from app.helpers.getters import isDebugMode
from app.models.user import User
from app.core.security import SECRET_KEY, ALGORITHM
from app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    description="Autenticação via email e senha"
)

async def get_db():
    async with SessionAsync() as session:
        yield session

def get_db_sync():
    db = SessionSync()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
        token: str = Depends(oauth2_scheme),
                     db: AsyncSession = Depends(get_db),
                     ):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        tv = payload.get("tv")
        if user_id is None or tv is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or int(tv) != int(user.token_version or 1):
        raise credentials_exception
    return user

async def get_redis():
    redis = await aioredis.from_url(
        settings.CELERY_BROKER_URL_EXTERNAL if isDebugMode() else settings.CELERY_BROKER_URL
    )
    try:
        yield redis
    finally:
        await redis.close()
