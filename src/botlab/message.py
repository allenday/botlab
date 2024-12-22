from typing import Dict, Optional
from datetime import datetime
import xml.etree.ElementTree as ET

class Message:
    """Represents a message in the conversation"""
    
    def __init__(
        self,
        role: str,
        content: str,
        agent: str,
        channel: Optional[str] = None,
        message_id: Optional[int] = None,
        reply_to_channel: Optional[str] = None,
        reply_to_message_id: Optional[int] = None,
        timestamp: Optional[str] = None
    ):
        self.role = role
        self.content = content
        self.agent = agent
        self.channel = channel
        self.message_id = message_id
        self.reply_to_channel = reply_to_channel
        self.reply_to_message_id = reply_to_message_id
        self.timestamp = timestamp or datetime.now().isoformat()
        
    def to_dict(self) -> Dict:
        """Convert message to dictionary format"""
        return {
            'role': self.role,
            'agent': self.agent,
            'message_channel': self.channel,
            'message_id': self.message_id,
            'reply_to_channel': self.reply_to_channel,
            'reply_to_message_id': self.reply_to_message_id,
            'content': self.content,
            'timestamp': self.timestamp
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'Message':
        """Create message from dictionary"""
        return cls(
            role=data.get('role', ''),
            content=data.get('content', ''),
            agent=data.get('agent', ''),
            channel=data.get('message_channel'),
            message_id=data.get('message_id'),
            reply_to_channel=data.get('reply_to_channel'),
            reply_to_message_id=data.get('reply_to_message_id'),
            timestamp=data.get('timestamp')
        ) 
        
    def to_xml(self) -> str:
        """Convert message to XML format"""
        # Create XML element
        msg = ET.Element('message')
        msg.set('timestamp', self.timestamp)
        msg.set('channel', str(self.channel) if self.channel else '')
        msg.set('id', str(self.message_id) if self.message_id else '')
        msg.set('agent', f'@{self.agent}' if self.agent else '')
        
        # Add reply_to element
        reply = ET.SubElement(msg, 'reply_to')
        reply.set('channel', str(self.reply_to_channel) if self.reply_to_channel else '')
        reply.set('id', str(self.reply_to_message_id) if self.reply_to_message_id else '')
        
        # Add role element
        role = ET.SubElement(msg, 'role')
        role.set('type', self.role)
        role.text = self.role
        
        # Add content element
        content = ET.SubElement(msg, 'content')
        content.text = self.content
        
        return ET.tostring(msg, encoding='unicode', method='xml')
        
    @classmethod
    def from_xml(cls, xml_str: str) -> 'Message':
        """Create message from XML string"""
        try:
            # Parse XML string
            msg = ET.fromstring(xml_str)
            
            # Extract attributes
            timestamp = msg.get('timestamp')
            channel = msg.get('channel')
            message_id = msg.get('id')
            agent = msg.get('agent', '').lstrip('@')
            
            # Get reply_to info
            reply = msg.find('reply_to')
            reply_to_channel = reply.get('channel') if reply is not None else None
            reply_to_message_id = reply.get('id') if reply is not None else None
            
            # Get role and content
            role = msg.find('role')
            content = msg.find('content')
            
            if role is None or content is None:
                raise ValueError("Missing required elements")
            
            return cls(
                role=role.get('type'),
                content=content.text or '',
                agent=agent,
                channel=channel,
                message_id=int(message_id) if message_id else None,
                reply_to_channel=reply_to_channel,
                reply_to_message_id=int(reply_to_message_id) if reply_to_message_id else None,
                timestamp=timestamp
            )
            
        except Exception as e:
            logger.error(f"Error parsing message XML: {str(e)}")
            return None