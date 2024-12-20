import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from botlab.bot import Bot
from telegram import Update, Message, User, Chat
import aiohttp

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
async def test_handle_message(mock_update, mock_context, mock_env_vars, mock_config):
    # Create a mock response that simulates the Claude API streaming response
    stream_content = [
        'data: {"type":"content_block_delta","delta":{"text":"Test "}}\n',
        'data: {"type":"content_block_delta","delta":{"text":"response"}}\n',
        'data: {"type":"message_stop"}\n'
    ]
    mock_response = MockResponse(200, MockStreamReader(stream_content))
    mock_session = MockClientSession(mock_response)
    
    with patch('aiohttp.ClientSession', return_value=mock_session), \
         patch('botlab.bot.load_agent_config', return_value=mock_config), \
         patch('botlab.bot.Bot.should_respond', return_value=True):
        # Create bot instance
        bot = Bot()
        mock_update.message.reply_text = AsyncMock()
        
        # Test message handling
        await bot.handle_message(mock_update, mock_context)
        
        # Verify response was sent
        mock_update.message.reply_text.assert_called_once_with("Test response")

@pytest.mark.asyncio
async def test_rate_limiting(mock_update, mock_context, mock_env_vars):
    config = MagicMock()
    config.response_interval = 60.0  # 60 seconds
    config.momentum_sequences = []
    config.name = "TestBot"
    config.type = "Test Assistant"
    
    # Create a mock response that simulates the Claude API streaming response
    stream_content = [
        'data: {"type":"content_block_delta","delta":{"text":"Test response"}}\n',
        'data: {"type":"message_stop"}\n'
    ]
    mock_response = MockResponse(200, MockStreamReader(stream_content))
    mock_session = MockClientSession(mock_response)
    
    with patch('aiohttp.ClientSession', return_value=mock_session), \
         patch('botlab.bot.load_agent_config', return_value=config), \
         patch('botlab.bot.Bot.should_respond', side_effect=[True, False]):  # First True, then False
        bot = Bot()
        mock_update.message.reply_text = AsyncMock()
        
        # First message should go through
        await bot.handle_message(mock_update, mock_context)
        assert mock_update.message.reply_text.call_count == 1
        
        # Second message should be rate limited
        await bot.handle_message(mock_update, mock_context)
        assert mock_update.message.reply_text.call_count == 1  # Still 1, not 2