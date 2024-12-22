import pytest
import shutil
from botlab.xml_handler import validate_xml_dtd, parse_momentum_sequence, load_agent_config
import xml.etree.ElementTree as ET
from pathlib import Path
import tempfile

@pytest.fixture
def sample_xml():
    return '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE agent SYSTEM "../../../config/dtd/agent.dtd">
<agent dtd_version="1.0">
    <metadata>
        <name>TestBot</name>
        <type category="foundation">Test Assistant</type>
        <version>1.0</version>
        <timing>
            <response_interval unit="seconds">30</response_interval>
        </timing>
        <service>
            <provider>anthropic</provider>
            <model>claude-3-opus-20240229</model>
            <api_version>2024-02-15</api_version>
        </service>
    </metadata>
    <objectives>
        <primary>Test objective</primary>
        <secondary><objective>Test</objective></secondary>
        <metrics><metric>Test</metric></metrics>
    </objectives>
    <styles>
        <communication_style><aspect>Test</aspect></communication_style>
        <analytical_style><aspect>Test</aspect></analytical_style>
    </styles>
    <constraints>
        <operational><constraint>Test</constraint></operational>
        <technical><constraint>Test</constraint></technical>
    </constraints>
    <counterparty_perception>
        <assumptions><assumption>Test</assumption></assumptions>
        <adaptation><strategy>Test</strategy></adaptation>
    </counterparty_perception>
    <momentum>
        <sequence id="init" type="initialization" temperature="0.5">
            <message position="1">
                <role type="system"/>
                <content>Test Content</content>
            </message>
        </sequence>
    </momentum>
    <communication>
        <input>
            <message_format><schema>Test</schema></message_format>
            <analysis_points><point>Test</point></analysis_points>
            <history>
                <lru_cache>
                    <threads max_count="100">
                        <context length="10"/>
                    </threads>
                </lru_cache>
            </history>
        </input>
        <output><format>Test</format></output>
    </communication>
    <behavior>
        <core_function>Test</core_function>
        <methodology><step>Test</step></methodology>
    </behavior>
</agent>'''

@pytest.fixture
def sample_sequence():
    element = ET.fromstring("""
    <sequence id="init" type="initialization" temperature="0.5">
        <message position="1">
            <role type="system"/>
            <content>Test Content</content>
        </message>
    </sequence>
    """)
    return element

def test_validate_xml_dtd(tmp_path, sample_xml):
    # Write sample XML to temporary file
    xml_path = tmp_path / "test_agent.xml"
    xml_path.write_text(sample_xml)
    
    # Test validation
    assert validate_xml_dtd(str(xml_path)) == True

def test_parse_momentum_sequence(sample_sequence):
    sequence = parse_momentum_sequence(sample_sequence)
    assert sequence is not None
    assert sequence.id == "init"
    assert sequence.type == "initialization"
    assert sequence.temperature == 0.5
    assert len(sequence.messages) == 1
    assert sequence.messages[0].role_type == "system"
    assert sequence.messages[0].content == "Test Content"
    assert sequence.messages[0].position == 1

def test_load_agent_config():
    """Test loading agent configuration"""
    xml_str = """<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE agent SYSTEM "../../../config/dtd/agent.dtd">
    <agent dtd_version="1.0">
        <metadata>
            <name>TestAgent</name>
            <type category="foundation">inhibitor</type>
            <version>1.0</version>
            <timing>
                <response_interval unit="seconds">30</response_interval>
            </timing>
            <service>
                <provider>anthropic</provider>
                <model>claude-3-opus-20240229</model>
                <api_version>2024-02-15</api_version>
            </service>
        </metadata>
        <objectives>
            <primary>Test objective</primary>
            <secondary><objective>Test</objective></secondary>
            <metrics><metric>Test</metric></metrics>
        </objectives>
        <styles>
            <communication_style><aspect>Test</aspect></communication_style>
            <analytical_style><aspect>Test</aspect></analytical_style>
        </styles>
        <constraints>
            <operational><constraint>Test</constraint></operational>
            <technical><constraint>Test</constraint></technical>
        </constraints>
        <counterparty_perception>
            <assumptions><assumption>Test</assumption></assumptions>
            <adaptation><strategy>Test</strategy></adaptation>
        </counterparty_perception>
        <momentum>
            <sequence id="init" type="initialization" temperature="0.1">
                <message position="0">
                    <role type="system"/>
                    <content>Test</content>
                </message>
            </sequence>
        </momentum>
        <communication>
            <input>
                <message_format><schema>Test</schema></message_format>
                <analysis_points><point>Test</point></analysis_points>
            </input>
            <output><format>Test</format></output>
        </communication>
        <behavior>
            <core_function>Test</core_function>
            <methodology><step>Test</step></methodology>
        </behavior>
    </agent>
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml') as tmp:
        tmp.write(xml_str)
        tmp.flush()
        
        config = load_agent_config(tmp.name)
        assert config is not None
        assert config.name == "TestAgent"
        assert config.type == "inhibitor"
        assert config.category == "foundation"
        assert config.version == "1.0"
        assert config.response_interval == 30
        assert config.response_interval_unit == "seconds"
        assert len(config.momentum_sequences) == 1
        assert config.service.provider == "anthropic"
        assert config.service.model == "claude-3-opus-20240229"
        assert config.service.api_version == "2024-02-15"