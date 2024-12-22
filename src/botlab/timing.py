from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ResponseTimer:
    """Manages response timing and rate limiting"""
    
    def __init__(self, response_interval: float, start_time: datetime):
        self.response_interval = response_interval
        self.start_time = start_time
        self.last_response_time: Dict[int, datetime] = {}
        
    def can_respond(self, chat_id: int, message_time: datetime) -> bool:
        """Check if enough time has passed for a response"""
        # Check if message is from before bot start
        if message_time < self.start_time:
            logger.info("Message is from before bot start time")
            return False
            
        # Check response interval
        last_response = self.last_response_time.get(chat_id)
        if last_response:
            time_since_last = (datetime.now() - last_response).total_seconds()
            if time_since_last < self.response_interval:
                logger.info(f"Response interval not met: {time_since_last}s < {self.response_interval}s")
                return False
                
        return True
        
    def record_response(self, chat_id: int) -> None:
        """Record time of response"""
        self.last_response_time[chat_id] = datetime.now() 