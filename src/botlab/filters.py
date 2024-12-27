from abc import ABC, abstractmethod
from typing import List, Set, Union
from dataclasses import dataclass
import logging
from .timing import ResponseTimer
import re

logger = logging.getLogger(__name__)

@dataclass
class FilterResult:
    passed: bool
    reason: str

class MessageFilter(ABC):
    @abstractmethod
    def check(self, message) -> FilterResult:
        pass

class FilterSet(MessageFilter):
    """A set of filters that run in parallel - ANY filter passing means the set passes"""
    def __init__(self, filters: List[Union[MessageFilter, 'FilterSet']]):
        self.filters = filters
    
    def check(self, message) -> FilterResult:
        """Run all filters in parallel - if any pass, the set passes"""
        results = [f.check(message) for f in self.filters if f is not None]
        passed_filters = [r for r in results if r.passed]
        
        if passed_filters:
            return FilterResult(
                passed=True,
                reason=f"Passed filters: {[r.reason for r in passed_filters]}"
            )
        
        return FilterResult(
            passed=False,
            reason=f"Failed all filters: {[r.reason for r in results]}"
        )

class FilterChain(MessageFilter):
    """A series of filter sets - ALL sets must pass for message to be processed"""
    def __init__(self):
        self.filter_sets: List[Union[FilterSet, MessageFilter]] = []
    
    def add_filter_set(self, filter_set: Union[FilterSet, MessageFilter]):
        """Add a set of parallel filters"""
        self.filter_sets.append(filter_set)
    
    def check(self, message) -> FilterResult:
        """Check message against all filter sets in series"""
        for filter_set in self.filter_sets:
            result = filter_set.check(message)
            if not result.passed:
                logger.debug(f"Message filtered out: {result.reason}")
                return result
        return FilterResult(True, "Passed all filter sets")

# Concrete filters
class MentionFilter(MessageFilter):
    def __init__(self, username: str):
        self.username = username
    
    def check(self, message) -> FilterResult:
        """Check if message mentions the bot's username"""
        if not message.content:
            return FilterResult(False, "Empty message")
            
        # Check for exact username match with @ prefix
        mention = f"@{self.username}"
        
        # Split on whitespace and punctuation
        words = re.split(r'[\s\.,!?]+', message.content)
        
        # Check for exact match
        if mention in words:
            return FilterResult(True, "Bot mentioned")
            
        # Check for mention in code block
        if "```" in message.content and mention in message.content:
            return FilterResult(True, "Bot mentioned in code block")
            
        return FilterResult(False, "Bot not mentioned")

class TopicFilter(MessageFilter):
    def __init__(self, allowed_topic: str):
        self.allowed_topic = allowed_topic
    
    def check(self, message) -> FilterResult:
        if message.topic == self.allowed_topic:
            return FilterResult(True, "Message in allowed topic")
        return FilterResult(False, "Message not in allowed topic") 

class RateLimitFilter(MessageFilter):
    def __init__(self, timer: ResponseTimer):
        self.timer = timer
    
    def check(self, message) -> FilterResult:
        """Check if message passes rate limiting"""
        if not hasattr(message, 'chat_id') or not hasattr(message, 'date'):
            return FilterResult(True, "Message missing rate limit attributes")
            
        if self.timer.can_respond(message.chat_id, message.date):
            return FilterResult(True, "Rate limit not exceeded")
            
        remaining = self.timer.get_remaining_time(message.chat_id)
        return FilterResult(False, f"Rate limited - must wait {remaining} seconds") 