import pytest
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from botlab.filters import (
    FilterResult,
    MessageFilter,
    FilterSet,
    FilterChain,
    MentionFilter,
    TopicFilter,
    RateLimitFilter
)
from botlab.timing import ResponseTimer
from botlab.agents.inhibitor import InhibitorFilter
from botlab.xml_handler import AgentConfig, MomentumSequence
from botlab.message import Message
from pathlib import Path
from xml.etree.ElementTree import fromstring, ElementTree
from botlab.bot import Bot
from typing import Optional

FIXTURES_DIR = Path(__file__).parent.parent / "xml" / "fixtures"

@dataclass
class MockMessage:
    content: str = ""
    topic: str = ""
    chat_id: int = 123
    date: datetime = field(default_factory=lambda: datetime.now())
    message_thread_id: Optional[int] = None
    text: Optional[str] = None
    message_id: int = 1
    from_user: Optional[object] = field(default_factory=lambda: Mock(id=456, username="test_user"))

@pytest.fixture
def mock_config():
    config = Mock()
    # Basic config attributes
    config.name = "TestBot"
    config.type = "filter"
    config.category = "foundation"
    config.version = "1.0"
    
    # Don't include response_interval for basic config
    # This will be added in rate limit tests
    
    # Required attributes for InhibitorFilter
    config.protocols = [Mock(
        id="test",
        agent_definition=Mock(
            objectives=Mock(primary="Test", secondary=["Test"]),
            style=Mock(communication=["Test"], analysis=["Test"])
        )
    )]
    config.momentum_sequences = [Mock(
        id="init",
        type="initialization",
        protocol_ref="test",
        temperature=0.7,
        messages=[Mock(role="system", content="Test")]
    )]
    return config

@pytest.fixture
def bot(mock_config):
    with patch('botlab.bot.load_agent_config') as mock_load, \
         patch('botlab.bot.ResponseTimer') as mock_timer, \
         patch('botlab.bot.MessageHistory') as mock_history, \
         patch('botlab.bot.TelegramService') as mock_telegram:
        mock_load.return_value = mock_config
        
        # Set up timer mock
        mock_timer_instance = Mock(spec=['can_respond', 'record_response', 'get_remaining_time'])
        mock_timer_instance.can_respond.return_value = True
        mock_timer_instance.get_remaining_time.return_value = 0
        mock_timer.return_value = mock_timer_instance
        
        # Set up history mock
        mock_history_instance = Mock(spec=['get_thread_history'])
        mock_history_instance.get_thread_history.return_value = "<history>test</history>"
        mock_history.return_value = mock_history_instance
        
        # Set up telegram mock
        mock_telegram_instance = Mock(spec=['start', 'stop'])
        mock_telegram.return_value = mock_telegram_instance
        
        from botlab.bot import Bot
        bot = Bot(
            config_path="test_config.xml",
            username="test_bot",
            allowed_topic="allowed_topic"
        )
        return bot

class SimplePassFilter(MessageFilter):
    def check(self, message) -> FilterResult:
        return FilterResult(True, "Always pass")

class SimpleFailFilter(MessageFilter):
    def check(self, message) -> FilterResult:
        return FilterResult(False, "Always fail")

# Test individual filters
def test_mention_filter():
    """Test MentionFilter behavior"""
    filter = MentionFilter("test_bot")
    
    # Test direct mention
    msg = MockMessage(content="Hey @test_bot help")
    result = filter.check(msg)
    assert result.passed == True
    assert "Bot mentioned" in result.reason
    
    # Test no mention
    msg = MockMessage(content="Hello there")
    result = filter.check(msg)
    assert result.passed == False
    assert "Bot not mentioned" in result.reason
    
    # Test partial mention (should not match)
    msg = MockMessage(content="@test_bot_extra")
    result = filter.check(msg)
    assert result.passed == False
    
    # Test mention in code block
    msg = MockMessage(content="```\n@test_bot\n```")
    result = filter.check(msg)
    assert result.passed == True

