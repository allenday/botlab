import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from botlab.bot import Bot
from botlab.xml_handler import load_agent_config
from datetime import datetime, timezone

@pytest.fixture
def mock_env(monkeypatch):
    """Set up test environment variables"""
    monkeypatch.setenv('RESPONSE_INTERVAL_SECONDS', '1')
    monkeypatch.setenv('TELEGRAM_TOKEN', 'test_token')
    monkeypatch.setenv('AGENT_USERNAME', 'test_bot')

@pytest.fixture
def mock_telegram():
    return MagicMock()

@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    update.message = MagicMock()
    update.message.text = "Hello bot!"
    update.message.chat_id = 123
    update.message.message_thread_id = None
    return update

@pytest.fixture
def mock_context():
    return MagicMock(spec=ContextTypes.DEFAULT_TYPE)

def test_handle_message(mock_env, mock_telegram, mock_update, mock_context):
    """Test basic message handling"""
    bot = Bot()
    bot.telegram = mock_telegram
    
    # Load configs
    config_dir = Path(__file__).parent.parent.parent / "config/agents"
    
    # First load inhibitor
    inhibitor_config = load_agent_config(str(config_dir / "inhibitor.xml"))
    assert inhibitor_config is not None
    bot.add_agent(inhibitor_config)
    
    # Then load others
    for config_file in config_dir.glob("*.xml"):
        if config_file.name != "inhibitor.xml":
            config = load_agent_config(str(config_file))
            if config:
                bot.add_agent(config)
    
    assert len(bot.agents) > 0
    assert any(agent.config.category == "filter" for agent in bot.agents)
    
    # Test message handling
    response = bot.handle_message(mock_update, mock_context)
    assert response is not None

@pytest.mark.asyncio
async def test_rate_limiting():
    """Test that rate limiting works"""
    # Use the actual inhibitor config
    config_path = Path(__file__).parent.parent.parent / "config/agents/inhibitor.xml"
    bot = Bot(config_path=str(config_path))
    
    # Create test update
    update = Mock()
    update.message = Mock()
    update.message.chat_id = 123
    update.message.date = datetime.now(timezone.utc)
    update.message.text = "test"
    
    # First message should be allowed
    assert await bot.should_respond(update.message.chat_id, update)
    
    # Second immediate message should be rate limited
    assert not await bot.should_respond(update.message.chat_id, update)