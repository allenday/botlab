import logging
import xml.etree.ElementTree as ET
from lxml import etree
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class Message:
    role_type: str
    content: str
    position: int

@dataclass
class MomentumSequence:
    id: str
    type: str
    temperature: float
    messages: List[Message]

@dataclass
class ServiceConfig:
    provider: str
    model: str
    api_version: str

@dataclass
class AgentConfig:
    name: str
    type: str
    category: str
    version: str
    response_interval: float
    response_interval_unit: str
    service: ServiceConfig
    momentum_sequences: List[MomentumSequence]

    def get_momentum_sequence(self, sequence_id: str) -> List[Message]:
        """Get messages from a specific momentum sequence"""
        for sequence in self.momentum_sequences:
            if sequence.id == sequence_id:
                return sequence.messages
        return []

def validate_xml_dtd(xml_path: str) -> bool:
    """Validate XML against its DTD."""
    try:
        logger.info(f"Validating XML: {xml_path}")
        
        # Get project root directory
        project_root = Path(__file__).parent.parent.parent
        
        # Create a validating parser with custom entity resolver
        class DTDResolver(etree.Resolver):
            def resolve(self, system_url, public_id, context):
                if system_url.endswith('agent.dtd'):
                    dtd_path = project_root / 'config' / 'dtd' / 'agent.dtd'
                    return self.resolve_filename(str(dtd_path), context)
                return None
                
        parser = etree.XMLParser(
            dtd_validation=True,
            load_dtd=True,
            resolve_entities=True,
            attribute_defaults=True
        )
        parser.resolvers.add(DTDResolver())
        
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
            
            if role is None or content is None:
                logger.error("Message missing required role or content")
                return None
                
            position = int(msg_elem.get('position', '0'))
            
            logger.debug(f"Adding message at position {position}: role={role.get('type')}")
            logger.debug(f"Message content length: {len(content.text or '')}")
            messages.append(Message(
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

def load_agent_config(file_path: str) -> Optional[AgentConfig]:
    """Load agent configuration from XML file"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Parse metadata
        metadata = root.find('metadata')
        name = metadata.find('name').text
        type_elem = metadata.find('type')
        type_str = type_elem.text
        category = type_elem.get('category')
        version = metadata.find('version').text
        
        # Parse timing
        timing = metadata.find('timing')
        response_interval = float(timing.find('response_interval').text)
        response_interval_unit = timing.find('response_interval').get('unit')
        
        # Parse service config
        service_elem = metadata.find('service')
        service = ServiceConfig(
            provider=service_elem.find('provider').text,
            model=service_elem.find('model').text,
            api_version=service_elem.find('api_version').text
        )
        
        # Parse momentum sequences
        momentum_sequences = []
        momentum = root.find('momentum')
        if momentum is not None:
            for seq in momentum.findall('sequence'):
                messages = []
                for msg in seq.findall('message'):
                    messages.append(Message(
                        role_type=msg.find('role').get('type'),
                        content=msg.find('content').text,
                        position=int(msg.get('position'))
                    ))
                
                momentum_sequences.append(MomentumSequence(
                    id=seq.get('id'),
                    type=seq.get('type'),
                    temperature=float(seq.get('temperature')),
                    messages=messages
                ))
        
        return AgentConfig(
            name=name,
            type=type_str,
            category=category,
            version=version,
            response_interval=response_interval,
            response_interval_unit=response_interval_unit,
            service=service,
            momentum_sequences=momentum_sequences
        )
        
    except Exception as e:
        logger.error(f"Failed to load agent config from {file_path}: {str(e)}")
        return None