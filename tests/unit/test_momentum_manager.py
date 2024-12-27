import pytest
from unittest.mock import Mock, AsyncMock, ANY as mock_ANY
from botlab.momentum import MomentumManager
from botlab.message import Message
from botlab.xml_handler import Protocol, AgentDefinition, MomentumSequence
import asyncio

@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service"""
    service = Mock()
    service.call_api = AsyncMock(return_value="Test response")
    return service

@pytest.fixture
def mock_config():
    """Create a mock configuration with proper protocol structure"""
    config = Mock()
    
    # Create a test protocol
    test_protocol = Protocol(
        id="test_proto",
        agent_definition={
            'objectives': {
                'primary': 'Test objective',
                'secondary': ['Test secondary']
            },
            'style': {
                'communication': 'Test communication',
                'analysis': 'Test analysis'
            }
        }
    )
    
    # Create a test sequence
    test_sequence = MomentumSequence(
        id="init",
        type="initialization",
        protocol_ref="test_proto",
        temperature=0.7,
        messages=[
            Message(
                role="system",
                content="Test message",
                agent="system",
                chat_id=0,
                message_id=1
            )
        ]
    )
    
    # Set up the mock config
    config.protocols = [test_protocol]
    config.momentum_sequences = [test_sequence]
    return config

@pytest.fixture
def momentum_manager(mock_llm_service, mock_config):
    """Create a MomentumManager instance for testing"""
    return MomentumManager(llm_service=mock_llm_service, config=mock_config)

def test_momentum_initialization(momentum_manager):
    """Test that MomentumManager initializes correctly"""
    assert momentum_manager is not None
    assert len(momentum_manager.config.momentum_sequences) > 0
    assert any(seq.id == "init" for seq in momentum_manager.config.momentum_sequences)

def test_get_sequence(momentum_manager):
    """Test retrieving a specific sequence"""
    messages = momentum_manager._get_sequence("init")
    assert messages is not None
    assert len(messages) > 0
    assert messages[0].role == "system"
    assert messages[0].content == "Test message"
    assert messages[0].agent == "system"
    assert messages[0].chat_id == 0

def test_get_nonexistent_sequence(momentum_manager):
    """Test retrieving a sequence that doesn't exist"""
    messages = momentum_manager._get_sequence("nonexistent")
    assert messages is None

def test_get_sequence_messages(momentum_manager):
    """Test getting messages from a sequence"""
    messages = momentum_manager._get_sequence("init")
    assert len(messages) > 0
    assert isinstance(messages[0], Message)
    assert messages[0].role == "system"
    assert messages[0].agent == "system"
    assert messages[0].chat_id == 0

@pytest.mark.asyncio
async def test_initialize_chat(momentum_manager):
    """Test chat initialization"""
    result = await momentum_manager.initialize(123)
    assert result is True
    assert 123 in momentum_manager.initialized_chats

@pytest.mark.asyncio
async def test_initialize_chat_failure(momentum_manager):
    """Test chat initialization failure"""
    # Set llm_service to None to simulate failure
    momentum_manager.llm_service = None
    result = await momentum_manager.initialize(123)
    assert result is False
    assert 123 not in momentum_manager.initialized_chats

@pytest.mark.asyncio
async def test_recover_chat(momentum_manager):
    """Test chat recovery"""
    result = await momentum_manager.recover(123)
    assert result is True

@pytest.mark.asyncio
async def test_recover_chat_failure(momentum_manager):
    """Test chat recovery failure"""
    # Set llm_service to None to simulate failure
    momentum_manager.llm_service = None
    result = await momentum_manager.recover(123)
    assert result is False

@pytest.mark.asyncio
async def test_get_response_with_history(momentum_manager):
    """Test getting response with history"""
    history_xml = "<history><message>test</message></history>"
    response = await momentum_manager.get_response(history_xml)
    assert response == "Test response"

@pytest.mark.asyncio
async def test_get_response_failure(momentum_manager, mock_llm_service):
    """Test getting response failure"""
    mock_llm_service.call_api.side_effect = Exception("API error")
    response = await momentum_manager.get_response("<history></history>")
    assert response is None

@pytest.mark.asyncio
async def test_get_response_no_init_sequence(momentum_manager):
    """Test getting response with missing init sequence"""
    momentum_manager.config.momentum_sequences = []  # Remove all sequences
    momentum_manager.llm_service = None  # Ensure service failure
    response = await momentum_manager.get_response("<history></history>")
    assert response is None 

@pytest.mark.asyncio
async def test_sequence_execution_order(momentum_manager):
    """Test that sequence messages are executed in correct order"""
    # Add a test sequence with multiple messages
    test_sequence = MomentumSequence(
        id="test_seq",
        type="test",
        protocol_ref="test_proto",
        temperature=0.7,
        messages=[
            Message(role="system", content="First message", agent="system", chat_id=0, message_id=1),
            Message(role="assistant", content="Second message", agent="assistant", chat_id=0, message_id=2),
            Message(role="system", content="Third message", agent="system", chat_id=0, message_id=3)
        ]
    )
    momentum_manager.config.momentum_sequences.append(test_sequence)
    
    messages = momentum_manager._get_sequence("test_seq")
    assert len(messages) == 3
    assert messages[0].message_id == 1
    assert messages[0].content == "First message"
    assert messages[1].message_id == 2
    assert messages[1].content == "Second message"
    assert messages[2].message_id == 3
    assert messages[2].content == "Third message"

