import pytest
from pathlib import Path
from botlab.xml_handler import validate_xml_dtd, load_agent_config

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config/agents"

def test_all_agent_configs_valid():
    """Test that all agent configs in config/agents are valid"""
    for config_file in CONFIG_DIR.glob("*.xml"):
        assert validate_xml_dtd(str(config_file)), f"Invalid config: {config_file.name}"
        # Also check that we can load it
        config = load_agent_config(str(config_file))
        assert config is not None, f"Failed to load config: {config_file.name}"

def test_agent_config_compatibility():
    """Test that agent configs are compatible with each other"""
    configs = []
    for config_file in CONFIG_DIR.glob("*.xml"):
        config = load_agent_config(str(config_file))
        if config is None:
            pytest.skip(f"Skipping compatibility test - failed to load {config_file.name}")
        configs.append(config)
    
    if not configs:
        pytest.skip("No configs found to test compatibility")
        
    # Check that all configs have compatible timing
    base_interval = configs[0].response_interval
    base_unit = configs[0].response_interval_unit
    for config in configs[1:]:
        assert config.response_interval_unit == base_unit, "Incompatible timing units"
        assert config.response_interval >= base_interval, "Response interval too short"