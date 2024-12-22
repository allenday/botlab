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
        """Initialize momentum for a chat"""
        try:
            logger.info(f"Initializing momentum for chat {chat_id}")
            messages = self._get_sequence("init")
            if not messages:
                logger.error("No initialization sequence found")
                return False
                
            # Convert to API format
            api_messages = [
                {'role': msg.role_type, 'content': msg.content or ''}
                for msg in messages
            ]
            
            logger.debug(f"Sending initialization sequence: {api_messages}")
            response = await self.llm_service.call_api("", api_messages)
            if response:
                logger.info(f"Successfully initialized momentum for chat {chat_id}")
                self.initialized_chats.add(chat_id)
                return True
                
            logger.warning(f"Failed to get response during initialization for chat {chat_id}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to initialize momentum: {str(e)}")
            return False
            
    async def recover(self, chat_id: int) -> bool:
        """Recover momentum after error"""
        try:
            logger.info(f"Attempting momentum recovery for chat {chat_id}")
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
            logger.error(f"Failed to recover momentum: {str(e)}")
            return False
            
    async def get_response(self, history_xml: str) -> Optional[str]:
        """Generate response using conversation history"""
        logger.debug("Generating response from history")
        try:
            # Get initialization sequence for system prompt and momentum
            init_sequence = self._get_sequence('init')
            if not init_sequence:
                logger.error("No initialization sequence found")
                return None
            
            system_msg = ""
            momentum_messages = []
            
            for msg in init_sequence:
                if msg.role_type == 'system':
                    system_msg = msg.content
                else:
                    momentum_messages.append({
                        'role': msg.role_type,
                        'content': msg.content
                    })
            
            # Create message list for LLM
            messages = momentum_messages + [{
                'role': 'user',
                'content': f"""
                Here is the conversation history in XML format:
                {history_xml}
                
                Based on this history and the latest message, please provide a response.
                """
            }]
            
            response = await self.llm_service.call_api(system_msg, messages)
            logger.debug(f"Generated response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return None 