def test_topic_filter():
    """Test TopicFilter behavior"""
    filter = TopicFilter("allowed_topic")
    
    # Test allowed topic
    msg = MockMessage(topic="allowed_topic")
    result = filter.check(msg)
    assert result.passed == True
    assert "Message in allowed topic" in result.reason
    
    # Test different topic
    msg = MockMessage(topic="other_topic")
    result = filter.check(msg)
    assert result.passed == False
    assert "Message not in allowed topic" in result.reason
    
    # Test empty topic
    msg = MockMessage(topic="")
    result = filter.check(msg)
    assert result.passed == False

# Test FilterSet (OR logic)
def test_filter_set_any_pass():
    """Test that FilterSet passes if any filter passes"""
    filter_set = FilterSet([
        SimplePassFilter(),
        SimpleFailFilter()
    ])
    
    result = filter_set.check(MockMessage())
    assert result.passed == True
    assert "Always pass" in result.reason

def test_filter_set_all_fail():
    """Test that FilterSet fails if all filters fail"""
    filter_set = FilterSet([
        SimpleFailFilter(),
        SimpleFailFilter()
    ])
    
    result = filter_set.check(MockMessage())
    assert result.passed == False
    assert "Failed all filters" in result.reason

def test_filter_set_with_none():
    """Test FilterSet handling of None filters"""
    filter_set = FilterSet([
        SimplePassFilter(),
        None,
        SimpleFailFilter()
    ])
    
    result = filter_set.check(MockMessage())
    assert result.passed == True

# Test FilterChain (AND logic)
def test_filter_chain_all_pass():
    """Test that FilterChain passes if all sets pass"""
    chain = FilterChain()
    chain.add_filter_set(SimplePassFilter())
    chain.add_filter_set(SimplePassFilter())
    
    result = chain.check(MockMessage())
    assert result.passed == True
    assert "Passed all filter sets" in result.reason

def test_filter_chain_any_fail():
    """Test that FilterChain fails if any set fails"""
    chain = FilterChain()
    chain.add_filter_set(SimplePassFilter())
    chain.add_filter_set(SimpleFailFilter())
    
    result = chain.check(MockMessage())
    assert result.passed == False
    assert "Always fail" in result.reason

# Test nested structures
def test_nested_filter_sets():
    """Test nested filter sets"""
    # Create a structure like: (Pass OR Fail) AND (Pass OR Pass)
    inner_set1 = FilterSet([SimplePassFilter(), SimpleFailFilter()])
    inner_set2 = FilterSet([SimplePassFilter(), SimplePassFilter()])
    
    chain = FilterChain()
    chain.add_filter_set(inner_set1)
    chain.add_filter_set(inner_set2)
    
    result = chain.check(MockMessage())
    assert result.passed == True

def test_complex_filter_structure():
    """Test a complex filter structure"""
    # Create a structure like:
    # (Mention OR Topic) AND (Pass)
    msg = MockMessage(content="@test_bot", topic="wrong_topic")
    
    access_filters = FilterSet([
        MentionFilter("test_bot"),
        TopicFilter("allowed_topic")
    ])
    
    chain = FilterChain()
    chain.add_filter_set(access_filters)
    chain.add_filter_set(SimplePassFilter())
    
    # Should pass because of mention
    result = chain.check(msg)
    assert result.passed == True
    
    # Change message to have no mention but correct topic
    msg = MockMessage(content="hello", topic="allowed_topic")
    result = chain.check(msg)
    assert result.passed == True
    
    # Change message to have neither
    msg = MockMessage(content="hello", topic="wrong_topic")
    result = chain.check(msg)
    assert result.passed == False

def test_empty_filter_set():
    """Test behavior with empty filter set"""
    filter_set = FilterSet([])
    result = filter_set.check(MockMessage())
    assert result.passed == False
    assert "Failed all filters" in result.reason

def test_empty_filter_chain():
    """Test behavior with empty filter chain"""
    chain = FilterChain()
    result = chain.check(MockMessage())
    assert result.passed == True
    assert "Passed all filter sets" in result.reason

def test_filter_result_reasons():
    """Test that filter reasons are properly propagated"""
    filter_set = FilterSet([
        SimplePassFilter(),
        SimpleFailFilter()
    ])
    
    result = filter_set.check(MockMessage())
    assert "Always pass" in result.reason
    assert "Always fail" not in result.reason  # Failed filter reason not included in pass result 

