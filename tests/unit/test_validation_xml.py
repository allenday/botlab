import pytest
from pathlib import Path
import tempfile
from botlab.xml_handler import validate_xml_dtd

FIXTURES_DIR = Path(__file__).parent.parent / "xml" / "fixtures"

def test_validate_xml_dtd_with_invalid_path():
    """Test validation with nonexistent file"""
    result, errors = validate_xml_dtd('nonexistent.xml')
    assert not result
    assert "No such file or directory: 'nonexistent.xml'" in errors[0]

def test_validate_xml_dtd_with_malformed_xml():
    """Test validation with malformed XML"""
    malformed_xml = FIXTURES_DIR / "invalid" / "malformed.xml"
    result, errors = validate_xml_dtd(str(malformed_xml))
    assert not result
    assert "mismatched tag" in errors[0] 