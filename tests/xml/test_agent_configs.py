import pytest
from pathlib import Path
from xml.etree import ElementTree as ET
from botlab.xml_handler import parse_momentum_sequence

FIXTURES_DIR = Path(__file__).parent / "fixtures"

def test_momentum_sequence_parsing():
    """Test parsing momentum sequences"""
    xml_path = FIXTURES_DIR / "valid" / "single_message_sequence.xml"
    sequence_elem = ET.parse(str(xml_path)).getroot().find(".//sequence")
    sequence = parse_momentum_sequence(sequence_elem)
    
    assert sequence.id == "test"
    assert sequence.type == "init"
    assert sequence.protocol_ref == "test"
    assert sequence.temperature == 0.7
    assert len(sequence.messages) == 1
    assert sequence.messages[0].role == "system"
    assert sequence.messages[0].content == "Test message"

def test_sequence_message_ordering():
    """Test that message order is preserved"""
    xml_path = FIXTURES_DIR / "valid" / "ordered_messages_sequence.xml"
    sequence_elem = ET.parse(str(xml_path)).getroot().find(".//sequence")
    sequence = parse_momentum_sequence(sequence_elem)
    
    assert len(sequence.messages) == 3
    assert sequence.messages[0].content == "First message"
    assert sequence.messages[1].content == "Second message"
    assert sequence.messages[2].content == "Third message"