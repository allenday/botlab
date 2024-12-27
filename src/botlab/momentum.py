from typing import Optional, List, Set
import logging
from .message import Message

logger = logging.getLogger(__name__)

class MomentumManager:
    """Manages conversation momentum and context"""
    
    def __init__(self, llm_service, config=None):
        self.llm_service = llm_service
        self.config = config
        self.protocols = {}  # Map of protocol IDs to definitions
        self._initialize_protocols()
        self.initialized_chats: Set[int] = set()
        logger.info("Initialized momentum manager")
        
    def _initialize_protocols(self):
        """Build protocol lookup table"""
        if self.config and self.config.protocols:
            for protocol in self.config.protocols:
                self.protocols[protocol.id] = protocol
                
    def _get_sequence(self, sequence_id: str) -> Optional[List[Message]]:
        """Get messages from a specific sequence"""
        if not self.config or not self.config.momentum_sequences:
            return None
            
        for sequence in self.config.momentum_sequences:
            if sequence.id == sequence_id:
                # Validate protocol reference exists
                if sequence.protocol_ref not in self.protocols:
                    logger.error(f"Invalid protocol reference: {sequence.protocol_ref}")
                    return None
                return sequence.messages
        return None
        
    async def initialize(self, chat_id: int) -> bool:
        """Initialize momentum for a chat"""
        try:
            logger.info(f"Initializing momentum for chat {chat_id}")
            if not self.llm_service:
                logger.error("LLM service not initialized")
                return False
            # Initialize chat-specific context
            self.initialized_chats.add(chat_id)
            return True
        except Exception as e:
            logger.error(f"Failed to initialize momentum: {str(e)}")
            return False
            
    async def recover(self, chat_id: int) -> bool:
        """Recover momentum after error"""
        try:
            logger.info(f"Recovering momentum for chat {chat_id}")
            if not self.llm_service:
                logger.error("LLM service not initialized")
                return False
            # Reset chat-specific context
            if chat_id in self.initialized_chats:
                self.initialized_chats.remove(chat_id)
            return True
        except Exception as e:
            logger.error(f"Failed to recover momentum: {str(e)}")
            return False
            
    async def get_response(self, sequence_or_history) -> Optional[str]:
        """Generate response using conversation history and protocol content"""
        try:
            logger.debug("Generating response from history")
            if not self.llm_service:
                logger.error("LLM service not initialized")
                return None
            
            # Get protocol content for system message
            protocol_content = []
            active_protocols = set()  # Track which protocols are active
            temperature = 0.7  # Default temperature
            
            # Handle both MomentumSequence objects and history XML
            if hasattr(sequence_or_history, 'protocol_ref'):
                # Direct sequence object
                current_sequence = sequence_or_history
                temperature = max(0.0, min(1.0, current_sequence.temperature))  # Clamp temperature
                if current_sequence.protocol_ref in self.protocols:
                    protocol = self.protocols[current_sequence.protocol_ref]
                    active_protocols.add(protocol)
                    protocol_content.extend(protocol.get_content())
                messages = current_sequence.messages
            else:
                # History XML string
                history_xml = sequence_or_history
                
                # Determine current sequence based on conversation state
                if self.config and self.config.momentum_sequences:
                    # If there's only one sequence, use it (for testing)
                    if len(self.config.momentum_sequences) == 1:
                        current_sequence = self.config.momentum_sequences[0]
                    # Otherwise, select based on conversation state
                    else:
                        if "Start initialization" in history_xml and "Hello" not in history_xml:
                            current_sequence = next((seq for seq in self.config.momentum_sequences if seq.id == "init"), None)
                        elif "Hello" in history_xml and "Analyze" not in history_xml:
                            current_sequence = next((seq for seq in self.config.momentum_sequences if seq.id == "greeting"), None)
                        elif "Analyze" in history_xml and "Wrap" not in history_xml:
                            current_sequence = next((seq for seq in self.config.momentum_sequences if seq.id == "analysis"), None)
                        elif "Wrap" in history_xml:
                            current_sequence = next((seq for seq in self.config.momentum_sequences if seq.id == "conclusion"), None)
                        else:
                            current_sequence = self.config.momentum_sequences[0]  # Default to first sequence
                    
                    # Get protocol content from sequence's protocol
                    if current_sequence and current_sequence.protocol_ref in self.protocols:
                        temperature = max(0.0, min(1.0, current_sequence.temperature))  # Clamp temperature
                        protocol = self.protocols[current_sequence.protocol_ref]
                        active_protocols.add(protocol)
                        protocol_content.extend(protocol.get_content())
                    messages = current_sequence.messages
                else:
                    messages = []
            
            # Add protocol content to first system message
            if protocol_content and messages:
                first_msg = messages[0]
                if first_msg.role == "system":
                    first_msg.content = "\n".join(protocol_content) + "\n\n" + first_msg.content
            
            # Call LLM service with protocol content and messages
            response = await self.llm_service.call_api(
                messages=messages,
                temperature=temperature
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get response: {str(e)}")
            return None 