import logging
import xml.etree.ElementTree as ET
from lxml import etree
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class MomentumMessage:
    role_type: str
    content: str
    position: int

@dataclass
class MomentumSequence:
    id: str
    type: str
    temperature: float
    messages: List[MomentumMessage]

@dataclass
class AgentConfig:
    name: str
    type: str
    category: str
    version: str
    response_interval: float
    response_interval_unit: str
    momentum_sequences: List[MomentumSequence]

def validate_xml_dtd(xml_path: str) -> bool:
    """Validate XML against its DTD."""
    try:
        xml_dir = Path(xml_path).parent
        parser = etree.XMLParser(load_dtd=True)
        etree.parse(xml_path, parser)
        return True
    except Exception as e:
        logger.error(f"XML validation error: {str(e)}")
        return False

def parse_momentum_sequence(sequence_element: ET.Element) -> Optional[MomentumSequence]:
    """Parse a momentum sequence from XML."""
    try:
        sequence_id = sequence_element.get('id')
        sequence_type = sequence_element.get('type')
        temperature = float(sequence_element.get('temperature', '0.1'))
        
        messages = []
        for msg_elem in sequence_element.findall('message'):
            role = msg_elem.find('role')
            content = msg_elem.find('content')
            position = int(msg_elem.get('position', '0'))
            
            if role is not None and content is not None:
                messages.append(MomentumMessage(
                    role_type=role.get('type', 'system'),
                    content=content.text or '',
                    position=position
                ))
        
        return MomentumSequence(
            id=sequence_id,
            type=sequence_type,
            temperature=temperature,
            messages=sorted(messages, key=lambda x: x.position)
        )
    except Exception as e:
        logger.error(f"Error parsing momentum sequence: {str(e)}")
        return None

def load_agent_config(xml_path: str) -> Optional[AgentConfig]:
    """Load agent configuration from XML file."""
    try:
        # Validate XML against DTD
        if not validate_xml_dtd(xml_path):
            return None
        
        # Parse XML
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Parse metadata
        metadata = root.find('metadata')
        if metadata is None:
            raise ValueError("Missing metadata section")
        
        name = metadata.find('name')
        type_elem = metadata.find('type')
        version = metadata.find('version')
        timing = metadata.find('timing')
        
        if None in (name, type_elem, version, timing):
            raise ValueError("Missing required metadata elements")
        
        # Parse timing
        response_interval = timing.find('response_interval')
        if response_interval is None:
            raise ValueError("Missing response_interval")
        
        interval_value = float(response_interval.text or '0')
        interval_unit = response_interval.get('unit', 'seconds')
        
        # Parse momentum sequences
        momentum = root.find('momentum')
        sequences = []
        if momentum is not None:
            for seq_elem in momentum.findall('sequence'):
                sequence = parse_momentum_sequence(seq_elem)
                if sequence:
                    sequences.append(sequence)
        
        return AgentConfig(
            name=name.text or '',
            type=type_elem.text or '',
            category=type_elem.get('category', ''),
            version=version.text or '',
            response_interval=interval_value,
            response_interval_unit=interval_unit,
            momentum_sequences=sequences
        )
    except Exception as e:
        logger.error(f"Error loading agent config: {str(e)}")
        return None