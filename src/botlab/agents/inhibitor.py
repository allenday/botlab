from typing import Dict, Optional
import logging
from .filter import Filter
import xml.etree.ElementTree as ET
import os
from ..services.anthropic import AnthropicService
from ..xml_handler import AgentConfig

logger = logging.getLogger(__name__)

class InhibitorFilter(Filter):
    """
    Inhibitor that filters messages based on conversation context and agent role.
    Makes binary allow/block decisions using status codes.
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.llm_service = AnthropicService(
            api_key=os.getenv('ANTHROPIC_API_KEY'),
            api_version=config.service.api_version,
            model=config.service.model
        )
        logger.info(f"Initialized InhibitorFilter with config: {config.name}")
        
    def get_metadata(self) -> Dict:
        """Get agent metadata"""
        return {
            'name': self.config.name,
            'type': self.config.type,
            'category': self.config.category,
            'version': self.config.version
        }
        
    async def _filter_message(self, message: Dict) -> Optional[Dict]:
        """Required implementation of abstract method from Filter base class"""
        try:
            logger.info("=== INHIBITOR ANALYSIS START ===")
            logger.info(f"Analyzing message: {message.get('content', '')}")
            logger.info(f"Message context: {message.get('history_xml', '')}")

            # Get initialization sequence
            logger.info("Looking for 'init' sequence")
            init_sequences = self.config.get_momentum_sequence('init')
            if not init_sequences:
                logger.error("No initialization sequence found")
                logger.info(f"Available sequences: {[seq.id for seq in self.config.momentum_sequences]}")
                return None
            
            logger.info(f"Found {len(init_sequences)} initialization messages")
            system_msg = next((msg.content for msg in init_sequences if msg.role_type == 'system'), None)
            if not system_msg:
                logger.error("No system message found in initialization sequence")
                logger.info(f"Available message types: {[msg.role_type for msg in init_sequences]}")
                return None

            # Get inhibitor decision from LLM
            response = await self.llm_service.call_api(
                system=system_msg,
                messages=[{
                    'role': 'user',
                    'content': f"""
                    Here is the conversation history and current message to analyze:
                    {message.get('history_xml', '')}
                    
                    Current message: {message.get('content', '')}
                    
                    Analyze this message and decide whether to allow a response.
                    Return your analysis in XML format.
                    """
                }]
            )
            
            logger.info(f"LLM Analysis: {response}")

            # Parse response XML
            try:
                root = ET.fromstring(response)
                code = root.get('code', '500')
                reason = root.text.strip() if root.text else "No reason provided"
                
                logger.info(f"Decision Code: {code}")
                logger.info(f"Reason: {reason}")
                
                if code.startswith(('4', '5')):
                    logger.info("DECISION: Blocking response")
                    return {'code': code, 'reason': reason}
                else:
                    logger.info("DECISION: Allowing response")
                    message.update({'code': code, 'reason': reason})
                    return message
                    
            except ET.ParseError as e:
                logger.error(f"Failed to parse inhibitor response XML: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error in inhibitor processing: {str(e)}")
            logger.exception("Full traceback:")  # Added full traceback logging
            return None
        finally:
            logger.info("=== INHIBITOR ANALYSIS END ===")