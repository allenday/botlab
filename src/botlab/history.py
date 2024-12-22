from typing import List, Dict, Optional
import logging
from datetime import datetime
from .message import Message

logger = logging.getLogger(__name__)

class MessageHistory:
    """Manages conversation history and XML formatting"""
    
    def __init__(self):
        logger.info("Initializing message history")
        self.conversations: Dict[int, List[Message]] = {}
        
    def add_message(
        self,
        chat_id: int,
        role: str,
        content: str,
        agent: str,
        channel: Optional[int] = None,
        message_id: Optional[int] = None,
        reply_to_channel: Optional[int] = None,
        reply_to_message: Optional[int] = None
    ) -> None:
        """Add a message to the conversation history"""
        logger.debug(f"Adding message to chat {chat_id}: role={role}, agent={agent}, id={message_id}")
        if chat_id not in self.conversations:
            logger.info(f"Creating new conversation history for chat {chat_id}")
            self.conversations[chat_id] = []
            
        message = Message(
            role=role,
            content=content,
            agent=agent,
            channel=channel,
            message_id=message_id,
            reply_to_channel=reply_to_channel,
            reply_to_message_id=reply_to_message
        )
        
        self.conversations[chat_id].append(message)
        logger.debug(f"Message added to chat {chat_id}, history size: {len(self.conversations[chat_id])}")
        
    def get_history_xml(self, chat_id: int, channel: Optional[int] = None) -> str:
        """Get conversation history in XML format"""
        logger.debug(f"Getting XML history for chat {chat_id}, channel {channel}")
        messages = self.conversations.get(chat_id, [])
        
        # Filter by channel if specified
        if channel is not None:
            messages = [msg for msg in messages if msg.channel == channel]
        
        logger.debug(f"Found {len(messages)} messages in history")
        
        messages_xml = [msg.to_xml() for msg in messages]
        xml = f"<conversation>\n{''.join(messages_xml)}\n</conversation>"
        logger.debug(f"Generated conversation XML: {xml[:200]}...")
        return xml
        
    def get_messages(self, chat_id: int) -> List[Message]:
        """Get list of messages for a chat"""
        logger.debug(f"Retrieving message list for chat {chat_id}")
        messages = self.conversations.get(chat_id, [])
        logger.debug(f"Returning {len(messages)} messages")
        return messages 