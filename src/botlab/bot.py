import os
import logging
from typing import Optional, List, Dict
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes
from .xml_handler import load_agent_config, AgentConfig
from .agents.inhibitor import InhibitorFilter
from .services.telegram import TelegramService
from .services.anthropic import AnthropicService
from .momentum import MomentumManager
from .history import MessageHistory
from .handlers import MessageHandler
from .timing import ResponseTimer
from pathlib import Path

# Load environment variables first
load_dotenv()

# Set up logging based on environment variable
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class Bot:
    def __init__(self, config_path: str = None):
        logger.info("Initializing bot")
        # Load environment variables
        self.agent_username = os.getenv('AGENT_USERNAME')
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        self.allowed_topic = os.getenv('ALLOWED_TOPIC_NAME')
        self.claude_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        # Initialize components
        self.agents = []
        self.timer = None  # Will be set when inhibitor agent is added
        self.history = MessageHistory()
        
        # Initialize services
        self.llm_service = AnthropicService(
            api_key=self.claude_api_key,
            api_version=os.getenv('ANTHROPIC_API_VERSION', '2024-02-15'),
            model=os.getenv('SPEAKER_MODEL', 'claude-3-opus-20240229')
        )
        
        # Load ODV config first for momentum manager
        odv_config_path = Path(__file__).parent.parent.parent / "config/agents/odv.xml"
        odv_config = load_agent_config(str(odv_config_path))
        if not odv_config:
            logger.error("Failed to load ODV config")
            raise RuntimeError("Could not load ODV config")
        
        # Initialize momentum manager with ODV config
        self.momentum = MomentumManager(
            config=odv_config,
            llm_service=self.llm_service
        )
        
        # Initialize message handler
        self.message_handler = MessageHandler(
            history=self.history,
            momentum=self.momentum,
            llm_service=self.llm_service,
            agent_username=self.agent_username,
            allowed_topic=self.allowed_topic
        )
        
        # Initialize telegram service
        self.telegram = TelegramService(
            token=self.telegram_token,
            message_handler=self.handle_message,
            start_handler=self.start
        )
        
        # Load inhibitor config if provided
        if config_path:
            inhibitor_config = load_agent_config(str(config_path))
            if inhibitor_config:
                self.add_agent(inhibitor_config)

    def add_agent(self, config: AgentConfig):
        """Add an agent to the bot"""
        logger.info(f"Adding agent: {config.name}")
        if config.category == "filter":
            self.agents.append(InhibitorFilter(config))
            # Update response timer with config values
            self.timer = ResponseTimer(
                response_interval=config.response_interval,
                response_interval_unit=config.response_interval_unit,
                start_time=datetime.now()
            )
        # Add other agent types as needed

    async def process_message_pipeline(self, message: Dict) -> Optional[Dict]:
        """Process message through agent pipeline"""
        # ... existing pipeline code ...

    async def should_respond(self, chat_id: int, update: Update) -> bool:
        """Check if bot should respond"""
        logger.debug(f"Checking rate limit for chat {chat_id}")
        
        if self.timer is None:
            logger.warning("No response timer configured - loading default inhibitor config")
            config_path = Path(__file__).parent.parent.parent / "config/agents/inhibitor.xml"
            config = load_agent_config(str(config_path))
            if config:
                self.add_agent(config)
            else:
                logger.error("Failed to load inhibitor config")
                return False
        
        # Check if enough time has passed since last response
        can_respond = self.timer.can_respond(chat_id, update.message.date)
        
        if can_respond:
            logger.debug("Rate limit check passed")
            # Record this response time
            self.timer.record_response(chat_id)
        else:
            logger.debug(f"Rate limited - must wait {self.timer.get_remaining_time(chat_id)} seconds")
        
        return can_respond

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        # ... existing start code ...

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        logger.debug(f"Received message: {update.message.text}")
        
        # Check if message is meant for this bot
        if not update.message.text or f"@{self.agent_username}" not in update.message.text:
            logger.debug("Message not for this bot")
            return
        
        # Check rate limiting
        if not await self.should_respond(update.message.chat_id, update):
            logger.debug("Rate limited")
            return
        
        try:
            # Process message through handler
            response = await self.message_handler.handle_message(update.message)
            if response:
                logger.debug(f"Sending response: {response}")
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    message_thread_id=update.message.message_thread_id,
                    text=response
                )
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")

    def run(self):
        """Run the bot"""
        logger.info("Starting bot")
        self.telegram.start()

    def stop(self):
        """Stop the bot"""
        logger.info("Stopping bot")
        self.telegram.stop()

if __name__ == '__main__':
    # Load inhibitor config by default
    config_path = Path(__file__).parent.parent.parent / "config/agents/inhibitor.xml"
    bot = Bot(config_path=str(config_path))
    bot.run() 
