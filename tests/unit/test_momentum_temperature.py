import pytest
from unittest.mock import Mock, AsyncMock, ANY as mock_ANY
from botlab.momentum import MomentumManager
from botlab.message import Message
from botlab.xml_handler import Protocol, AgentDefinition, MomentumSequence
from xml.etree.ElementTree import fromstring, ElementTree
from pathlib import Path

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
    # Load test momentum config
    config_path = Path(__file__).parent.parent / "xml" / "fixtures" / "valid" / "momentum_basic.xml"
    tree = ElementTree(fromstring(config_path.read_text()))
    momentum_elem = tree.find(".//momentum")
    
    # Test with different temperatures
    temperatures = [0.1, 0.7, 1.0]
    
    for temp in temperatures:
        # Create sequence with current temperature
        sequence = MomentumSequence(
            id=f"test_seq_{temp}",
            type="test",
            protocol_ref="test_proto",
            temperature=temp,
            messages=[
                Message(
                    role="user",
                    content="Hello",
                    agent="user",
                    chat_id=123,
                    message_id=1
                )
            ]
        )
        
        # Set up mock response
        mock_llm_service.call_api.return_value = f"Response with temperature {temp}"
        
        # Get response with current temperature
        response = await momentum_manager.get_response(sequence)
        
        # Verify temperature was passed correctly
        mock_llm_service.call_api.assert_called_with(
            messages=mock_ANY,
            temperature=temp
        )