"""Pytest configuration and shared fixtures."""
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

# Configure pytest for async tests
@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx client for testing HTTP calls."""
    client = AsyncMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.is_closed = False
    return client


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing handlers."""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def sample_user_settings():
    """Create sample user settings for testing."""
    from app.models.schemas import UserSettings
    return UserSettings(
        assistant_name="Galatea",
        assistant_nickname="Gala",
        selected_model="ministral-3:latest",
        selected_voice="af_heart",
        tts_provider="kokoro",
        user_location="Redlands, California",
        vision_enabled=False
    )


@pytest.fixture
def sample_conversation_state():
    """Create a sample conversation state for testing."""
    from app.handlers.base import ConversationState
    return ConversationState()
