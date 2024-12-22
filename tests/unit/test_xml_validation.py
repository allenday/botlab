import pytest
from pathlib import Path
import tempfile
from botlab.xml_handler import validate_xml_dtd

def test_validate_xml_dtd_with_invalid_path():
    """Test validation with non-existent file"""
    assert not validate_xml_dtd("nonexistent.xml")

def test_validate_xml_dtd_with_malformed_xml():
    """Test validation with malformed XML"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml') as tmp:
        tmp.write("<?xml version='1.0'?><not>valid</xml>")
        tmp.flush()
        assert not validate_xml_dtd(tmp.name) 