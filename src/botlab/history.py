from typing import List, Dict, Optional
import logging
from datetime import datetime
from .message import Message

logger = logging.getLogger(__name__)

class MessageHistory:
    """Manages conversation history and XML formatting"""
    
    def __init__(self):
        self.conversations: Dict[int, List[Message]] = {}
        
    def add_message(
        self,
        chat_id: int,
        role: str,
        content: str,
        agent: str,
        channel: Optional[str] = None,
        message_id: Optional[int] = None,
        reply_to_channel: Optional[str] = None,
        reply_to_message_id: Optional[int] = None
    ) -> None:
        """Add a message to the conversation history"""
        if chat_id not in self.conversations:
            self.conversations[chat_id] = []
            
        message = Message(
            role=role,
            content=content,
            agent=agent,
            channel=channel,
            message_id=message_id,
            reply_to_channel=reply_to_channel,
            reply_to_message_id=reply_to_message_id
        )
        
        self.conversations[chat_id].append(message)
        
    def get_history_xml(self, chat_id: int) -> str:
        """Get conversation history in XML format"""
        messages = self.conversations.get(chat_id, [])
        messages_xml = [msg.to_xml() for msg in messages]
        return f"<conversation>\n{''.join(messages_xml)}\n</conversation>"
        
    def get_messages(self, chat_id: int) -> List[Message]:
        """Get list of messages for a chat"""
        return self.conversations.get(chat_id, []) 