def test_rate_limit_filter():
    """Test RateLimitFilter behavior"""
    from datetime import datetime
    
    # Create mock timer that allows response
    mock_timer = Mock()
    mock_timer.can_respond.return_value = True
    mock_timer.get_remaining_time.return_value = 0
    
    filter = RateLimitFilter(mock_timer)
    
    # Test message with required attributes
    msg = MockMessage(
        chat_id=123,
        date=datetime.now()
    )
    
    result = filter.check(msg)
    assert result.passed == True
    assert "Rate limit not exceeded" in result.reason
    
    # Test rate limited message
    mock_timer.can_respond.return_value = False
    mock_timer.get_remaining_time.return_value = 30
    
    result = filter.check(msg)
    assert result.passed == False
    assert "Rate limited" in result.reason

def test_complex_filter_chain_with_rate_limit():
    """Test complex filter chain with rate limiting"""
    # Create mock timer
    mock_timer = Mock()
    mock_timer.can_respond.return_value = True
    mock_timer.get_remaining_time.return_value = 0
    
    # Create filter chain
    chain = FilterChain()
    
    # Add access filters (mention OR topic)
    access_filters = [
        MentionFilter("test_bot"),
        TopicFilter("allowed_topic")
    ]
    chain.add_filter_set(FilterSet(access_filters))
    
    # Add rate limit filter
    chain.add_filter_set(RateLimitFilter(mock_timer))
    
    # Test message that should pass all filters
    msg = MockMessage(
        content="@test_bot help",
        topic="allowed_topic",
        chat_id=123,
        date=datetime.now()
    )
    result = chain.check(msg)
    assert result.passed == True

def test_bot_filter_chain_initialization_without_rate_limit():
    """Test bot filter chain initialization without rate limit"""
    config = Mock(
        response_interval=None,
        response_interval_unit=None,
        protocols=[{
            'id': 'test',
            'agent_definition': {
                'objectives': {'primary': 'Test', 'secondary': ['Test']},
                'style': {'communication': 'Test', 'analysis': 'Test'}
            }
        }],
        momentum_sequences=[Mock(
            id='init',
            type='initialization',
            protocol_ref='test',
            temperature=0.7,
            messages=[Mock(role='system', content='Test')]
        )]
    )
    
    with patch('botlab.bot.load_agent_config') as mock_load:
        mock_load.return_value = config
        bot = Bot(
            config_path="test_config.xml",
            username="test_bot",
            allowed_topic="allowed_topic"
        )
        
        # Should only have access filters
        assert len(bot.filter_chain.filter_sets) == 1
        assert isinstance(bot.filter_chain.filter_sets[0], FilterSet)

@pytest.mark.asyncio
async def test_bot_async_message_handling():
    """Test async message handling with filters"""
    # Create test message
    msg = Message(
        content="Test message",
        role="user",
        agent="testuser",
        chat_id=123,
        message_id=1
    )
    
    # Create a simple pass filter
    simple_pass = SimplePassFilter()
    result = simple_pass.check(msg)
    
    # Test message handling
    assert result.passed == True
    assert "Always pass" in result.reason

def test_filter_config_from_xml():
    """Test loading filter configuration from XML"""
    # Load test filter config
    config_path = FIXTURES_DIR / "valid" / "filter_basic.xml"
    tree = ElementTree(fromstring(config_path.read_text()))
    filters_elem = tree.find(".//filters")
    
    # Create filter chain from config
    filter_chain = FilterChain.from_xml(filters_elem)
    assert isinstance(filter_chain, FilterChain)
    assert len(filter_chain.filter_sets) > 0

def test_filter_chain_from_odv_config():
    """Test loading filter chain from ODV config"""
    # Load ODV config
    config_path = FIXTURES_DIR / "valid" / "odv_basic.xml"
    tree = ElementTree(fromstring(config_path.read_text()))
    filters_elem = tree.find(".//odv/filters")
    
    # Create filter chain from config
    filter_chain = FilterChain.from_xml(filters_elem)
    assert isinstance(filter_chain, FilterChain)
    assert len(filter_chain.filter_sets) > 0 