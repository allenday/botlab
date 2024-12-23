from typing import Dict, Optional, Union
from datetime import datetime
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger(__name__)

class Message:
    """Represents a conversation message"""
    
    def __init__(
        self, 
        content: str,
        role: str,
        agent: Optional[str] = None,
        channel: Optional[int] = None,
        message_id: Optional[int] = None,
        reply_to_channel: Optional[int] = None,
        reply_to_message_id: Optional[int] = None,
        timestamp: Optional[Union[str, datetime]] = None
    ) -> None:
        """Initialize message
        Args:
            content: Message content
            role: Message role (user/assistant/system)
            agent: Agent name (optional)
            channel: Channel ID (optional)
            message_id: Message ID (optional)
            reply_to_channel: Channel being replied to (optional)
            reply_to_message_id: Message being replied to (optional)
            timestamp: Message timestamp as string or datetime (defaults to now if not provided)
        """
        self.content = content
        self.role = role
        self.agent = agent
        self.channel = channel
        self.message_id = message_id
        self.reply_to_channel = reply_to_channel
        self.reply_to_message_id = reply_to_message_id
        
        # Handle timestamp
        if isinstance(timestamp, str):
            self.timestamp = timestamp
        elif isinstance(timestamp, datetime):
            self.timestamp = timestamp.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            self.timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    def to_xml(self) -> str:
        """Convert message to XML format"""
        xml = [f'  <message role="{self.role}"']
        
        # Add optional attributes
        if self.agent:
            xml[0] += f' agent="{self.agent}"'
        if self.channel:
            xml[0] += f' channel="{self.channel}"'
        if self.message_id:
            xml[0] += f' id="{self.message_id}"'
        if self.reply_to_channel:
            xml[0] += f' reply_to_channel="{self.reply_to_channel}"'
        if self.reply_to_message_id:
            xml[0] += f' reply_to="{self.reply_to_message_id}"'
        
        # Add timestamp (always present)
        xml[0] += f' timestamp="{self.timestamp}"'
        
        xml[0] += '>'
        xml.append(f'    <content>{self.content}</content>')
        xml.append('  </message>')
        
        return '\n'.join(xml)