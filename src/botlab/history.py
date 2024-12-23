from typing import List, Dict, Optional
import logging
from datetime import datetime
from .message import Message

logger = logging.getLogger(__name__)

class MessageHistory:
    """Manages conversation history"""
    
    def __init__(self):
        self.messages: Dict[int, Dict[Optional[int], List[Message]]] = {}
        logger.info("Initialized message history")
        
    def add_message(self, chat_id: int, content: str, role: str, thread_id: Optional[int] = None, agent: Optional[str] = None) -> None:
        """Add message to history"""
        if chat_id not in self.messages:
            self.messages[chat_id] = {}
            
        if thread_id not in self.messages[chat_id]:
            self.messages[chat_id][thread_id] = []
            
        self.messages[chat_id][thread_id].append(
            Message(content=content, role=role, agent=agent)
        )
        logger.debug(f"Added message to history for chat {chat_id}, thread {thread_id}")
        
    def get_thread_history(self, chat_id: int, thread_id: Optional[int] = None) -> str:
        """Get conversation history for a thread in XML format"""
        if chat_id not in self.messages or thread_id not in self.messages[chat_id]:
            logger.debug(f"No history found for chat {chat_id}, thread {thread_id}")
            return "<history></history>"
            
        messages = self.messages[chat_id][thread_id]
        
        # Convert to XML format
        xml = ["<history>"]
        for msg in messages:
            xml.append(f'  <message role="{msg.role}">')
            xml.append(f'    <content>{msg.content}</content>')
            xml.append('  </message>')
        xml.append("</history>")
        
        history_xml = "\n".join(xml)
        logger.debug(f"Retrieved history for chat {chat_id}, thread {thread_id}: {history_xml}")
        return history_xml
        
    def clear_history(self, chat_id: int, thread_id: Optional[int] = None) -> None:
        """Clear history for a chat/thread"""
        if chat_id in self.messages:
            if thread_id is None:
                self.messages[chat_id] = {}
            elif thread_id in self.messages[chat_id]:
                self.messages[chat_id][thread_id] = []
        logger.debug(f"Cleared history for chat {chat_id}, thread {thread_id}")