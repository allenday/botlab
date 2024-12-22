from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime
import logging
from ..xml_handler import AgentConfig
from .base import Agent
import re

logger = logging.getLogger(__name__)

class Observer(Agent):
    """
    Base class for observer agents that monitor and analyze conversation context.
    Implements common observer functionality while allowing specific agents to
    define their own analysis and response logic.
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        
        logger.debug(f"Initializing Observer with config: {config}")
        
        self.threads: Dict[str, Dict] = {}  # Thread ID -> Thread data
        self.boundaries: List[Dict] = []    # Context boundaries detected
        self.lru_cache: List[str] = []      # LRU cache of thread IDs
        
        # Cache settings from config
        history_config = config.communication.input.history
        if history_config and history_config.lru_cache:
            logger.debug(f"Loading thread config: {history_config.lru_cache}")
            self.max_threads = history_config.lru_cache.max_count
            self.context_length = history_config.lru_cache.context_length
        else:
            logger.debug("Using default thread settings")
            self.max_threads = 5  # Default values
            self.context_length = 3
        
        # Load agent-specific metadata from config
        self.metadata = self._load_metadata()

    async def process_message(self, message) -> Dict:
        """Process an incoming message and return observer response"""
        try:
            # Extract message data
            content = message.text
            timestamp = message.get('timestamp')
            thread_id = message.get('thread')
            
            # Analyze message context
            analysis_result = await self._analyze_message(message)
            if analysis_result:
                return analysis_result
            
            # Default to thread update
            return self._format_response('310', thread_id, "Updated context")
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return self._format_response('500', None, "Error processing message")

    @abstractmethod
    async def _analyze_message(self, message) -> Optional[Dict]:
        """Analyze message based on configuration"""
        pass

    def get_thread_metadata(self, thread_id: str) -> Optional[Dict]:
        """Get metadata for a specific thread"""
        return self.threads.get(thread_id, {}).get('metadata')

    def get_context_boundaries(self) -> List[Dict]:
        """Get detected context boundaries"""
        return self.boundaries

    def _create_thread(self, content: str) -> str:
        """Create a new thread and return thread ID"""
        topic = self._extract_topic(content)
        thread_id = f"{topic}_{self._generate_hex_id()}"
        
        self.threads[thread_id] = {
            'messages': [],
            'metadata': {},
            'created_at': datetime.now().isoformat()
        }
        
        self._update_lru_cache(thread_id)
        return thread_id

    def _update_thread(self, thread_id: str, content: str):
        """Update thread with new message"""
        thread = self.threads[thread_id]
        thread['messages'].append({
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        
        # Maintain context length
        if len(thread['messages']) > self.context_length:
            thread['messages'].pop(0)
        
        self._update_lru_cache(thread_id)

    def _format_response(self, code: str, thread_id: Optional[str], message: str) -> Dict:
        """Format observer response"""
        return {
            'agent': self.config.name.lower(),
            'timestamp': str(int(datetime.now().timestamp() * 1000)),
            'mode': 'thought',
            'code': code,
            'thread': thread_id,
            'content': message
        }

    def _update_lru_cache(self, thread_id: str):
        """Update LRU cache of threads"""
        if thread_id in self.lru_cache:
            self.lru_cache.remove(thread_id)
        self.lru_cache.append(thread_id)
        
        # Evict oldest if over capacity
        while len(self.lru_cache) > self.max_threads:
            oldest = self.lru_cache.pop(0)
            if oldest in self.threads:
                del self.threads[oldest]

    def _load_metadata(self) -> Dict:
        """Load agent-specific metadata from config"""
        return {
            'name': self.config.name,
            'type': self.config.type,
            'category': self.config.category,
            'version': self.config.version
        }

    @staticmethod
    def _extract_topic(content: str) -> str:
        """Extract topic from message content using LLM analysis"""
        # This will be overridden by specific agents to use their LLM
        return 'general'

    @staticmethod
    def _generate_hex_id() -> str:
        """Generate random 4-character hex ID"""
        import random
        return ''.join(random.choices('0123456789abcdef', k=4))

    def get_metadata(self) -> Dict:
        """Get agent metadata"""
        return self.metadata


class Contextualizer(Observer):
    """
    Contextualizer agent that analyzes conversation context and manages threads.
    Implements specific context analysis logic including:
    - Thread creation and management
    - Emotional context tracking
    - Context boundary detection
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        
        # Initialize emotional context tracking
        self.emotional_baseline = {
            'valence': 0.0,
            'intensity': 0.0
        }
        
    async def _analyze_message(self, message) -> Optional[Dict]:
        """Analyze message for context management"""
        try:
            content = message.text
            thread_id = message.get('thread')
            
            # Get system prompt from momentum sequence
            system_prompt = self.config.momentum_sequences[0].messages[0].content
            
            # Call LLM for analysis
            analysis = await self._call_llm(system_prompt, content)
            if not analysis:
                return None
            
            # Extract status code from analysis
            code = self._extract_code(analysis)
            
            # Handle thread creation if needed
            if code == '300' or not thread_id:
                thread_id = self._create_thread(content)
                return self._format_response(code, thread_id, analysis)
            
            # Thread branching
            if code == '301' and thread_id not in self.threads:
                new_thread_id = self._create_thread(content)
                self.threads[new_thread_id]['parent_id'] = thread_id
                return self._format_response(code, new_thread_id, analysis)
            
            # Update existing thread
            self._update_thread(thread_id, content)
            
            return self._format_response(code, thread_id, analysis)
            
        except Exception as e:
            logger.error(f"Error in message analysis: {str(e)}")
            return None

    def _create_thread(self, content: str) -> str:
        """Create a new thread with emotional context"""
        thread_id = super()._create_thread(content)
        
        # Initialize emotional context
        self.threads[thread_id]['metadata']['emotional_context'] = {
            'valence': 0.0,
            'intensity': 0.0
        }
        
        # Analyze initial message
        self._update_emotional_context(thread_id, content)
        return thread_id

    def _update_thread(self, thread_id: str, content: str):
        """Update thread and emotional context"""
        super()._update_thread(thread_id, content)
        self._update_emotional_context(thread_id, content)

    def _update_emotional_context(self, thread_id: str, content: str):
        """Update emotional context based on message content"""
        thread = self.threads[thread_id]
        
        # High intensity for caps, exclamations
        if re.search(r'[A-Z]{3,}|!{2,}', content):
            thread['metadata']['emotional_context']['intensity'] = 1.0
            
        # Negative valence for urgent/critical/disaster
        if re.search(r'urgent|critical|disaster', content.lower()):
            thread['metadata']['emotional_context']['valence'] = -1.0