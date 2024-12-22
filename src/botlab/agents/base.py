from abc import ABC, abstractmethod
from typing import Dict, Optional
import logging
import aiohttp
import json
from ..xml_handler import AgentConfig
import re
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class Agent(ABC):
    """Base class for all agents"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        if not config:
            raise ValueError("Agent requires a valid configuration")
        
        # Cache service config
        self.api_base = "https://api.anthropic.com/v1"
        self.model = config.service.model
        self.api_version = config.service.api_version
        
    async def _call_llm(self, system_prompt: str, user_message: str) -> Optional[str]:
        """Call LLM API directly"""
        try:
            headers = {
                'anthropic-version': self.api_version,
                'anthropic-beta': 'max-tokens-3-5-sonnet-2024-07-15',
                'content-type': 'application/json',
                'x-api-key': self._get_api_key()
            }
            
            data = {
                'model': self.model,
                'max_tokens': 1024,
                'temperature': 0.1,
                'system': system_prompt,
                'messages': [
                    {'role': 'user', 'content': user_message}
                ],
                'stream': True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_base}/messages",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        full_response = ""
                        async for line in response.content:
                            if line:
                                try:
                                    line = line.decode('utf-8').strip()
                                    if line.startswith('data: '):
                                        data = json.loads(line[6:])
                                        if data.get('type') == 'message_stop':
                                            break
                                        if data.get('type') == 'content_block_delta':
                                            full_response += data['delta']['text']
                                except Exception as e:
                                    logger.error(f"Error parsing stream: {str(e)}")
                                    continue
                        return full_response
                    else:
                        error = await response.text()
                        logger.error(f"LLM API error: {error}")
                        return None
                        
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            return None
            
    def _get_api_key(self) -> str:
        """Get API key from environment"""
        import os
        key = os.getenv('ANTHROPIC_API_KEY')
        if not key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        return key

    def _extract_code(self, analysis: str, default: str = '310') -> str:
        """Extract status code from XML context response"""
        try:
            # Parse full context XML
            context = ET.fromstring(analysis)
            # Get management message code
            mgmt_msg = context.find('.//management/message')
            if mgmt_msg is not None:
                code = mgmt_msg.get('code')
                if code:
                    logger.debug(f"Extracted code {code} from analysis")
                    return code
            logger.warning(f"No code found in analysis")
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