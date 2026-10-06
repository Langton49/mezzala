import os
from pathlib import Path
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from database.tables import Base
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TEST_DB_URL = f"postgresql+asyncpg://{os.environ.get('POSTGRES_USER', 'fake')}:{os.environ.get('POSTGRES_PASS', 'fake')}@{os.environ.get('TEST_DB_HOST', 'localhost')}:{os.environ.get('TEST_DB_PORT', '5432')}/mezzala_test"

@pytest_asyncio.fixture
async def test_db_session(): 
    ENGINE = create_async_engine(TEST_DB_URL, future=True) 
    async with ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        
    session_factory = async_sessionmaker(ENGINE, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await ENGINE.dispose()


