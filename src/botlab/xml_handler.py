import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
from .message import Message

logger = logging.getLogger(__name__)

@dataclass
class MomentumSequence:
    """Represents a momentum sequence in the agent configuration"""
    id: str
    type: str
    protocol_ref: str
    temperature: float = 0.7  # Default temperature
    messages: List[Message] = field(default_factory=list)

    def __post_init__(self):
        """Validate temperature after initialization"""
        if not isinstance(self.temperature, (int, float)):
            raise ValueError(f"Temperature must be a number, got {type(self.temperature)}")
        self.temperature = float(self.temperature)  # Convert to float if int
        self.temperature = max(0.0, min(1.0, self.temperature))  # Clamp to valid range

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access for backward compatibility"""
        return getattr(self, key)

@dataclass
class AgentConfig:
    name: str
    type: str
    category: str
    version: str
    response_interval: Optional[int] = None
    response_interval_unit: Optional[str] = None
    protocols: List[Dict] = field(default_factory=list)
    momentum_sequences: List[MomentumSequence] = field(default_factory=list)

@dataclass
class Protocol:
    """Represents a protocol in the agent configuration"""
    id: str
    agent_definition: Dict[str, Any]

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access for backward compatibility"""
        if key == 'id':
            return self.id
        elif key == 'agent_definition':
            return self.agent_definition
        raise KeyError(f"Invalid key: {key}")

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-like get method with default value"""
        try:
            return self[key]
        except KeyError:
            return default

@dataclass
class AgentDefinition:
    """Represents an agent definition in a protocol"""
    objectives: Dict[str, Any]
    style: Dict[str, Any]

def parse_momentum_sequence(sequence_elem):
    """Parse a momentum sequence from XML"""
    # Get protocol reference from either namespaced or non-namespaced attribute
    protocol_ref = sequence_elem.get('{http://botlab.dev/protocol}ref') or sequence_elem.get('protocol_ref')
    if not protocol_ref:
        raise KeyError("Missing required protocol reference in sequence element")
    
    # Validate other required attributes
    required_attrs = ['id', 'type']
    for attr in required_attrs:
        if sequence_elem.get(attr) is None:
            raise KeyError(f"Missing required attribute '{attr}' in sequence element")
    
    messages = []
    for msg in sequence_elem.findall('message'):
        role = msg.find('role')
        if role is None or not role.get('type'):
            logging.error(f"Missing role in message for sequence {sequence_elem.get('id')}")
            continue
            
        content = msg.find('content')
        if content is None:
            continue
            
        messages.append(Message(
            role=role.get('type'),
            content=content.text or "",
            agent="system",  # System agent for momentum sequences
            chat_id=0,  # Special chat_id for system sequences
            thread_id=None,  # No thread for system sequences
            message_id=msg.get('position')  # Use position as message_id if available
        ))
    
    # Handle missing temperature attribute
    temp = sequence_elem.get('temperature')
    if temp is not None:
        temp = float(temp)
    else:
        temp = 0.7  # Default temperature if not specified
    
    return MomentumSequence(
        id=sequence_elem.get('id'),
        type=sequence_elem.get('type'),
        protocol_ref=protocol_ref,
        temperature=temp,
        messages=messages
    )

def parse_protocol(protocol_elem) -> Protocol:
    """Parse a protocol from XML"""
    objectives = {
        'primary': protocol_elem.find('.//objectives/primary').text,
        'secondary': [s.text for s in protocol_elem.findall('.//objectives/secondary')]
    }
    
    style = {
        'communication': protocol_elem.find('.//style/communication').text,
        'analysis': protocol_elem.find('.//style/analysis').text
    }
    
    agent_definition = AgentDefinition(
        objectives=objectives,
        style=style
    )
    
    return Protocol(
        id=protocol_elem.get('id'),
        agent_definition=agent_definition.__dict__
    )

def validate_xml_dtd(xml_path: str) -> tuple[bool, list[str]]:
    """Validate XML against its DTD."""
    errors = []
    try:
        logger.info(f"Validating XML: {xml_path}")
        
        # Parse XML
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Validate required elements
        required_elements = ['metadata', 'protocols', 'momentum']
        for elem in required_elements:
            if root.find(elem) is None:
                msg = f"Missing required element <{elem}>"
                logger.error(msg)
                errors.append(msg)
        
        # Validate protocols
        protocols = root.find('protocols')
        if not protocols or len(protocols.findall('protocol')) == 0:
            msg = f"At least one <protocol> element is required"
            logger.error(msg)
            errors.append(msg)
            
        # Validate momentum
        momentum = root.find('momentum')
        if not momentum or len(momentum.findall('sequence')) == 0:
            msg = f"At least one <sequence> element is required within <momentum>"
            logger.error(msg)
            errors.append(msg)
        
        return len(errors) == 0, errors
            
    except Exception as e:
        msg = f"Error validating {Path(xml_path).name}: {str(e)}"
        logger.error(msg)
        errors.append(msg)
        return False, errors

def load_agent_config(config_path: str) -> AgentConfig:
    """Load agent configuration from XML file"""
    try:
        tree = ET.parse(config_path)
        root = tree.getroot()
        
        # Get metadata elements
        metadata = root.find('metadata')
        if metadata is None:
            raise ValueError("Missing required <metadata> element")
            
        name_elem = metadata.find('name')
        if name_elem is None:
            raise ValueError("Missing required <n> element in <metadata>")
        name = name_elem.text
            
        type_elem = metadata.find('type')
        if type_elem is None:
            raise ValueError("Missing required <type> element in <metadata>")
        type_name = type_elem.text
        category = type_elem.get('category')
            
        version_elem = metadata.find('version')
        if version_elem is None:
            raise ValueError("Missing required <version> element in <metadata>")
        version = version_elem.text
        
        # Get timing info
        response_interval = None
        response_interval_unit = None
        
        interval_elem = metadata.find('.//response_interval')
        if interval_elem is not None:
            response_interval = int(interval_elem.text)
            response_interval_unit = interval_elem.get('unit')
        
        # Get protocols
        protocols = []
        for protocol in root.findall('.//protocols/protocol'):
            protocols.append(parse_protocol(protocol))
        
        # Get momentum sequences
        sequences = []
        for sequence in root.findall('.//momentum/sequence'):
            sequences.append(parse_momentum_sequence(sequence))
        
        return AgentConfig(
            name=name,
            type=type_name,
            category=category,
            version=version,
            response_interval=response_interval,
            response_interval_unit=response_interval_unit,
            protocols=protocols,
            momentum_sequences=sequences
        )
        
    except ET.ParseError as e:
        raise Exception(f"DTD validation failed: {str(e)}")
    except Exception as e:
        raise Exception(f"Error loading config: {str(e)}")