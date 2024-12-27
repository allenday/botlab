import pytest
from pathlib import Path
from botlab.xml_handler import validate_xml_dtd

FIXTURES_DIR = Path(__file__).parent.parent / "xml" / "fixtures"

def test_validate_xml_dtd():
    """Test XML validation against DTD"""
    valid_xml = FIXTURES_DIR / "valid" / "test_agent.xml"
    result, errors = validate_xml_dtd(str(valid_xml))
    assert result, f"Validation failed with errors: {errors}"

def test_validate_xml_dtd_invalid():
    """Test XML validation fails with invalid XML"""
    invalid_xml = FIXTURES_DIR / "invalid" / "missing_metadata.xml"
    result, errors = validate_xml_dtd(str(invalid_xml))
    assert not result, "Validation should fail for invalid XML"
    assert "Missing required element <metadata>" in errors

def test_all_agent_configs_valid():
    """Test all agent config files in config/agents are valid"""
    config_dir = Path(__file__).parent.parent.parent / "config" / "agents"
    for xml_file in config_dir.glob("*.xml"):
        result, errors = validate_xml_dtd(str(xml_file))
        assert result, f"Validation failed for {xml_file.name} with errors: {errors}"

def test_all_fixture_xmls_validate_correctly():
    """Test that valid fixtures pass and invalid fixtures fail validation"""
    # Valid fixtures should pass
    valid_dir = FIXTURES_DIR / "valid"
    for xml_file in valid_dir.glob("*.xml"):
        result, errors = validate_xml_dtd(str(xml_file))
        assert result, f"Valid fixture {xml_file.name} failed validation: {errors}"

    # Invalid fixtures should fail
    invalid_dir = FIXTURES_DIR / "invalid"
    for xml_file in invalid_dir.glob("*.xml"):
        result, errors = validate_xml_dtd(str(xml_file))
        assert not result, f"Invalid fixture {xml_file.name} unexpectedly passed validation"