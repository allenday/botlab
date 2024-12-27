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
            
    async def get_response(self, history_xml: str) -> Optional[str]:
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
                    temperature = current_sequence.temperature
                    protocol = self.protocols[current_sequence.protocol_ref]
                    active_protocols.add(protocol.id)
                    protocol_content.append(f"\nProtocol {protocol.id}:")
                    
                    # Add objectives
                    objectives = protocol.agent_definition.get('objectives', {})
                    if objectives:
                        protocol_content.append("Objectives:")
                        protocol_content.append(f"- Primary: {objectives.get('primary', '')}")
                        for secondary in objectives.get('secondary', []):
                            protocol_content.append(f"- Secondary: {secondary}")
                    
                    # Add style
                    style = protocol.agent_definition.get('style', {})
                    if style:
                        protocol_content.append("Style:")
                        protocol_content.append(f"- Communication: {style.get('communication', '')}")
                        protocol_content.append(f"- Analysis: {style.get('analysis', '')}")
            
            # If no sequence-specific protocol content, use all available protocols
            if not protocol_content and self.config and self.config.protocols:
                for protocol in self.config.protocols:
                    active_protocols.add(protocol.id)
                    protocol_content.append(f"\nProtocol {protocol.id}:")
                    
                    # Add objectives
                    objectives = protocol.agent_definition.get('objectives', {})
                    if objectives:
                        protocol_content.append("Objectives:")
                        protocol_content.append(f"- Primary: {objectives.get('primary', '')}")
                        for secondary in objectives.get('secondary', []):
                            protocol_content.append(f"- Secondary: {secondary}")
                    
                    # Add style
                    style = protocol.agent_definition.get('style', {})
                    if style:
                        protocol_content.append("Style:")
                        protocol_content.append(f"- Communication: {style.get('communication', '')}")
                        protocol_content.append(f"- Analysis: {style.get('analysis', '')}")
            
            # Ensure temperature is within bounds
            temperature = max(0.0, min(1.0, temperature))
            
            # Build system message with protocol content
            system_msg = "You are an intelligent assistant following these protocols:\n"
            system_msg += '\n'.join(protocol_content)
            system_msg += "\n\nRespond based on the conversation history."
            
            # Add protocol references to history XML
            if active_protocols:
                protocol_refs = ' '.join([f'proto:ref="{proto_id}"' for proto_id in active_protocols])
                history_xml = history_xml.replace("<history>", f"<history {protocol_refs}>")
            
            return await self.llm_service.call_api(
                system_msg=system_msg,
                messages=[{
                    'role': 'user',
                    'content': history_xml
                }],
                temperature=temperature
            )
        except Exception as e:
            logger.error(f"Failed to get response: {str(e)}")
            return None 