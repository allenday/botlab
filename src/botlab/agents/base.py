from abc import ABC, abstractmethod
from typing import Dict, Optional
import logging
from ..xml_handler import AgentConfig
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class Agent(ABC):
    """Base class for all agents"""
    
    def __init__(self, config: AgentConfig):
        logger.info(f"Initializing agent: {config.name}")
        self.config = config
        if not config:
            logger.error("Missing agent configuration")
            raise ValueError("Agent requires a valid configuration")
        
        # Cache service config
        self.api_base = "https://api.anthropic.com/v1"
        self.model = config.service.model
        self.api_version = config.service.api_version
        
    async def _call_llm(self, system_prompt: str, user_message: str) -> Optional[str]:
        """Call LLM API directly"""
        try:
            logger.debug(f"Calling LLM for agent {self.config.name}")
            response = await self._make_api_call(system_prompt, user_message)
            if not response:
                logger.error(f"No response from LLM for agent {self.config.name}")
                return None
            return response
            
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            return None
            
    def _get_api_key(self) -> str:
        """Get API key from environment"""
        import os
        key = os.getenv('ANTHROPIC_API_KEY')
        if not key:
            logger.error("ANTHROPIC_API_KEY environment variable not set")
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        logger.debug("Successfully retrieved API key")
        return key

    def _extract_code(self, analysis: str, default: str = '310') -> str:
        """Extract status code from XML context response"""
        try:
            logger.debug("Extracting status code from analysis")
            # Parse full context XML
            context = ET.fromstring(analysis)
            # Get management message code
            mgmt_msg = context.find('.//management/message')
            if mgmt_msg is not None:
                code = mgmt_msg.get('code')
                if code:
                    logger.debug(f"Extracted code {code} from analysis")
                    return code
            logger.warning(f"No code found in analysis, using default: {default}")
            return default
        except Exception as e:
            logger.error(f"Error extracting code: {str(e)}")
            return default

    @abstractmethod
    async def process_message(self, message) -> Dict:
        """Process an incoming message and return response"""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict:
        """Get agent metadata"""
        pass 