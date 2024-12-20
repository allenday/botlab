import pytest
import shutil
from xml_handler import validate_xml_dtd, parse_momentum_sequence, load_agent_config
import xml.etree.ElementTree as ET
from pathlib import Path

@pytest.fixture
def test_dtd(tmp_path):
    # Create dtd directory in temp path
    dtd_dir = tmp_path / "dtd"
    dtd_dir.mkdir()
    
    # Write test DTD
    dtd_content = '''
    <!-- Agent Configuration DTD v1.0 -->
    <!ELEMENT agent (metadata, communication, behavior, constraints, momentum)>
    <!ATTLIST agent dtd_version CDATA #REQUIRED>
    <!ELEMENT metadata (name, type, version, timing)>
    <!ELEMENT name (#PCDATA)>
    <!ELEMENT type (#PCDATA)>
    <!ATTLIST type category CDATA #REQUIRED>
    <!ELEMENT version (#PCDATA)>
    <!ELEMENT timing (response_interval)>
    <!ELEMENT response_interval (#PCDATA)>
    <!ATTLIST response_interval unit (seconds|milliseconds) "seconds">
    <!ELEMENT communication (input, output)>
    <!ELEMENT input (format)>
    <!ELEMENT output (format)>
    <!ELEMENT format (#PCDATA)>
    <!ELEMENT behavior (core_function, methodology)>
    <!ELEMENT core_function (#PCDATA)>
    <!ELEMENT methodology (step+)>
    <!ELEMENT step (#PCDATA)>
    <!ELEMENT constraints (excluded_topics?)>
    <!ELEMENT excluded_topics (topic*)>
    <!ELEMENT topic (#PCDATA)>
    <!ELEMENT momentum (sequence+)>
    <!ELEMENT sequence (message+)>
    <!ATTLIST sequence id CDATA #REQUIRED type CDATA #REQUIRED temperature CDATA "0.1">
    <!ELEMENT message (role, content)>
    <!ATTLIST message position CDATA #REQUIRED>
    <!ELEMENT role (#PCDATA)>
    <!ATTLIST role type (system|user|assistant) #REQUIRED>
    <!ELEMENT content (#PCDATA)>
    '''
    dtd_path = dtd_dir / "agent.dtd"
    dtd_path.write_text(dtd_content)
    return dtd_dir

@pytest.fixture
def sample_xml(test_dtd):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE agent SYSTEM "dtd/agent.dtd">
<agent dtd_version="1.0">
    <metadata>
        <name>TestBot</name>
        <type category="test">Test Assistant</type>
        <version>1.0</version>
        <timing>
            <response_interval unit="seconds">30</response_interval>
        </timing>
    </metadata>
    <communication>
        <input><format>Test Format</format></input>
        <output><format>Test Format</format></output>
    </communication>
    <behavior>
        <core_function>test function</core_function>
        <methodology><step>test step</step></methodology>
    </behavior>
    <constraints>
        <excluded_topics><topic>test topic</topic></excluded_topics>
    </constraints>
    <momentum>
        <sequence id="test" type="test" temperature="0.5">
            <message position="1">
                <role type="system">Test Role</role>
                <content>Test Content</content>
            </message>
        </sequence>
    </momentum>
</agent>'''

@pytest.fixture
def sample_sequence():
    element = ET.fromstring("""
    <sequence id="test" type="test" temperature="0.5">
        <message position="1">
            <role type="system">Test Role</role>
            <content>Test Content</content>
        </message>
    </sequence>
    """)
    return element

def test_validate_xml_dtd(tmp_path, test_dtd, sample_xml):
    # Write sample XML to temporary file
    xml_path = tmp_path / "test_agent.xml"
    xml_path.write_text(sample_xml)
    
    # Test validation
    assert validate_xml_dtd(str(xml_path)) == True

def test_parse_momentum_sequence(sample_sequence):
    sequence = parse_momentum_sequence(sample_sequence)
    assert sequence is not None
    assert sequence.id == "test"
    assert sequence.type == "test"
    assert sequence.temperature == 0.5
    assert len(sequence.messages) == 1
    assert sequence.messages[0].role_type == "system"
    assert sequence.messages[0].content == "Test Content"
    assert sequence.messages[0].position == 1

def test_load_agent_config(tmp_path, test_dtd, sample_xml):
    # Write sample XML to temporary file
    xml_path = tmp_path / "test_agent.xml"
    xml_path.write_text(sample_xml)
    
    # Test config loading
    config = load_agent_config(str(xml_path))
    assert config is not None
    assert config.name == "TestBot"
    assert config.type == "Test Assistant"
    assert config.category == "test"
    assert config.version == "1.0"
    assert config.response_interval == 30.0
    assert config.response_interval_unit == "seconds"
    assert len(config.momentum_sequences) == 1