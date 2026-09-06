from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import settings

# Lazily connect to db when needed
# echo set to false so I dont see queries in console, pool_size number of connections kept in stock, max_overflow number of connections that can be created above pool_size if needed
engine = create_async_engine(settings.db_url, echo=False, pool_size=10, max_overflow=5)

# A session factory that will create new AsyncSession objects when called
# expire_on_commit=False means that objects will not be expired after commit, so they can still be used after a commit.
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_session():
    """
    Async generator that yields a database session and ensures it is closed after use.
    """
    print("Session opened")
    async with async_session() as session:
        yield session
    print("Session closed")