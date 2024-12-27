import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from botlab.momentum import MomentumManager
from botlab.xml_handler import load_agent_config

@pytest.fixture
def mock_anthropic_service():
    """Create a mock Anthropic service that captures calls"""
    service = Mock()
    service.call_api = AsyncMock(return_value="Test response")
    return service

@pytest.mark.asyncio
async def test_protocol_content_included_in_anthropic_messages():
    """Test that protocol content from XML is included in messages sent to Anthropic"""
    # Load test agent config
    config_path = Path("tests/xml/fixtures/valid/agent_protocol.xml")
    config = load_agent_config(config_path)
    
    # Create mock service
    mock_service = Mock()
    mock_service.call_api = AsyncMock(return_value="Test response")
    
    # Create momentum manager
    manager = MomentumManager(mock_service, config)
    
    # Simulate a chat message
    history_xml = """
    <history>
        <message timestamp="123" role="user">Hello</message>
    </history>
    """
    
    # Get response which should include protocol content
    await manager.get_response(history_xml)
    
    # Verify the call to Anthropic included protocol content
    mock_service.call_api.assert_called_once()
    
    # Get the keyword arguments from the mock call
    call_kwargs = mock_service.call_api.call_args.kwargs
    
    # Check messages include protocol content
    messages = call_kwargs.get('messages', [])
    assert any('test_proto' in str(msg.content) for msg in messages)
    assert any('Test objective' in str(msg.content) for msg in messages)
    assert any('Test communication style' in str(msg.content) for msg in messages)

@pytest.mark.asyncio
async def test_sequence_chain():
    """Test full chain of sequence executions"""
    # Load test agent config with multiple sequences
    config_path = Path("tests/xml/fixtures/valid/sequence_chain.xml")
    config = load_agent_config(config_path)
    
    # Create mock service that tracks sequence progression
    mock_service = Mock()
    responses = {
        "init": "Initialization complete",
        "greeting": "Hello! How can I help?",
        "analysis": "Here's my analysis...",
        "conclusion": "To summarize..."
    }
    
    def get_response(messages, temperature):
        # Extract sequence content from messages to determine which sequence we're in
        history = messages[0].content
        if "Start initialization" in history and "Hello" not in history:
            return responses["init"]
        elif "Hello" in history and "Analyze" not in history:
            return responses["greeting"]
        elif "Analyze" in history and "Wrap" not in history:
            return responses["analysis"]
        elif "Wrap" in history:
            return responses["conclusion"]
        return "Default response"
    
    mock_service.call_api = AsyncMock(side_effect=get_response)
    
    # Create momentum manager
    manager = MomentumManager(mock_service, config)
    
    # Initialize chat
    chat_id = 123
    assert await manager.initialize(chat_id)
    assert chat_id in manager.initialized_chats
    
    # Test sequence chain execution
    sequences = [
        # Initial sequence
        """<history>
            <message role="system">Start initialization</message>
        </history>""",
        
        # Greeting sequence
        """<history>
            <message role="system">Start initialization</message>
            <message role="assistant">Initialization complete</message>
            <message role="user">Hello</message>
        </history>""",
        
        # Analysis sequence
        """<history>
            <message role="system">Start initialization</message>
            <message role="assistant">Initialization complete</message>
            <message role="user">Hello</message>
            <message role="assistant">Hello! How can I help?</message>
            <message role="user">Analyze this data</message>
        </history>""",
        
        # Conclusion sequence
        """<history>
            <message role="system">Start initialization</message>
            <message role="assistant">Initialization complete</message>
            <message role="user">Hello</message>
            <message role="assistant">Hello! How can I help?</message>
            <message role="user">Analyze this data</message>
            <message role="assistant">Here's my analysis...</message>
            <message role="user">Wrap it up</message>
        </history>"""
    ]
    
    expected_responses = [
        "Initialization complete",
        "Hello! How can I help?",
        "Here's my analysis...",
        "To summarize..."
    ]
    
    # Execute sequence chain
    for history_xml, expected_response in zip(sequences, expected_responses):
        response = await manager.get_response(history_xml)
        assert response == expected_response
        
        # Verify protocol content was included
        last_call = mock_service.call_api.call_args
        messages = last_call.kwargs['messages']
        assert any('Protocol' in str(msg.content) for msg in messages)
        assert any('Test objective' in str(msg.content) for msg in messages)
        assert any('Test communication style' in str(msg.content) for msg in messages)
        
        # Verify temperature was within bounds
        temperature = last_call.kwargs['temperature']
        assert 0.0 <= temperature <= 1.0
        
        # Verify sequence-specific temperature was used
        if "Start initialization" in history_xml and "Hello" not in history_xml:
            assert temperature == 0.7  # init sequence temperature
        elif "Hello" in history_xml and "Analyze" not in history_xml:
            assert temperature == 0.8  # greeting sequence temperature
        elif "Analyze" in history_xml and "Wrap" not in history_xml:
            assert temperature == 0.4  # analysis sequence temperature
        elif "Wrap" in history_xml:
            assert temperature == 0.6  # conclusion sequence temperature
    
    # Test error recovery
    assert await manager.recover(chat_id)
    assert chat_id not in manager.initialized_chats
    
    # Test re-initialization after recovery
    assert await manager.initialize(chat_id)
    assert chat_id in manager.initialized_chats
    
    # Verify final state
    response = await manager.get_response(sequences[-1])  # Use last sequence
    assert response == expected_responses[-1]  # Should get conclusion response 