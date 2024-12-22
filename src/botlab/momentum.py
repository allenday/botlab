from typing import Optional, List, Dict
import logging
from .message import Message
from .services.anthropic import AnthropicService
from .xml_handler import AgentConfig, MomentumMessage

logger = logging.getLogger(__name__)

class MomentumManager:
    """Manages conversation momentum including initialization and recovery"""
    
    def __init__(self, config: AgentConfig, llm_service: AnthropicService):
        self.config = config
        self.llm_service = llm_service
        self.initialized_chats = set()
        
    def _get_sequence(self, sequence_id: str) -> Optional[List[MomentumMessage]]:
        """Get a momentum sequence by ID"""
        sequence = next(
            (seq for seq in self.config.momentum_sequences if seq.id == sequence_id),
            None
        )
        return sequence.messages if sequence else None
        
    async def initialize(self, chat_id: int) -> bool:
        """Initialize momentum for a new chat"""
        try:
            messages = self._get_sequence("init")
            if not messages:
                logger.error("No initialization sequence found")
                return False
                
            # Convert to API format
            api_messages = [
                {'role': msg.role_type, 'content': msg.content or ''}
                for msg in messages
            ]
            
            response = await self.llm_service.call_api("", api_messages)
            if response:
                self.initialized_chats.add(chat_id)
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error initializing momentum: {str(e)}")
            return False
            
    async def recover(self, chat_id: int) -> bool:
        """Recover momentum after context loss"""
        try:
            messages = self._get_sequence("recovery")
            if not messages:
                logger.error("No recovery sequence found")
                return False
                
            api_messages = [
                {'role': msg.role_type, 'content': msg.content or ''}
                for msg in messages
            ]
            
            response = await self.llm_service.call_api("", api_messages)
            return bool(response)
            
        except Exception as e:
            logger.error(f"Error recovering momentum: {str(e)}")
            return False 