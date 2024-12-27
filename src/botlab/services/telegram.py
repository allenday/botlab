import logging
from typing import Optional, Callable, Awaitable
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from ..message import Message

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(
        self, 
        token: str, 
        message_handler: Callable[[Message], Awaitable[Optional[str]]], 
        start_handler: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]
    ):
        """Initialize Telegram service"""
        self.token = token
        self.message_handler = message_handler
        self.start_handler = start_handler
        self.app = None
        logger.info("Initialized Telegram service")

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await self.start_handler(update, context)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        # Convert Telegram Update to our Message model
        msg = Message(
            content=update.message.text,
            role="user",
            agent=update.message.from_user.username,
            chat_id=update.message.chat_id,
            thread_id=update.message.message_thread_id,
            message_id=update.message.message_id,
            reply_to_thread_id=update.message.reply_to_message.message_thread_id if update.message.reply_to_message else None,
            reply_to_message_id=update.message.reply_to_message.message_id if update.message.reply_to_message else None
        )
        
        # Process message and get response
        response = await self.message_handler(msg)
        
        if response:
            # Send response back to Telegram
            await update.message.reply_text(response)

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