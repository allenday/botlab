import pytest
from unittest.mock import Mock, patch, AsyncMock
from botlab.bot import Bot
from botlab.xml_handler import AgentConfig, MomentumSequence
from botlab.message import Message

@pytest.fixture
def mock_config():
    """Create a mock configuration"""
    return AgentConfig(
        name="test_bot",
        type="filter",
        category="foundation",
        version="1.0",
        protocols=[{
            'id': 'test',
            'agent_definition': {
                'objectives': {
                    'primary': 'Test primary objective',
                    'secondary': ['Test secondary objective']
                },
                'style': {
                    'communication': 'Test communication',
                    'analysis': 'Test analysis'
                }
            }
        }],
        momentum_sequences=[
            MomentumSequence(
                id="init",
                type="initialization",
                protocol_ref="test",
                temperature=0.7,
                messages=[Message(
                    role="system",
                    content="Test message",
                    agent="system",
                    chat_id=0
                )]
            )
        ]
    )

@pytest.fixture
def bot(mock_config):
    """Create a bot instance with mocked dependencies"""
    with patch('botlab.bot.load_agent_config') as mock_load:
        mock_load.return_value = mock_config
        return Bot(
            config_path="test_config.xml",
            username="test_bot",
            allowed_topic=None  # Test without topic restriction
        )

def test_no_topic_restriction_if_none_set(bot):
    """Test that bot responds without topic restriction if none set"""
    msg = Message(
        content="@test_bot help",
        role="user",
        agent="testuser",
        chat_id=123,
        message_id=1
    )
    assert bot._should_respond(msg) == True

def test_handle_none_message(bot):
    """Test handling None message"""
    assert bot.handle_message(None) is None

def test_partial_mention_match(bot):
    """Test that partial username matches don't trigger response"""
    msg = Message(
        content="@test_bot_extra help",
        role="user",
        agent="testuser",
        chat_id=123,
        message_id=1
    )
    assert bot._should_respond(msg) == False

def test_mention_with_punctuation(bot):
    """Test mention with punctuation"""
    msg = Message(
        content="Hey @test_bot! How are you?",
        role="user",
        agent="testuser",
        chat_id=123,
        message_id=1
    )
    assert bot._should_respond(msg) == True

def test_env_fallback_values(monkeypatch):
    """Test environment variable fallbacks"""
    import os
    
    # Mock environment variables
    monkeypatch.setenv('BOT_USERNAME', 'env_bot')
    monkeypatch.setenv('BOT_ALLOWED_TOPIC', 'env_topic')
    
    with patch('botlab.bot.load_agent_config') as mock_load:
        mock_load.return_value = AgentConfig(
            name="test_bot",
            type="filter",
            category="foundation",
            version="1.0",
            protocols=[],
            momentum_sequences=[]
        )
        
        # Create bot without explicit username/topic
        bot = Bot(config_path="test_config.xml")
        
        # Should use environment values
        assert bot.username == 'env_bot'
        assert bot.allowed_topic == 'env_topic' 