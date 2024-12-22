import logging
from typing import Optional, Callable
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self, token: str, message_handler: Callable, start_handler: Callable):
        """Initialize Telegram service"""
        self.token = token
        self.message_handler = message_handler
        self.start_handler = start_handler
        self.app = None

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await self.start_handler(update, context)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        await self.message_handler(update, context)

    def start(self):
        """Start the Telegram bot"""
        logger.info("Starting Telegram service")
        self.app = Application.builder().token(self.token).build()
        
        # Add handlers
        self.app.add_handler(CommandHandler("start", self.handle_start))
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_message
        ))
        
        # Start polling
        logger.info("Starting message polling")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)

    def stop(self):
        """Stop the Telegram bot"""
        if self.app:
            logger.info("Stopping Telegram service")
            self.app.stop() 