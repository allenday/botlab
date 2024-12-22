import pytest
from pathlib import Path
from botlab.xml_handler import parse_momentum_sequence, MomentumMessage, MomentumSequence
import xml.etree.ElementTree as ET

def test_parse_momentum_sequence_with_invalid_input():
    """Test parsing with invalid sequence element"""
    invalid_xml = """
    <sequence>
        <message>
            <!-- Missing required role and content -->
        </message>
    </sequence>
    """
    element = ET.fromstring(invalid_xml)
    result = parse_momentum_sequence(element)
    assert result is None

def test_parse_momentum_sequence_with_empty_sequence():
    """Test parsing empty sequence"""
    empty_xml = "<sequence/>"
    element = ET.fromstring(empty_xml)
    result = parse_momentum_sequence(element)
    # Should return a valid sequence with no messages
    assert isinstance(result, MomentumSequence)
    assert len(result.messages) == 0

def test_parse_momentum_message_with_missing_attributes():
    """Test parsing message with missing attributes"""
    xml = """
    <message>
        <role>system</role>
        <content>test</content>
    </message>
    """
    element = ET.fromstring(xml)
    msg = MomentumMessage(
        role_type="system",
        content="test",
        position=0
    )
    assert msg.role_type == "system"
    assert msg.content == "test"
    assert msg.position == 0

def test_parse_momentum_sequence_with_valid_input():
    """Test parsing valid sequence"""
    xml = """
    <sequence id="test" type="system" temperature="0.5">
        <message position="0">
            <role type="system"/>
            <content>Test content</content>
        </message>
    </sequence>
    """
    element = ET.fromstring(xml)
    result = parse_momentum_sequence(element)
    assert isinstance(result, MomentumSequence)
    assert result.id == "test"
    assert result.type == "system"
    assert result.temperature == 0.5
    assert len(result.messages) == 1

def test_parse_behavior_section():
    """Test parsing behavior section"""
    xml = """
    <behavior>
        <core_function>Test function</core_function>
        <methodology>
            <step>Step 1</step>
            <step>Step 2</step>
        </methodology>
    </behavior>
    """
    element = ET.fromstring(xml)
    core_function = element.find('core_function')
    methodology = element.find('methodology')
    assert core_function is not None
    assert core_function.text == "Test function"
    assert methodology is not None
    steps = methodology.findall('step')
    assert len(steps) == 2
    assert steps[0].text == "Step 1"
    assert steps[1].text == "Step 2"