import os
import logging
import time
import json
import aiohttp
from typing import Optional, List, Dict, Tuple, Set
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from .xml_handler import load_agent_config, AgentConfig, MomentumMessage
from pathlib import Path
from .agents.base import Agent
from .agents.inhibitor import InhibitorFilter
from .services.anthropic import AnthropicService
from .message import Message
from .momentum import MomentumManager
from .history import MessageHistory
from .handlers import MessageHandler
from .timing import ResponseTimer

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages'

class Bot:
    def __init__(self, config_path: str = None):
        # Load environment variables
        load_dotenv()
        self.agent_username = os.getenv('AGENT_USERNAME')
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        self.claude_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.allowed_topic = os.getenv('ALLOWED_TOPIC_NAME')
        self.model = os.getenv('SPEAKER_MODEL', 'claude-3-opus-20240229')
        self.api_version = os.getenv('ANTHROPIC_API_VERSION', '2023-06-01')
        
        if not self.telegram_token or not self.claude_api_key:
            raise ValueError("Missing required environment variables")
        
        # Load agent configuration
        if config_path is None:
            config_path = os.getenv('SPEAKER_PROMPT_FILE', 'config/agents/claude.xml')
        
        self.config = load_agent_config(str(config_path))
        if not self.config:
            raise ValueError(f"Failed to load agent configuration from {config_path}")
        
        # Initialize conversation state
        self.history = MessageHistory()
        self.timer = ResponseTimer(
            self.config.response_interval,
            datetime.now()
        )
        
        # Initialize services and managers
        self.llm_service = AnthropicService(
            self.claude_api_key,
            self.api_version,
            self.model
        )
        self.momentum = MomentumManager(self.config, self.llm_service)
        self.message_handler = MessageHandler(
            self.history,
            self.momentum,
            self.llm_service,
            self.agent_username,
            self.allowed_topic
        )
        
        # Initialize agent pipeline
        self.agents = self._initialize_pipeline()
        
    def _initialize_pipeline(self) -> List[Agent]:
        """Initialize the agent pipeline"""
        agents = []
        
        # Load inhibitor agent
        inhibitor_config_path = os.getenv('INHIBITOR_CONFIG_FILE', 'config/agents/inhibitor.xml')
        inhibitor_config = load_agent_config(str(inhibitor_config_path))
        if not inhibitor_config:
            raise ValueError(f"Failed to load inhibitor configuration")
            
        # Get speaker prompt for inhibitor
        init_sequence = self.config.get_momentum_sequence('initialization')
        speaker_prompt = ""
        for msg in init_sequence:
            if msg.role_type == 'system':
                speaker_prompt = msg.content
                break
                
        agents.append(InhibitorFilter(inhibitor_config, speaker_prompt))
        
        # Future: Add contextualizer and other pipeline agents here
        
        return agents
    
    async def process_message_pipeline(self, message: Dict) -> Optional[Dict]:
        """Process message through agent pipeline"""
        current_message = message
        
        for agent in self.agents:
            result = await agent.process_message(current_message)
            if not result:
                return None
                
            # Check for inhibition codes (4xx, 5xx)
            code = result.get('code', '500')
            if code.startswith(('4', '5')):
                return result
                
            # Update message with agent's analysis
            current_message.update(result)
            
        return current_message
    
    async def should_respond(self, chat_id: int, update: Update) -> bool:
        """Check if the bot should respond based on timing, context and inhibition."""
        message_time = datetime.fromtimestamp(update.message.date.timestamp())
        if not self.timer.can_respond(chat_id, message_time):
            return False
        
        if self.allowed_topic:
            message_topic = update.message.message_thread_id
            if not message_topic or str(message_topic) != self.allowed_topic:
                logger.info(f"Message not in allowed topic: {message_topic} != {self.allowed_topic}")
                return False
        
        # Check if directly addressed
        if f'@{self.agent_username}' in update.message.text:
            return True
        
        # Run message through pipeline
        message = {
            'history_xml': self.history.get_history_xml(chat_id),
            'chat_id': chat_id,
            'update': update,
            'text': update.message.text,
            'thread_id': update.message.message_thread_id,
            'timestamp': message_time.isoformat()
        }
        
        result = await self.process_message_pipeline(message)
        if not result:
            logger.info("Pipeline processing failed")
            return False
            
        # Check for inhibition codes
        code = result.get('code', '500')
        if code.startswith(('4', '5')):
            logger.info(f"Response inhibited: {result.get('content', 'No reason provided')}")
            return False
        
        return True
    
    def add_to_history(self, chat_id: int, role: str, content: str, from_user: str, message_channel: str, message_id: int, reply_to_channel: str, reply_to_message_id: int):
        """Add message to history"""
        self.history.add_message(
            chat_id,
            role,
            content,
            from_user,
            message_channel,
            message_id,
            reply_to_channel,
            reply_to_message_id
        )
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        welcome_message = (
            f"Hello! I'm {self.config.name}, {self.config.type}. "
            "I'm here to help you with your questions and tasks. "
            "Feel free to mention me in your messages when you need assistance."
        )
        await update.message.reply_text(welcome_message)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages."""
        if not update.message or not update.message.text:
            return
        
        # Check if we should respond
        if not await self.should_respond(update.message.chat_id, update):
            return
            
        response = await self.message_handler.process_message(update, self.agents)
        if response:
            await update.message.reply_text(response)
            self.timer.record_response(update.message.chat_id)
    
    def run(self):
        """Run the bot."""
        # Create application
        application = Application.builder().token(self.telegram_token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Start polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = Bot()
    bot.run() 
