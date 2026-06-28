from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.config import settings

_engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
