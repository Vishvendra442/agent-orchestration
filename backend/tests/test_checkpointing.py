import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class MockAsyncCursor:
    def __init__(self, items):
        self._items = items

    def sort(self, *args, **kwargs):
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._items:
            raise StopAsyncIteration
        return self._items.pop(0)


@pytest.mark.asyncio
async def test_checkpointer_list_empty():
    mock_cursor = MockAsyncCursor([])

    mock_col = MagicMock()
    mock_col.find.return_value = mock_cursor

    with patch("app.runtime.checkpointer.MongoDBCheckpointer._col", new_callable=lambda: property(lambda self: mock_col)):
        from app.runtime.checkpointer import MongoDBCheckpointer
        cp = MongoDBCheckpointer()
        result = await cp.list_checkpoints("nonexistent-thread")
        assert result == []


@pytest.mark.asyncio
async def test_checkpointer_get_none():
    mock_col = MagicMock()
    mock_col.find_one = AsyncMock(return_value=None)

    with patch("app.runtime.checkpointer.MongoDBCheckpointer._col", new_callable=lambda: property(lambda self: mock_col)):
        from app.runtime.checkpointer import MongoDBCheckpointer
        cp = MongoDBCheckpointer()
        result = await cp.get_checkpoint("thread-1", "checkpoint-1")
        assert result is None


@pytest.mark.asyncio
async def test_checkpointer_delete():
    mock_col = MagicMock()
    mock_result = MagicMock()
    mock_result.deleted_count = 3
    mock_col.delete_many = AsyncMock(return_value=mock_result)

    with patch("app.runtime.checkpointer.MongoDBCheckpointer._col", new_callable=lambda: property(lambda self: mock_col)):
        from app.runtime.checkpointer import MongoDBCheckpointer
        cp = MongoDBCheckpointer()
        count = await cp.delete_checkpoints("thread-1")
        assert count == 3
