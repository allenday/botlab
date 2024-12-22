from typing import Dict, Optional, List, Set, Tuple
import logging
from datetime import datetime
from .observer import Observer
from ..xml_handler import AgentConfig
import xml.etree.ElementTree as ET
import re

logger = logging.getLogger(__name__)

class ThreadRelation:
    """Represents a relation between threads in the conversation poset"""
    def __init__(self, thread_id: str, relation_type: str, timestamp: str):
        logger.debug(f"Creating thread relation: {thread_id} ({relation_type})")
        self.thread_id = thread_id
        self.relation_type = relation_type  # 'concurrent' or 'precedes'
        self.timestamp = timestamp

class Contextualizer(Observer):
    """
    Contextualizer agent that analyzes conversation context and manages threads.
    Models conversations as a partially ordered set where messages are totally ordered
    in time but threads can be concurrent.
    """
    
    def __init__(self, config: AgentConfig):
        logger.info(f"Initializing contextualizer agent: {config.name}")
        super().__init__(config)
        self.boundaries: List[Dict] = []
        # Maps thread IDs to sets of concurrent threads with their start times
        self.concurrent_threads: Dict[str, Dict[str, str]] = {}
        # Maps thread IDs to lists of threads that must precede it
        self.thread_ordering: Dict[str, List[ThreadRelation]] = {}
        
    def _add_concurrent_thread(self, thread_id: str, concurrent_id: str, start_time: str):
        """Add a concurrent relationship between threads"""
        logger.debug(f"Adding concurrent relationship: {thread_id} <-> {concurrent_id}")
        if thread_id not in self.concurrent_threads:
            self.concurrent_threads[thread_id] = {}
        if concurrent_id not in self.concurrent_threads:
            self.concurrent_threads[concurrent_id] = {}
            
        self.concurrent_threads[thread_id][concurrent_id] = start_time
        self.concurrent_threads[concurrent_id][thread_id] = start_time
        logger.debug(f"Updated concurrent threads for {thread_id}: {self.concurrent_threads[thread_id]}")
        
    def _add_thread_ordering(self, before_id: str, after_id: str, timestamp: str):
        """Add an ordering constraint between threads"""
        logger.debug(f"Adding thread ordering: {before_id} -> {after_id}")
        if after_id not in self.thread_ordering:
            self.thread_ordering[after_id] = []
        self.thread_ordering[after_id].append(
            ThreadRelation(before_id, 'precedes', timestamp)
        )
        logger.debug(f"Updated thread ordering for {after_id}: {self.thread_ordering[after_id]}")
        
    async def _analyze_message(self, message) -> Optional[Dict]:
        """Analyze message for context management"""
        try:
            if isinstance(message, ET.Element):
                content = message.text
                thread_id = message.get('thread')
                concurrent_threads = message.get('concurrent_threads')
                if concurrent_threads:
                    concurrent_threads = set(concurrent_threads.split(','))
            else:
                logger.error(f"Unsupported message type: {type(message)}")
                return None
            
            # Get system prompt from momentum sequence
            system_prompt = self.config.momentum_sequences[0].messages[0].content
            
            # Call LLM for analysis
            analysis = await self._call_llm(system_prompt, content)
            if not analysis:
                return None
            
            logger.debug(f"LLM analysis response: {analysis}")
            
            # Parse XML response
            try:
                xml_start = analysis.find('<context>')
                xml_end = analysis.find('</context>') + len('</context>')
                if xml_start == -1 or xml_end == -1:
                    logger.error("Could not find XML tags in response")
                    return None
                xml_content = analysis[xml_start:xml_end]
                context = ET.fromstring(xml_content)
            except ET.ParseError as e:
                logger.error(f"Failed to parse LLM response as XML: {e}")
                return None
                
            # Get management message and code
            mgmt_msg = context.find('.//management/message')
            if mgmt_msg is None:
                logger.error("No management message found in LLM response")
                return None
                
            code = mgmt_msg.get('code')
            if not code:
                logger.error("No code found in management message")
                return None
            
            # Get thread ID from management message
            new_thread_id = mgmt_msg.get('thread')
            if not new_thread_id:
                logger.error("No thread ID found in management message")
                return None
                
            # Initialize thread with ID from LLM if it doesn't exist
            if new_thread_id not in self.threads:
                topic_context = context.find('.//topic_context/current')
                topic = topic_context.text if topic_context is not None else 'general'
                self.threads[new_thread_id] = {
                    'messages': [],
                    'metadata': {
                        'topic_context': {
                            'current': topic,
                            'previous': None,
                            'shift_type': None
                        }
                    },
                    'created_at': datetime.now().isoformat()
                }
            
            # Handle concurrent threads (code 311)
            if code == '311':
                thread = context.find('.//thread')
                if thread is not None:
                    # Check for concurrent relations
                    relations = thread.find('relations')
                    if relations is not None:
                        for concurrent in relations.findall('concurrent'):
                            concurrent_id = concurrent.get('thread_id')
                            start_time = concurrent.get('start_time')
                            if concurrent_id and start_time:
                                self._add_concurrent_thread(new_thread_id, concurrent_id, start_time)
                                
                        # Check for ordering constraints
                        for precedes in relations.findall('precedes'):
                            thread_id = precedes.get('thread_id')
                            timestamp = precedes.get('timestamp')
                            if thread_id and timestamp:
                                self._add_thread_ordering(new_thread_id, thread_id, timestamp)
                                
                    logger.info(f"Updated thread relations for {new_thread_id}")
            
            # Track context boundaries
            if code in ('330', '331'):
                self.boundaries.append({
                    'code': code,
                    'thread': new_thread_id,
                    'timestamp': datetime.now().isoformat()
                })
            
            self._update_lru_cache(new_thread_id)
            return {
                'code': code,
                'thread': new_thread_id,
                'mode': 'thought',
                'agent': 'contextualizer',
                'content': analysis
            }
            
        except Exception as e:
            logger.error(f"Error in message analysis: {str(e)}")
            return None
            
    async def process_message(self, message) -> Optional[Dict]:
        """Process incoming message and return context management response"""
        return await self._analyze_message(message)
        
    def get_context_boundaries(self) -> List[Dict]:
        """Get list of detected context boundaries"""
        logger.debug(f"Retrieving {len(self.boundaries)} context boundaries")
        return self.boundaries
        
    def get_concurrent_threads(self, thread_id: str) -> Dict[str, str]:
        """Get dict mapping concurrent thread IDs to their start times"""
        logger.debug(f"Getting concurrent threads for {thread_id}")
        concurrent = self.concurrent_threads.get(thread_id, {})
        logger.debug(f"Found {len(concurrent)} concurrent threads")
        return concurrent
        
    def get_thread_ordering(self, thread_id: str) -> List[ThreadRelation]:
        """Get list of threads that must precede this thread"""
        logger.debug(f"Getting thread ordering for {thread_id}")
        ordering = self.thread_ordering.get(thread_id, [])
        logger.debug(f"Found {len(ordering)} preceding threads")
        return ordering
        
    def _update_emotional_context(self, thread_id: str, content: str):
        """Update emotional context based on message content"""
        logger.debug(f"Updating emotional context for thread {thread_id}")
        thread = self.threads[thread_id]
        
        # High intensity for caps, exclamations
        if re.search(r'[A-Z]{3,}|!{2,}', content):
            logger.debug(f"Detected high emotional intensity in thread {thread_id}")
            thread['metadata']['emotional_context']['intensity'] = 1.0
            
        # Negative valence for urgent/critical/disaster
        if re.search(r'urgent|critical|disaster', content.lower()):
            logger.debug(f"Detected negative emotional valence in thread {thread_id}")
            thread['metadata']['emotional_context']['valence'] = -1.0
        logger.debug(f"Updated emotional context: {thread['metadata']['emotional_context']}")