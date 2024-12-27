import os
import logging
from typing import Optional, Dict
from telegram import Update
from telegram.ext import ContextTypes
from .xml_handler import load_agent_config
from .services.telegram import TelegramService
from .services.anthropic import AnthropicService
from .momentum import MomentumManager
from .history import MessageHistory
from .handlers import MessageHandler
from .timing import ResponseTimer
from .filters import FilterChain, FilterSet, MentionFilter, TopicFilter, RateLimitFilter
from .agents.inhibitor import InhibitorFilter

logger = logging.getLogger(__name__)

class Bot:
    def __init__(self, config_path: str, username: str = None, allowed_topic: str = None):
        """Initialize bot with configuration"""
        self.config = load_agent_config(config_path)
        
        # Use provided values or fall back to environment variables
        self.username = username or os.getenv('BOT_USERNAME')
        self.allowed_topic = allowed_topic or os.getenv('BOT_ALLOWED_TOPIC')
        
        # Initialize filter chain
        self.filter_chain = FilterChain()
        
        # Add access filters (mention OR topic) only if both are specified
        access_filters = []
        if self.username:
            access_filters.append(MentionFilter(self.username))
        if self.allowed_topic:
            access_filters.append(TopicFilter(self.allowed_topic))
        if access_filters:
            self.filter_chain.add_filter_set(FilterSet(access_filters))
        
        # Initialize services
        self.timer = None
        self.history = None
        self.telegram = None
        self.inhibitor = None
        
        try:
            # Set up rate limiting if configured
            if hasattr(self.config, 'response_interval') and self.config.response_interval:
                self.timer = ResponseTimer(
                    response_interval=self.config.response_interval,
                    response_interval_unit=self.config.response_interval_unit
                )
                self.filter_chain.add_filter_set(RateLimitFilter(self.timer))
        except Exception as e:
            logger.error(f"Failed to initialize rate limiting: {str(e)}")
        
        try:
            self.history = MessageHistory()
        except Exception as e:
            logger.error(f"Failed to initialize message history: {str(e)}")
            
        try:
            self.telegram = TelegramService()
        except Exception as e:
            logger.error(f"Failed to initialize telegram service: {str(e)}")
            
        try:
            self.inhibitor = InhibitorFilter(self.config)
        except Exception as e:
            logger.error(f"Failed to initialize inhibitor: {str(e)}")

    def _should_respond(self, message) -> bool:
        """Determine if bot should respond to message"""
        if message is None or not hasattr(message, 'content'):
            return False
        
        result = self.filter_chain.check(message)
        if not result.passed:
            logger.debug(f"Message filtered: {result.reason}")
        return result.passed

    def handle_message(self, message):
        """Handle incoming message synchronously"""
        if message is None:
            logger.debug("Received None message")
            return None
        
        if not self._should_respond(message):
            logger.debug("Message filtered out")
            return None
        
        try:
            if self.inhibitor:
                return self.inhibitor.process(message)
            return None
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return None

    def run(self):
        """Run the bot"""
        logger.info("Starting bot")
        if self.telegram:
            self.telegram.start()
        else:
            logger.warning("Cannot start bot - TelegramService not initialized")

    def stop(self):
        """Stop the bot"""
        logger.info("Stopping bot")
        if self.telegram:
            self.telegram.stop()
        else:
            logger.warning("Cannot stop bot - TelegramService not initialized")

    async def handle_telegram_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming Telegram message asynchronously"""
        try:
            if not update.message:
                logger.debug("Empty message received")
                return
                
            # Check if we should respond
            if not self._should_respond(update.message):
                logger.debug("Message filtered out")
                return

            # Get conversation history if available
            history_xml = None
            if self.history:
                history_xml = await self.history.get_thread_history(
                    chat_id=update.message.chat_id,
                    message_id=update.message.message_id
                )

            # Process through inhibitor
            response = None
            if self.inhibitor:
                response = self.inhibitor.process({
                    'content': update.message.text,
                    'chat_id': update.message.chat_id,
                    'thread_id': update.message.message_thread_id,
                    'history_xml': history_xml
                })

            # Send response
            if response and self.telegram:
                await self.telegram.send_message(
                    chat_id=update.message.chat_id,
                    message_thread_id=update.message.message_thread_id,
                    text=response
                )
                
                # Record response for rate limiting
                if self.timer:
                    self.timer.record_response(update.message.chat_id)
            
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}") 
