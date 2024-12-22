import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime
from botlab.bot import Bot
from telegram import Update, Message, User, Chat
import aiohttp
from pathlib import Path
from botlab.history import MessageHistory
from botlab.timing import ResponseTimer
from botlab.services.anthropic import AnthropicService
from botlab.momentum import MomentumManager
from botlab.handlers import MessageHandler

class MockResponse:
    def __init__(self, status, content):
        self.status = status
        self._content = content
        
    async def text(self):
        return "Error"
    
    @property
    def content(self):
        return self._content
    
    async def __aenter__(self):
        print("MockResponse.__aenter__")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print("MockResponse.__aexit__")
        pass

class MockStreamReader:
    def __init__(self, responses):
        self.responses = responses
        self.index = 0
    
    def __aiter__(self):
        print("MockStreamReader.__aiter__")
        return self
        
    async def __anext__(self):
        print(f"MockStreamReader.__anext__ (index: {self.index})")
        if self.index >= len(self.responses):
            raise StopAsyncIteration
        response = self.responses[self.index]
        self.index += 1
        return response.encode('utf-8')

class MockClientSession:
    def __init__(self, mock_response):
        self.mock_response = mock_response
        
    def post(self, *args, **kwargs):
        print("MockClientSession.post")
        return self.mock_response
    
    async def __aenter__(self):
        print("MockClientSession.__aenter__")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print("MockClientSession.__aexit__")
        pass

@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    message = MagicMock(spec=Message)
    user = MagicMock(spec=User)
    chat = MagicMock(spec=Chat)
    
    # Configure mocks
    user.first_name = "Test User"
    chat.id = 123
    message.from_user = user
    message.chat = chat
    message.text = "Hello bot"
    message.date = datetime.now()
    update.message = message
    
    return update

@pytest.fixture
def mock_context():
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.username = "test_bot"
    return context

@pytest.fixture
def mock_env_vars():
    with patch.dict('os.environ', {
        'TELEGRAM_TOKEN': 'test_token',
        'ANTHROPIC_API_KEY': 'test_key'
    }):
        yield

@pytest.fixture
def mock_config():
    config = MagicMock()
    config.name = "TestBot"
    config.type = "Test Assistant"
    config.response_interval = 1.0
    config.momentum_sequences = []
    return config

@pytest.fixture
def bot():
    config_path = Path(__file__).parent.parent.parent / "config/agents/claude.xml"
    bot = Bot(config_path)
    # Initialize required components that were commented out
    bot.history = MessageHistory()
    bot.timer = ResponseTimer(
        bot.config.response_interval,
        datetime.now()
    )
    bot.llm_service = AnthropicService(
        bot.claude_api_key,
        bot.api_version,
        bot.model
    )
    bot.momentum = MomentumManager(bot.config, bot.llm_service)
    bot.message_handler = MessageHandler(
        bot.history,
        bot.momentum,
        bot.llm_service,
        bot.agent_username,
        bot.allowed_topic
    )
    return bot

@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context, mock_env_vars, mock_config):
    with patch('botlab.bot.load_agent_config', return_value=mock_config):
        bot = Bot()
        mock_update.message.reply_text = AsyncMock()
        
        await bot.start(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "Hello!" in call_args
        assert "TestBot" in call_args

@pytest.mark.asyncio
async def test_handle_message(bot):
    update = MagicMock(spec=Update)
    message = MagicMock(spec=Message)
    message.text = "test message"
    message.chat_id = 123
    message.date = datetime.now()
    update.message = message
    update.message.reply_text = AsyncMock()
    
    # Mock the message handler
    bot.message_handler.process_message = AsyncMock(return_value="Test response")
    
    await bot.handle_message(update, None)
    bot.message_handler.process_message.assert_called_once_with(update, bot.agents)

@pytest.mark.asyncio
async def test_rate_limiting(bot):
    update = MagicMock(spec=Update)
    message = MagicMock(spec=Message)
    message.text = "test message"
    message.chat_id = 123
    message.date = datetime.now()
    update.message = message
    
    # Mock the pipeline processing
    bot.process_message_pipeline = AsyncMock(return_value={'code': '200'})
    
    # First message should work
    result = await bot.should_respond(123, update)
    assert result is True
    
    # Second immediate message should be rate limited
    result = await bot.should_respond(123, update)
    assert result is False