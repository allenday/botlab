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
from .agents.inhibitor import InhibitorFilter

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
        self.last_response_time: Dict[int, datetime] = {}
        self.conversation_history: Dict[int, List[Dict]] = {}
        self.start_time = datetime.now()
        self.initialized_chats: Set[int] = set()  # Track which chats have been initialized
        
        # Initialize agent pipeline
        self.agents = self._initialize_agents()
        
    def _initialize_agents(self) -> List[Agent]:
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
        
        return agents
    
    def get_momentum_sequence(self, sequence_type: str) -> List[MomentumMessage]:
        """Get a momentum sequence by type."""
        for sequence in self.config.momentum_sequences:
            if sequence.type == sequence_type:
                logger.info(sequence.messages)
                return sequence.messages
        return []
    
    def format_message_history(self, chat_id: int) -> str:
        """Format message history as XML."""
        history = self.conversation_history.get(chat_id, [])
        messages_xml = []
        
        for msg in history:
            logger.debug(f"{msg=}")
            role = msg.get('role', '')
            agent = msg.get('agent', '')
            message_channel = msg.get('message_channel', '')
            message_id = msg.get('message_id', '')
            reply_to_channel = msg.get('reply_to_channel', '')
            reply_to_message_id = msg.get('reply_to_message_id', '')
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            
            message_xml = f"""
            <message timestamp="{timestamp}" channel="{message_channel}" id="{message_id}" agent="@{agent}">
                <reply_to channel="{reply_to_channel}" id="{reply_to_message_id}"/>
                <role type="{role}">{role}</role>
                <content>{content}</content>
            </message>
            """
            logger.info(f"{message_xml=}")
            messages_xml.append(message_xml)
        
        return f"<conversation>\n{''.join(messages_xml)}\n</conversation>"
    
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
        current_time = datetime.now()
        
        # Basic checks (existing code)
        last_response = self.last_response_time.get(chat_id)
        if last_response:
            time_since_last = (current_time - last_response).total_seconds()
            if time_since_last < self.config.response_interval:
                logger.info(f"Response interval not met: {time_since_last}s < {self.config.response_interval}s")
                return False
        
        message_time = datetime.fromtimestamp(update.message.date.timestamp())
        if message_time < self.start_time:
            logger.info("Message is from before bot start time")
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
            'history_xml': self.format_message_history(chat_id),
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
        """Add a message to the conversation history."""
        if chat_id not in self.conversation_history:
            self.conversation_history[chat_id] = []
        
        self.conversation_history[chat_id].append({
            'role': role,
            'agent': from_user,
            'message_channel': message_channel,
            'message_id': message_id,
            'reply_to_channel': reply_to_channel,
            'reply_to_message_id': reply_to_message_id,
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
    
    async def call_claude_api(self, system, messages: List[Dict]) -> str:
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
            'system': system,
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
    
    async def initialize_momentum(self, chat_id: int) -> bool:
        """Initialize momentum for a new chat."""
        try:
            # Get initialization sequence
            init_sequence = next(
                (seq for seq in self.config.momentum_sequences if seq.id == "init"),
                None
            )
            if not init_sequence:
                logger.error("No initialization sequence found in config")
                return False
            
            # Convert momentum sequence to Claude API format
            messages = []
            for msg in init_sequence.messages:
                messages.append({
                    'role': msg.role_type,
                    'content': msg.content or ''
                })
            
            # Call Claude API with initialization sequence
            logger.info(f"Initializing momentum for chat {chat_id}")
            response = await self.call_claude_api(system="", messages=messages)
            
            if response:
                # Record initialization messages in history
                for msg in init_sequence.messages:
                    self.add_to_history(
                        chat_id,
                        msg.role_type,
                        msg.content or '',
                        self.agent_username,
                        None,
                        None,
                        None,
                        None
                    )
                
                # Mark chat as initialized
                self.initialized_chats.add(chat_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error initializing momentum: {str(e)}")
            return False
    
    async def recover_momentum(self, chat_id: int) -> bool:
        """Recover momentum for a chat that has lost context."""
        try:
            # Get recovery sequence
            recovery_sequence = next(
                (seq for seq in self.config.momentum_sequences if seq.id == "recovery"),
                None
            )
            if not recovery_sequence:
                logger.error("No recovery sequence found in config")
                return False
            
            # Convert momentum sequence to Claude API format
            messages = []
            for msg in recovery_sequence.messages:
                messages.append({
                    'role': msg.role_type,
                    'content': msg.content or ''
                })
            
            # Call Claude API with recovery sequence
            logger.info(f"Recovering momentum for chat {chat_id}")
            response = await self.call_claude_api(system="", messages=messages)
            
            if response:
                # Record recovery messages in history
                for msg in recovery_sequence.messages:
                    self.add_to_history(
                        chat_id,
                        msg.role_type,
                        msg.content or '',
                        self.agent_username,
                        None,
                        None,
                        None,
                        None
                    )
                self.add_to_history(
                    chat_id,
                    'assistant',
                    response,
                    self.agent_username,
                    None,
                    None,
                    None,
                    None
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error recovering momentum: {str(e)}")
            return False
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages."""
        if not update.message or not update.message.text:
            return
        
        chat_id = update.message.chat.id
        message_text = update.message.text
        from_user = update.message.from_user.username
        message_channel = update.message.message_thread_id
        message_id = update.message.message_id
        reply_to_message_id = None
        reply_to_channel = None
        if update.message.reply_to_message:
            reply_to_channel = update.message.reply_to_message.message_thread_id
            reply_to_message_id = update.message.reply_to_message.message_id
        
        # Check if we should respond
        if not await self.should_respond(chat_id, update):
            return
        
        # Add user message to history
        self.add_to_history(
            chat_id,
            'user',
            message_text,
            from_user,
            message_channel,
            message_id,
            reply_to_channel,
            reply_to_message_id
        )
        
        # Initialize momentum if needed
        if chat_id not in self.initialized_chats:
            success = await self.initialize_momentum(chat_id)
            if not success:
                await update.message.reply_text(
                    "I apologize, but I encountered an error during initialization. "
                    "Please try again later."
                )
                return
        
        try:
            # Create message for pipeline
            message = {
                'history_xml': self.format_message_history(chat_id),
                'chat_id': chat_id,
                'update': update,
                'text': message_text,
                'thread_id': message_channel,
                'timestamp': datetime.now().isoformat()
            }
            
            # Process through pipeline
            result = await self.process_message_pipeline(message)
            if not result:
                raise Exception("Pipeline processing failed")
            
            # Get initialization sequence
            init_sequence = self.get_momentum_sequence('initialization')
            system_msg = ""
            momentum_messages = []
            for msg in init_sequence:
                if msg.role_type == 'system':
                    system_msg = msg.content
                else:
                    momentum_messages.append({'role':msg.role_type,'content':msg.content})
            
            # Create the message list for Claude
            messages = momentum_messages + [
                {'role': 'user', 'content': f"""
                Here is the conversation history in XML format:
                {result.get('history_xml', '')}
                
                Based on this history and the latest message, please provide a response.
                """}
            ]

            # Get response from Claude
            assistant_message = await self.call_claude_api(system_msg, messages)
            await update.message.reply_text(assistant_message)
            
            # Update state
            self.last_response_time[chat_id] = datetime.now()
            self.add_to_history(
                    chat_id, 
                    'assistant', 
                    assistant_message, 
                    self.agent_username,
                    update.message.message_thread_id, 
                    update.message.message_id, 
                    update.message.message_thread_id, 
                    update.message.reply_to_message.message_id)
            
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            # Try to recover momentum
            if await self.recover_momentum(chat_id):
                await update.message.reply_text(
                    "I needed to realign my context. Could you please repeat your message?"
                )
            else:
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
