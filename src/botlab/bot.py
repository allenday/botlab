import os
import logging
import time
import json
import aiohttp
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from .xml_handler import load_agent_config, AgentConfig, MomentumMessage
from pathlib import Path

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
        self.last_response_time: Dict[int, datetime] = {}
        self.conversation_history: Dict[int, List[Dict]] = {}
        self.start_time = datetime.now()
    
    def get_momentum_sequence(self, sequence_type: str) -> List[MomentumMessage]:
        """Get a momentum sequence by type."""
        for sequence in self.config.momentum_sequences:
            if sequence.type == sequence_type:
                return sequence.messages
        return []
    
    def format_message_history(self, chat_id: int) -> str:
        """Format message history as XML."""
        history = self.conversation_history.get(chat_id, [])
        messages_xml = []
        
        for msg in history:
            role = msg.get('role', '')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            
            message_xml = f"""
            <message timestamp="{timestamp}">
                <role type="{role}">{role}</role>
                <content>{content}</content>
            </message>
            """
            messages_xml.append(message_xml)
        
        return f"<conversation>\n{''.join(messages_xml)}\n</conversation>"
    
    def should_respond(self, chat_id: int, update: Update) -> bool:
        """Check if the bot should respond based on timing and context."""
        current_time = datetime.now()
        
        # Check response interval
        last_response = self.last_response_time.get(chat_id)
        if last_response:
            time_since_last = (current_time - last_response).total_seconds()
            if time_since_last < self.config.response_interval:
                logger.info(f"Response interval not met: {time_since_last}s < {self.config.response_interval}s")
                return False
        
        # Check if message is after bot start time
        message_time = datetime.fromtimestamp(update.message.date.timestamp())
        if message_time < self.start_time:
            logger.info("Message is from before bot start time")
            return False
            
        # Check if message is in allowed topic
        if self.allowed_topic:
            message_topic = update.message.message_thread_id
            if not message_topic or str(message_topic) != self.allowed_topic:
                logger.info(f"Message not in allowed topic: {message_topic} != {self.allowed_topic}")
                return False
        
        return True
    
    def add_to_history(self, chat_id: int, role: str, content: str):
        """Add a message to the conversation history."""
        if chat_id not in self.conversation_history:
            self.conversation_history[chat_id] = []
        
        self.conversation_history[chat_id].append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /start command."""
        welcome_message = (
            f"Hello! I'm {self.config.name}, {self.config.type}. "
            "I'm here to help you with your questions and tasks. "
            "Feel free to mention me in your messages when you need assistance."
        )
        await update.message.reply_text(welcome_message)
    
    async def call_claude_api(self, messages: List[Dict]) -> str:
        """Call Claude API directly using aiohttp."""
        headers = {
            'anthropic-version': self.api_version,
            'anthropic-beta': 'max-tokens-3-5-sonnet-2024-07-15',
            'x-api-key': self.claude_api_key,
            'content-type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'max_tokens': 1000,
            'temperature': 0.7,
            'messages': messages,
            'stream': True
        }
        
        logger.info(f"Sending payload to Claude: {json.dumps(payload, indent=2)}")
        
        full_response = []
        async with aiohttp.ClientSession() as session:
            async with session.post(ANTHROPIC_API_URL, json=payload, headers=headers) as response:
                if response.status == 200:
                    # Handle streaming response
                    async for line in response.content:
                        if line:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: '):
                                try:
                                    data = json.loads(line[6:])  # Skip "data: " prefix
                                    if data.get('type') == 'content_block_delta':
                                        text = data.get('delta', {}).get('text', '')
                                        if text:
                                            full_response.append(text)
                                except json.JSONDecodeError:
                                    continue
                    
                    return ''.join(full_response)
                else:
                    error_text = await response.text()
                    logger.error(f"Claude API error: {error_text}")
                    return "Sorry, I couldn't process your request at this time."
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages."""
        if not update.message or not update.message.text:
            return
        
        chat_id = update.message.chat_id
        message_text = update.message.text
        
        # Check if we should respond
        if not self.should_respond(chat_id, update):
            return
        
        # Add user message to history
        self.add_to_history(chat_id, 'user', message_text)
        
        try:
            # Prepare conversation context
            history_xml = self.format_message_history(chat_id)
            
            # Get initialization sequence
            init_sequence = self.get_momentum_sequence('init')
            system_messages = [
                {'role': msg.role_type, 'content': msg.content}
                for msg in init_sequence
            ]
            
            # Create the message list for Claude
            messages = system_messages + [
                {'role': 'user', 'content': f"""
                Here is the conversation history in XML format:
                {history_xml}
                
                Based on this history and the latest message, please provide a helpful response.
                Remember to follow the guidelines about group chat interaction and context awareness.
                """}
            ]
            
            # Get response from Claude
            assistant_message = await self.call_claude_api(messages)
            await update.message.reply_text(assistant_message)
            
            # Update state
            self.last_response_time[chat_id] = datetime.now()
            self.add_to_history(chat_id, 'assistant', assistant_message)
            
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            await update.message.reply_text(
                "I apologize, but I encountered an error while processing your message. "
                "Please try again later."
            )
    
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