import pytest
from xml.etree.ElementTree import Element, SubElement
from botlab.xml_handler import parse_momentum_sequence, MomentumSequence
from botlab.message import Message
from pathlib import Path
import xml.etree.ElementTree as ET

def create_sequence_element(**kwargs):
    """Helper to create a sequence element for testing"""
    elem = Element('sequence')
    for key, value in kwargs.items():
        elem.set(key, str(value))
    return elem

def create_message_element(sequence_elem, role_type, content, position=1):
    """Helper to create a message element for testing"""
    msg = SubElement(sequence_elem, 'message')
    msg.set('position', str(position))
    
    role = SubElement(msg, 'role')
    role.set('type', role_type)
    
    content_elem = SubElement(msg, 'content')
    content_elem.text = content
    
    return msg

def test_parse_momentum_sequence_with_valid_input():
    """Test parsing a valid momentum sequence"""
    sequence = create_sequence_element(
        id="test_seq",
        type="initialization",
        protocol_ref="test_proto",
        temperature="0.7"
    )
    create_message_element(sequence, "system", "Test message")
    
    result = parse_momentum_sequence(sequence)
    
    assert result.id == "test_seq"
    assert result.type == "initialization"
    assert result.protocol_ref == "test_proto"
    assert result.temperature == 0.7
    assert len(result.messages) == 1
    assert result.messages[0].role == "system"
    assert result.messages[0].content == "Test message"
    assert result.messages[0].agent == "system"  # System agent for momentum sequences
    assert result.messages[0].chat_id == 0  # Special chat_id for system messages

def test_parse_momentum_sequence_with_invalid_input():
    """Test parsing an invalid momentum sequence"""
    sequence = create_sequence_element()  # Missing required attributes
    
    with pytest.raises(KeyError):
        parse_momentum_sequence(sequence)

def test_parse_momentum_sequence_with_empty_sequence():
    """Test parsing a sequence with no messages"""
    sequence = create_sequence_element(
        id="test_seq",
        type="initialization",
        protocol_ref="test_proto",
        temperature="0.7"
    )
    
    result = parse_momentum_sequence(sequence)
    assert len(result.messages) == 0

def test_parse_momentum_message_with_missing_attributes():
    """Test parsing a message with missing attributes"""
    sequence = create_sequence_element(
        id="test_seq",
        type="initialization",
        protocol_ref="test_proto",
        temperature="0.7"
    )
    message = SubElement(sequence, 'message')
    # No role attribute added
    
    result = parse_momentum_sequence(sequence)
    assert len(result.messages) == 0  # Message should be skipped due to missing role

def test_parse_momentum_sequence_with_multiple_messages():
    """Test parsing a sequence with multiple messages"""
    sequence = create_sequence_element(
        id="test_seq",
        type="initialization",
        protocol_ref="test_proto",
        temperature="0.7"
    )
    create_message_element(sequence, "system", "First message", 1)
    create_message_element(sequence, "assistant", "Second message", 2)
    create_message_element(sequence, "system", "Third message", 3)
    
    result = parse_momentum_sequence(sequence)
    
    assert len(result.messages) == 3
    assert result.messages[0].content == "First message"
    assert result.messages[1].content == "Second message"
    assert result.messages[2].content == "Third message"
    
    # Verify required fields
    for msg in result.messages:
        assert msg.agent == "system"  # System agent for momentum sequences
        assert msg.chat_id == 0  # Special chat_id for system messages
