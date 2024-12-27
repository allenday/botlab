import pytest
from unittest.mock import Mock, AsyncMock, ANY as mock_ANY
from botlab.momentum import MomentumManager
from botlab.message import Message
from botlab.xml_handler import Protocol, AgentDefinition, MomentumSequence

@pytest.fixture
def mock_llm_service():
    service = Mock()
    service.call_api = AsyncMock()
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
    
    config.protocols = [test_protocol]
    config.momentum_sequences = []
    return config

@pytest.fixture
def momentum_manager(mock_llm_service, mock_config):
    return MomentumManager(llm_service=mock_llm_service, config=mock_config)

@pytest.mark.asyncio
async def test_temperature_effects(momentum_manager, mock_llm_service):
    """Test temperature impact on response generation"""
    history_xml = "<history><message role='user'>Hello</message></history>"
    
    # Test with different temperatures
    temperatures = [0.1, 0.7, 1.0]
    responses = []
    
    for temp in temperatures:
        # Create a sequence with the current temperature
        test_sequence = MomentumSequence(
            id="test_seq",
            type="test",
            protocol_ref="test_proto",
            temperature=temp,
            messages=[Message(
                role="system",
                content="Test message",
                agent="system",
                chat_id=0,
                message_id=1
            )]
        )
        
        # Update the config with the new sequence
        momentum_manager.config.momentum_sequences = [test_sequence]
        
        # Configure mock to return different responses based on temperature
        mock_llm_service.call_api = AsyncMock(
            return_value=f"Response at temperature {temp}"
        )
        
        response = await momentum_manager.get_response(history_xml)
        responses.append(response)
        
        # Verify temperature was passed correctly to LLM service
        mock_llm_service.call_api.assert_called_with(
            system_msg=mock_ANY,  # System message includes protocol content
            messages=mock_ANY,  # Message content is handled by momentum manager
            temperature=temp
        )
    
    # Verify each temperature produced a different response
    assert len(set(responses)) == len(temperatures), "Different temperatures should produce different responses"