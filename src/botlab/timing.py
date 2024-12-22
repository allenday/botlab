from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ResponseTimer:
    """Manages response timing and rate limiting"""
    
    def __init__(self, response_interval: float, response_interval_unit: str, start_time: datetime):
        self.response_interval = self._normalize_interval(response_interval, response_interval_unit)
        self.start_time = start_time
        self.last_response_time: Dict[int, datetime] = {}
        logger.info(f"Initialized response timer with interval: {self.response_interval} seconds")
        
    def _normalize_interval(self, interval: float, unit: str) -> float:
        """Convert interval to seconds based on unit"""
        if unit == 'milliseconds':
            return interval / 1000
        elif unit == 'seconds':
            return interval
        else:
            logger.warning(f"Unknown interval unit '{unit}', defaulting to seconds")
            return interval
        
    def can_respond(self, chat_id: int, message_time: datetime) -> bool:
        """Check if enough time has passed since last response"""
        if chat_id not in self.last_response_time:
            logger.debug(f"No previous response for chat {chat_id}")
            return True
        
        time_since_last = (message_time - self.last_response_time[chat_id]).total_seconds()
        logger.debug(f"Time since last response: {time_since_last} seconds")
        return time_since_last >= self.response_interval
        
    def record_response(self, chat_id: int) -> None:
        """Record time of response"""
        self.last_response_time[chat_id] = datetime.now() 
        
    def get_remaining_time(self, chat_id: int) -> float:
        """Get remaining time until next response allowed"""
        if chat_id not in self.last_response_time:
            return 0
        
        time_since_last = (datetime.now() - self.last_response_time[chat_id]).total_seconds()
        remaining = max(0, self.response_interval - time_since_last)
        return round(remaining, 1)