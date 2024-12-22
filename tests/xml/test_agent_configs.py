import pytest
from pathlib import Path
import tempfile
from botlab.xml_handler import validate_xml_dtd, load_agent_config, parse_momentum_sequence
import xml.etree.ElementTree as ET

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROJECT_ROOT = Path(__file__).parent.parent.parent
DTD_PATH = PROJECT_ROOT / "config/dtd/agent.dtd"

def test_valid_agent_config():
    config_path = FIXTURES_DIR / "valid_agent.xml"
    assert validate_xml_dtd(config_path)
    config = load_agent_config(config_path)
    assert config is not None
    assert config.name == "TestAgent"
    assert config.type == "inhibitor"
    assert config.category == "foundation"
    assert config.version == "1.0"
    assert config.response_interval == 30
    assert config.response_interval_unit == "seconds"
    assert len(config.momentum_sequences) == 2

def test_invalid_agent_config():
    config_path = FIXTURES_DIR / "invalid_agent.xml"
    assert not validate_xml_dtd(config_path)
    config = load_agent_config(config_path)
    assert config is None

def test_momentum_sequence_parsing():
    tree = ET.parse(FIXTURES_DIR / "valid_agent.xml")
    root = tree.getroot()
    sequences = root.findall(".//sequence")
    
    init_seq = parse_momentum_sequence(sequences[0])
    assert init_seq is not None
    assert init_seq.id == "init"
    assert init_seq.type == "initialization"
    assert init_seq.temperature == 0.1
    assert len(init_seq.messages) == 1
    assert init_seq.messages[0].role_type == "system"
    assert init_seq.messages[0].content == "Initialize test sequence"
    assert init_seq.messages[0].position == 0

def test_missing_required_elements():
    config_path = FIXTURES_DIR / "invalid_agent.xml"
    config = load_agent_config(config_path)
    assert config is None

def test_sequence_message_ordering():
    """Test that messages are correctly ordered by position"""
    xml_str = f"""<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE agent SYSTEM "{DTD_PATH}">
    <sequence id="test" type="system" temperature="0.1">
        <message position="2">
            <role type="system">Second</role>
            <content>Message 2</content>
        </message>
        <message position="1">
            <role type="system">First</role>
            <content>Message 1</content>
        </message>
    </sequence>
    """
    sequence = parse_momentum_sequence(ET.fromstring(xml_str))
    assert sequence.messages[0].content == "Message 1"
    assert sequence.messages[1].content == "Message 2"

def test_dtd_validation_errors():
    """Test specific DTD validation error cases"""
    dtd_path = str(PROJECT_ROOT / "config/dtd/agent.dtd")
    
    invalid_cases = [
        # Case 1: Missing required elements
        (f"""<?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE agent SYSTEM "{dtd_path}">
            <agent dtd_version="1.0">
                <metadata>
                    <name>Test</name>
                    <type category="foundation">test</type>
                    <version>1.0</version>
                    <timing>
                        <response_interval unit="seconds">30</response_interval>
                    </timing>
                    <service>
                        <provider>test</provider>
                        <model>test</model>
                        <api_version>test</api_version>
                    </service>
                </metadata>
                <momentum>
                    <sequence id="init" type="initialization" temperature="0.7">
                        <message position="0">
                            <role type="system">Test</role>
                            <content>Test</content>
                        </message>
                    </sequence>
                </momentum>
            </agent>""", "Missing required elements"),
            
        # Case 2: Invalid category value
        (f"""<?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE agent SYSTEM "{dtd_path}">
            <agent dtd_version="1.0">
                <metadata>
                    <name>Test</name>
                    <type category="invalid">test</type>
                    <version>1.0</version>
                    <timing>
                        <response_interval unit="seconds">30</response_interval>
                    </timing>
                    <service>
                        <provider>test</provider>
                        <model>test</model>
                        <api_version>test</api_version>
                    </service>
                </metadata>
                <objectives>
                    <primary>Test</primary>
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
                    <sequence id="init" type="initialization" temperature="0.7">
                        <message position="0">
                            <role type="system">Test</role>
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
            </agent>""", "Invalid category value")
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml') as tmp:
        for xml_str, case in invalid_cases:
            tmp.write(xml_str)
            tmp.flush()
            assert not validate_xml_dtd(tmp.name), f"Should fail: {case}"