@pytest.mark.asyncio
async def test_sequence_protocol_validation(momentum_manager):
    """Test that sequences validate protocol references"""
    # Test with invalid protocol reference
    invalid_sequence = MomentumSequence(
        id="invalid_seq",
        type="test",
        protocol_ref="nonexistent_proto",
        temperature=0.7,
        messages=[Message(role="system", content="Test", agent="system", chat_id=0, message_id=1)]
    )
    momentum_manager.config.momentum_sequences.append(invalid_sequence)
    
    messages = momentum_manager._get_sequence("invalid_seq")
    assert messages is None

@pytest.mark.asyncio
async def test_sequence_state_transitions(momentum_manager):
    """Test state transitions during sequence execution"""
    # Initialize chat
    chat_id = 456
    assert await momentum_manager.initialize(chat_id) is True
    assert chat_id in momentum_manager.initialized_chats
    
    # Test recovery state
    assert await momentum_manager.recover(chat_id) is True
    assert chat_id not in momentum_manager.initialized_chats  # Should be removed during recovery
    assert await momentum_manager.initialize(chat_id) is True  # Should be re-initialized
    assert chat_id in momentum_manager.initialized_chats

@pytest.mark.asyncio
async def test_sequence_temperature_handling(momentum_manager):
    """Test that sequence temperature settings are respected"""
    test_sequence = MomentumSequence(
        id="temp_test",
        type="test",
        protocol_ref="test_proto",
        temperature=0.3,  # Lower temperature for more focused responses
        messages=[Message(role="system", content="Test", agent="system", chat_id=0, message_id=1)]
    )
    momentum_manager.config.momentum_sequences.append(test_sequence)
    
    messages = momentum_manager._get_sequence("temp_test")
    assert messages is not None
    assert len(messages) == 1
    # Temperature should be preserved in sequence metadata
    assert test_sequence.temperature == 0.3

@pytest.mark.asyncio
async def test_sequence_concurrent_execution(momentum_manager):
    """Test handling of concurrent sequence executions"""
    chat_ids = [1, 2, 3]
    
    # Initialize multiple chats concurrently
    results = await asyncio.gather(*[
        momentum_manager.initialize(chat_id) 
        for chat_id in chat_ids
    ])
    
    assert all(results)  # All initializations should succeed
    assert all(chat_id in momentum_manager.initialized_chats for chat_id in chat_ids)
    
    # Test concurrent recovery
    results = await asyncio.gather(*[
        momentum_manager.recover(chat_id)
        for chat_id in chat_ids
    ])
    
    assert all(results)  # All recoveries should succeed
    assert all(chat_id not in momentum_manager.initialized_chats for chat_id in chat_ids) 

@pytest.mark.asyncio
async def test_temperature_effects(momentum_manager, mock_llm_service):
    """Test that temperature settings affect response generation"""
    # Test default temperature
    history_xml = "<history><message>test</message></history>"
    await momentum_manager.get_response(history_xml)
    
    # Verify default temperature was used
    mock_llm_service.call_api.assert_called_with(
        messages=mock_ANY,
        temperature=0.7  # Default temperature
    )
    
    # Test custom temperature via sequence
    test_sequence = MomentumSequence(
        id="temp_test",
        type="test",
        protocol_ref="test_proto",
        temperature=0.2,  # Lower temperature for more focused responses
        messages=[Message(role="system", content="Test", agent="system", chat_id=0, message_id=1)]
    )
    momentum_manager.config.momentum_sequences = [test_sequence]
    
    await momentum_manager.get_response(history_xml)
    
    # Verify custom temperature was used
    mock_llm_service.call_api.assert_called_with(
        messages=mock_ANY,
        temperature=0.2  # Custom temperature from sequence
    )
    
    # Test temperature bounds
    test_sequence.temperature = 1.5  # Above max
    await momentum_manager.get_response(history_xml)
    mock_llm_service.call_api.assert_called_with(
        messages=mock_ANY,
        temperature=1.0  # Should be capped at max
    )
    
    test_sequence.temperature = -0.5  # Below min
    await momentum_manager.get_response(history_xml)
    mock_llm_service.call_api.assert_called_with(
        messages=mock_ANY,
        temperature=0.0  # Should be capped at min
    )

@pytest.mark.asyncio
async def test_temperature_validation(momentum_manager):
    """Test temperature validation in sequences"""
    # Test invalid temperature type
    with pytest.raises(ValueError):
        MomentumSequence(
            id="invalid_temp",
            type="test",
            protocol_ref="test_proto",
            temperature="invalid",  # Invalid type
            messages=[Message(role="system", content="Test", agent="system", chat_id=0, message_id=1)]
        )
    
    # Test missing temperature (should use default)
    sequence = MomentumSequence(
        id="no_temp",
        type="test",
        protocol_ref="test_proto",
        messages=[Message(role="system", content="Test", agent="system", chat_id=0, message_id=1)]
    )
    assert sequence.temperature == 0.7  # Default temperature
 