import logging
import xml.etree.ElementTree as ET
from lxml import etree
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import time

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
        logger.info(f"Validating XML: {xml_path}")
        
        # Create a validating parser
        parser = etree.XMLParser(
            dtd_validation=True,
            load_dtd=True,
            no_network=False,  # Allow loading external DTDs
            resolve_entities=True,
            attribute_defaults=True
        )
        
        # Parse and validate
        try:
            etree.parse(xml_path, parser)
            return True
        except etree.DocumentInvalid as e:
            logger.error(f"DTD validation failed: {str(e)}")
            return False
        except etree.XMLSyntaxError as e:
            logger.error(f"XML syntax error: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error during XML validation: {str(e)}")
        return False

def parse_momentum_sequence(sequence_element: ET.Element) -> Optional[MomentumSequence]:
    """Parse a momentum sequence from XML."""
    try:
        logger.debug(f"Parsing momentum sequence: {sequence_element.get('id')}")
        logger.debug(f"Sequence type: {sequence_element.get('type')}")
        logger.debug(f"Temperature: {sequence_element.get('temperature', '0.1')}")
        
        sequence_id = sequence_element.get('id')
        sequence_type = sequence_element.get('type')
        temperature = float(sequence_element.get('temperature', '0.1'))
        
        messages = []
        for msg_elem in sequence_element.findall('message'):
            role = msg_elem.find('role')
            content = msg_elem.find('content')
            position = int(msg_elem.get('position', '0'))
            
            if role is not None and content is not None:
                logger.debug(f"Adding message at position {position}: role={role.get('type')}")
                logger.debug(f"Message content length: {len(content.text or '')}")
                messages.append(MomentumMessage(
                    role_type=role.get('type', 'system'),
                    content=content.text or '',
                    position=position
                ))
        
        logger.debug(f"Parsed {len(messages)} messages in sequence")
        logger.debug("Sorting messages by position")
        return MomentumSequence(
            id=sequence_id,
            type=sequence_type,
            temperature=temperature,
            messages=sorted(messages, key=lambda x: x.position)
        )
    except Exception as e:
        logger.error(f"Error parsing momentum sequence: {str(e)}")
        logger.error(f"Failed sequence element: {ET.tostring(sequence_element)[:200]}")
        return None

def load_agent_config(xml_path: str) -> Optional[AgentConfig]:
    """Load agent configuration from XML file."""
    try:
        logger.info(f"Loading agent config: {xml_path}")
        
        if not validate_xml_dtd(xml_path):
            logger.error("XML validation failed")
            return None
            
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Parse metadata
        metadata = root.find('metadata')
        if metadata is None:
            logger.error("Missing metadata section")
            raise ValueError("Missing metadata section")
            
        name = metadata.find('name')
        type_elem = metadata.find('type')
        version = metadata.find('version')
        timing = metadata.find('timing')
        
        if None in (name, type_elem, version, timing):
            logger.error("Missing required metadata elements")
            raise ValueError("Missing required metadata elements")
        
        # Parse timing
        response_interval = timing.find('response_interval')
        if response_interval is None:
            logger.error("Missing response_interval")
            raise ValueError("Missing response_interval")
        
        interval_value = float(response_interval.text or '0')
        interval_unit = response_interval.get('unit', 'seconds')
        logger.debug(f"Response interval: {interval_value} {interval_unit}")
        
        # Parse momentum sequences
        momentum = root.find('momentum')
        sequences = []
        if momentum is not None:
            logger.debug("Parsing momentum sequences")
            for seq_elem in momentum.findall('sequence'):
                sequence = parse_momentum_sequence(seq_elem)
                if sequence:
                    sequences.append(sequence)
            logger.debug(f"Parsed {len(sequences)} momentum sequences")
        
        logger.info(f"Successfully loaded config for {name.text}")
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
        logger.error(f"Failed to load config: {str(e)}")
        return None