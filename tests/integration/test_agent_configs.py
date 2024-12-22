import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from botlab.agents.inhibitor import InhibitorFilter
from botlab.xml_handler import load_agent_config

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"

@pytest.mark.asyncio
async def test_inhibitor_config():
    """Test that inhibitor config works with actual agent"""
    config_path = CONFIG_DIR / "agents/inhibitor.xml"
    config = load_agent_config(config_path)
    
    # Mock the API service
    class MockService:
        def __init__(self):
            self.model = "test-model"
            self.api_version = "test-version"
            
        async def call_api(self, *args, **kwargs):
            return '<context><management><message code="200">OK</message></management></context>'
    
    config.service = MockService()
    
    class _TestInhibitor(InhibitorFilter):
        def get_metadata(self) -> dict:
            return {
                'name': self.config.name,
                'type': self.config.type,
                'version': self.config.version
            }
    
    agent = _TestInhibitor(config, speaker_prompt="Test system prompt")
    result = await agent.process_message({
        'text': 'test message',
        'thread_id': '123'
    })
    assert result is not None
    assert 'code' in result

# Similar tests for other agent types... 