import pytest
from pathlib import Path
from botlab.xml_handler import load_agent_config, validate_xml_dtd

CONFIG_DIR = Path(__file__).parent.parent.parent / "config/agents"

def test_inhibitor_config():
    """Test loading inhibitor agent config"""
    xml_path = Path(__file__).parent.parent.parent / "config/agents/inhibitor.xml"
    result, errors = validate_xml_dtd(str(xml_path))
    assert result is True, f"Validation failed with errors: {errors}"

def test_all_agent_configs():
    """Test that all agent config files are valid"""
    config_dir = Path(__file__).parent.parent.parent / "config" / "agents"
    for config_file in config_dir.glob("*.xml"):
        result, errors = validate_xml_dtd(str(config_file))
        assert result is True, f"Invalid config {config_file.name}: {errors}"
        
        # Then load the config
        config = load_agent_config(str(config_file))
        assert config is not None, f"Failed to load {config_file.name}"
        assert config.type is not None
        assert config.category is not None
        assert len(config.momentum_sequences) > 0 