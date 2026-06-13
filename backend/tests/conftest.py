"""测试配置和公共fixtures"""
import os
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# 设置测试环境变量
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "param_experiment_test"
os.environ["POSTGRES_USER"] = "postgres"
os.environ["POSTGRES_PASSWORD"] = "postgres"
os.environ["SQLITE_DB_PATH"] = os.path.join(os.path.dirname(__file__), "..", "..", "data", "geomods_2.0.db")
os.environ["DEEPSEEK_API_KEY"] = "test-key"

from app.database import Base, get_db
from app.main import app

# 使用同步引擎创建表（避免asyncpg并发问题）
SYNC_URL = "postgresql://postgres:postgres@localhost:5432/param_experiment_test"
sync_engine = create_engine(SYNC_URL, echo=False)
Base.metadata.create_all(sync_engine)
sync_engine.dispose()


@pytest.fixture
async def client():
    """每个测试创建独立的AsyncClient，使用独立的数据库session"""
    # 为每个测试创建独立的异步引擎
    test_engine = create_async_engine(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/param_experiment_test",
        echo=False,
        pool_size=2,
        max_overflow=2
    )
    test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with test_session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.fixture(autouse=True)
async def clean_db():
    """每个测试前后清理数据库"""
    yield
    # 测试后清理所有表数据
    sync_engine2 = create_engine(SYNC_URL, echo=False)
    with sync_engine2.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()
    sync_engine2.dispose()
