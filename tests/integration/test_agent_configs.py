import pytest
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from botlab.xml_handler import load_agent_config

CONFIG_DIR = Path(__file__).parent.parent.parent / "config/agents"

def test_inhibitor_config():
    """Test loading and validating inhibitor config"""
    config_path = CONFIG_DIR / "inhibitor.xml"
    config = load_agent_config(str(config_path))
    assert config is not None
    assert config.type == "Response Gatekeeper"
    assert config.category == "filter"
    assert len(config.momentum_sequences) > 0
    
    # Test required sequences
    sequence_ids = {seq.id for seq in config.momentum_sequences}
    assert "init" in sequence_ids, "Missing initialization sequence"

def test_all_agent_configs():
    """Test loading all agent configs"""
    for config_file in CONFIG_DIR.glob("*.xml"):
        config = load_agent_config(str(config_file))
        assert config is not None, f"Failed to load {config_file.name}"
        assert config.type is not None
        assert config.category is not None
        assert len(config.momentum_sequences) > 0

# Similar tests for other agent types... 