from typing import Dict, List, Optional
import logging
import aiohttp
import json
from ..message import Message

logger = logging.getLogger(__name__)

class AnthropicService:
    """Service for interacting with Anthropic's Claude API"""
    
    def __init__(self, api_key: str, api_version: str, model: str):
        logger.info(f"Initializing Anthropic service with model: {model}")
        self.api_key = api_key
        self.api_version = api_version
        self.model = model
        self.api_base = 'https://api.anthropic.com/v1/messages'
        
    async def call_api(
        self, 
        system_msg: str, 
        messages: List[Message], 
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Optional[str]:
        """Call Claude API with streaming response handling"""
        try:
            logger.info(f"Calling Claude API: {len(messages)} messages")
            
            headers = {
                'anthropic-version': self.api_version,
                'anthropic-beta': 'max-tokens-3-5-sonnet-2024-07-15',
                'x-api-key': self.api_key,
                'content-type': 'application/json'
            }
            
            # Convert Message objects to Anthropic format
            anthropic_messages = [
                {
                    'role': msg.role,
                    'content': msg.content
                }
                for msg in messages
            ]
            
            payload = {
                'model': self.model,
                'max_tokens': max_tokens,
                'temperature': temperature,
                'system': system_msg,
                'messages': anthropic_messages,
                'stream': True
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_base, json=payload, headers=headers) as response:
                    if response.status == 200:
                        logger.info("Claude API call successful")
                        return await self._handle_stream(response)
                    else:
                        error_text = await response.text()
                        logger.error(f"Claude API error: {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"API call failed: {str(e)}")
            return None
            
    async def _handle_stream(self, response) -> str:
        """Handle streaming response from Claude API"""
        logger.debug("Starting to process streaming response")
        full_response = []
        async for line in response.content:
            if line:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if data.get('type') == 'content_block_delta':
                            text = data.get('delta', {}).get('text', '')
                            if text:
                                full_response.append(text)
                                logger.debug(f"Received chunk: {text[:50]}...")
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse streaming response chunk")
                        continue
        logger.debug(f"Completed stream processing, total length: {len(''.join(full_response))}")
        return ''.join(full_response) 