import pytest

import database

@pytest.mark.asyncio
async def test_add_and_get_chore():
    await database.add_chore(123, "alice", "washed dishes")
    chores = await database.get_chores(123)

    assert len(chores) == 1
    assert chores[0]["chore_text"] == "washed dishes"

@pytest.mark.asyncio
async def test_get_chores_respects_limit():
    for i in range(25):
        await database.add_chore(123, "alice", f"chore {i}")

    chores = await database.get_chores(123, limit=10)
    assert len(chores) == 10

@pytest.mark.asyncio
async def test_clear_chores():
    await database.add_chore(123, "alice", "chore 1")
    await database.add_chore(123, "alice", "chore 2")

    count = await database.clear_chores(123)
    assert count == 2

    chores = await database.get_chores(123)
    assert len(chores) == 0

@pytest.mark.asyncio
async def test_ban_and_unban():
    assert not await database.is_banned(999)
    await database.ban_user(999)
    assert await database.is_banned(999)
    await database.unban_user(999)
    assert not await database.is_banned(999)

@pytest.mark.asyncio
async def test_stats():
    await database.add_chore(1, "alice", "a")
    await database.add_chore(1, "alice", "b")
    await database.add_chore(2, "bob", "c")

    stats = await database.get_stats()
    assert stats["total_chores"] == 3
    assert stats["active_users"] == 2

@pytest.mark.asyncio
async def test_get_chores_since():
    import datetime
    from time import sleep

    # SQLite CURRENT_TIMESTAMP is UTC, so use UTC time for the cutoff
    await database.add_chore(1, "alice", "before")
    sleep(1.1)
    cutoff = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
    sleep(1.1)
    await database.add_chore(2, "bob", "after")

    since = await database.get_chores_since(cutoff)
    assert len(since) == 1
    assert since[0]["chore_text"] == "after"
    assert since[0]["username"] == "bob"
    assert since[0]["user_id"] == 2

    # With an earlier cutoff, both should appear
    since_early = await database.get_chores_since("2020-01-01 00:00:00")
    assert len(since_early) == 2

@pytest.mark.asyncio
async def test_get_chores_orders_desc():
    await database.add_chore(123, "alice", "first")
    await database.add_chore(123, "alice", "second")
    await database.add_chore(123, "alice", "third")

    chores = await database.get_chores(123)
    assert chores[0]["chore_text"] == "third"
    assert chores[1]["chore_text"] == "second"
    assert chores[2]["chore_text"] == "first"
