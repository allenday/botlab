from abc import ABC, abstractmethod
from typing import Dict, Optional
import logging
from .base import Agent

logger = logging.getLogger(__name__)

class Filter(Agent):
    """
    Base class for filter agents that make binary decisions about message flow.
    Simpler than full Observer agents - just decides whether to allow or block messages.
    """
    
    async def process_message(self, message: Dict) -> Optional[Dict]:
        """Process a message and return filter decision"""
        try:
            decision = await self._filter_message(message)
            if not decision:
                return None
                
            return {
                'agent': self.config.name.lower(),
                'timestamp': message.get('timestamp'),
                'mode': 'filter',
                'code': decision.get('code', '500'),
                'thread': message.get('thread_id'),
                'content': decision.get('reason', 'No reason provided')
            }
            
        except Exception as e:
            logger.error(f"Error in filter: {str(e)}")
            return None
            
    @abstractmethod
    async def _filter_message(self, message: Dict) -> Optional[Dict]:
        """
        Filter a message. Should return:
        {
            'code': '2xx' for pass, '4xx'/'5xx' for block,
            'reason': explanation string
        }
        """
        pass 