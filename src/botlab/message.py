from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Message:
    """Represents a message in the chat system"""
    content: str
    role: str  # user/assistant/system
    agent: str  # username or bot name
    chat_id: int  # telegram chat_id
    thread_id: Optional[int] = None  # telegram message_thread_id
    message_id: Optional[int] = None  # telegram message_id
    reply_to_thread_id: Optional[int] = None  # telegram reply message_thread_id
    reply_to_message_id: Optional[int] = None  # telegram reply message_id
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    def to_xml(self) -> str:
        """Convert message to XML format"""
        xml = [f'  <message role="{self.role}"']
        
        # Add optional attributes
        if self.agent:
            xml[0] += f' agent="{self.agent}"'
        if self.chat_id:
            xml[0] += f' chat_id="{self.chat_id}"'
        if self.message_id:
            xml[0] += f' id="{self.message_id}"'
        if self.reply_to_thread_id:
            xml[0] += f' reply_to_thread_id="{self.reply_to_thread_id}"'
        if self.reply_to_message_id:
            xml[0] += f' reply_to="{self.reply_to_message_id}"'
        
        xml[0] += f' timestamp="{self.timestamp}">'
        xml.append(f'    <content>{self.content}</content>')
        xml.append('  </message>')
        
        return '\n'.join(xml)