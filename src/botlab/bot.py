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

logger = logging.getLogger(__name__)

class Bot:
    def __init__(self, config_path: str = None):
        logger.info("Initializing bot")
        # Load environment variables
        load_dotenv()
        self.agent_username = os.getenv('AGENT_USERNAME')
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        self.allowed_topic = os.getenv('ALLOWED_TOPIC_NAME')
        self.claude_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        # Initialize components
        self.agents = []
        self.timer = ResponseTimer(
            response_interval=float(os.getenv('RESPONSE_INTERVAL_SECONDS', '1')),
            start_time=datetime.now()
        )
        self.history = MessageHistory()
        
        # Initialize services
        self.llm_service = AnthropicService(
            api_key=self.claude_api_key,
            api_version=os.getenv('ANTHROPIC_API_VERSION', '2024-02-15'),
            model=os.getenv('SPEAKER_MODEL', 'claude-3-opus-20240229')
        )
        
        # Initialize momentum manager
        self.momentum = MomentumManager(
            config=None,  # Will be set when first agent is added
            llm_service=self.llm_service
        )
        
        # Initialize message handler with required dependencies
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
        
        # Load configs and initialize agents
        if config_path:
            config = load_agent_config(str(config_path))
            if config:
                self.add_agent(config)

    def add_agent(self, config: AgentConfig):
        """Add an agent to the bot"""
        logger.info(f"Adding agent: {config.name}")
        if config.category == "filter":
            self.agents.append(InhibitorFilter(config))
        # Add other agent types as needed

    async def process_message_pipeline(self, message: Dict) -> Optional[Dict]:
        """Process message through agent pipeline"""
        # ... existing pipeline code ...

    async def should_respond(self, chat_id: int, update: Update) -> bool:
        """Check if bot should respond"""
        # ... existing response check code ...

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        # ... existing start code ...

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        # ... existing message handling code ...

    def run(self):
        """Run the bot"""
        logger.info("Starting bot")
        self.telegram.start()

    def stop(self):
        """Stop the bot"""
        logger.info("Stopping bot")
        self.telegram.stop()

if __name__ == '__main__':
    bot = Bot()
    bot.run() 
