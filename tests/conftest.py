import asyncio
import os
import tempfile
import pytest
import pytest_asyncio

import database

# Use a temp file for tests (aiosqlite doesn't share :memory: across connections)
@pytest.fixture(scope="session")
def tmp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path

@pytest.fixture(scope="session", autouse=True)
def set_db_path(tmp_db_path):
    old = os.environ.get("DB_PATH")
    os.environ["DB_PATH"] = tmp_db_path
    yield
    os.environ["DB_PATH"] = old if old else ""
    if os.path.exists(tmp_db_path):
        os.unlink(tmp_db_path)

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    await database.init_db()
    # Clear tables between tests
    async with database.get_connection() as conn:
        await conn.execute("DELETE FROM chores")
        await conn.execute("DELETE FROM banned_users")
        await conn.commit()
    yield
