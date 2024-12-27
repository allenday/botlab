import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from botlab.bot import Bot
from botlab.filters import FilterResult
from botlab.message import Message

@pytest.fixture
def test_bot():
    config_path = Path(__file__).parent.parent / "xml" / "fixtures" / "valid" / "test_agent.xml"
    
    with patch('botlab.bot.ResponseTimer') as mock_timer, \
         patch('botlab.bot.TelegramService') as mock_telegram, \
         patch('botlab.bot.FilterChain') as mock_filter_chain:
        
        # Set up timer mock
        mock_timer_instance = Mock()
        mock_timer_instance.can_respond.return_value = True
        mock_timer.return_value = mock_timer_instance
        
        # Set up telegram mock
        mock_telegram_instance = Mock()
        mock_telegram_instance.send_message = AsyncMock(return_value="Test response")
        mock_telegram.return_value = mock_telegram_instance
        
        # Set up filter chain mock
        mock_chain = Mock()
        mock_chain.check.return_value = FilterResult(True, "Test passed")
        mock_filter_chain.return_value = mock_chain
        
        bot = Bot(
            config_path=str(config_path),
            username="test_bot",
            allowed_topic="allowed_topic"
        )
        return bot

def test_handle_message(test_bot):
    """Test basic message handling"""
    bot = test_bot
    
    # Create proper internal Message
    message = Message(
        role="user",
        content="@test_bot help",
        agent="testuser",
        chat_id=123,
        message_id=789
    )
    
    # Test message handling
    response = bot.handle_message(message)
    assert response is not None, "Bot should return a response when message passes filters"