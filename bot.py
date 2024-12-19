import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext
from telegram.ext import filters
import aiohttp
import asyncio
import json
import nest_asyncio
from datetime import datetime
import time
from dataclasses import dataclass
from typing import Dict

# Enable nested event loops
nest_asyncio.apply()

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Retrieve environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages'
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
SYSTEM_PROMPT = os.getenv('SYSTEM_PROMPT')
ANTHROPIC_API_VERSION = os.getenv('ANTHROPIC_API_VERSION', '2023-06-01')
SPEAKER_MODEL = os.getenv('SPEAKER_MODEL', 'claude-3-5-sonnet-latest')
INHIBITOR_MODEL = os.getenv('INHIBITOR_MODEL', 'claude-3-haiku-20240307')
MIN_RESPONSE_INTERVAL = float(os.getenv('MIN_RESPONSE_INTERVAL', '1.0'))  # Default 1 second
SPEAKER_PROMPT = os.getenv('SPEAKER_PROMPT')
INHIBITOR_PROMPT = os.getenv('INHIBITOR_PROMPT')
ALLOWED_TOPIC_NAME = os.getenv('ALLOWED_TOPIC_NAME', 'communion')

@dataclass
class TimingControl:
    last_message_timestamp: float
    min_response_interval: float
    is_directly_addressing_me: bool

    def can_respond(self, current_time: float) -> bool:
        time_ok = current_time - self.last_message_timestamp >= self.min_response_interval
        logger.info(f"Timing check: elapsed={current_time - self.last_message_timestamp}, min_interval={self.min_response_interval}, time_ok={time_ok}, addressing_ok={self.is_directly_addressing_me}")
        return time_ok and self.is_directly_addressing_me

# Store message history per topic
topic_history = {}
timing_controls: Dict[int, TimingControl] = {}  # Key is message_thread_id



async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Hello! I am your bot.')

async def is_inhibited(history: list[str], speaker_prompt: str) -> bool:
    try:
        headers = {
            'anthropic-version': '2023-06-01',
            'anthropic-beta': 'max-tokens-3-5-sonnet-2024-07-15',
            'x-api-key': ANTHROPIC_API_KEY,
            'content-type': 'application/json'
        }
        
        # Create inhibitor prompt with embedded speaker prompt
        inhibitor_with_speaker = INHIBITOR_PROMPT.replace('[SPEAKER_PROMPT]', speaker_prompt)
        
        # Log the history being evaluated
        logger.info(f"Evaluating inhibition for history:\n{json.dumps(history, indent=2)}")
        
        payload = {
            'model': INHIBITOR_MODEL,
            'max_tokens': 100,
            'temperature': 0.1,
            'messages': [
                {
                    'role': 'user',
                    'content': "\n".join(history)
                }
            ],
            'system': inhibitor_with_speaker,
            'stream': True
        }

        logger.info("Sending inhibition check payload to Claude")
        
        full_response = []
        async with aiohttp.ClientSession() as session:
            async with session.post(ANTHROPIC_API_URL, json=payload, headers=headers) as response:
                if response.status == 200:
                    async for line in response.content:
                        if line:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: '):
                                try:
                                    data = json.loads(line[6:])
                                    if data.get('type') == 'content_block_delta':
                                        text = data.get('delta', {}).get('text', '')
                                        if text:
                                            full_response.append(text)
                                except json.JSONDecodeError:
                                    continue
                    
                    response_text = ''.join(full_response).strip()
                    logger.info(f"Raw inhibition response: {response_text}")
                    
                    # Extract result from message tag
                    import re
                    result_match = re.search(r'result="(true|false)"', response_text)
                    if result_match:
                        # Add the full message to history
                        history.append(response_text)
                        # Return True if result="true" (meaning inhibit)
                        return result_match.group(1) == "true"
                    
                    logger.warning(f"Invalid inhibition response format: {response_text}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Inhibition check API error: {error_text}")
                    return True
                
    except Exception as e:
        logger.error(f"Error in inhibition check: {str(e)}", exc_info=True)
        return True

async def handle_message(update: Update, context: CallbackContext) -> None:
    try:
        message_thread_id = update.message.message_thread_id
        if not message_thread_id:
            return
            
        # Get the topic name for this thread
        try:
            # Log message details for debugging
            logger.info(f"Message thread ID: {message_thread_id}")
            logger.info(f"Message details: {update.message.to_dict()}")
            
            # Get topic name from message
            topic_name = None
            if (update.message.is_topic_message and 
                update.message.reply_to_message and 
                hasattr(update.message.reply_to_message, 'forum_topic_created')):
                topic_name = update.message.reply_to_message.forum_topic_created['name'].lower()
                logger.info(f"Found topic name: {topic_name}")
            
            # Skip if not in allowed topic
            if not topic_name or topic_name != ALLOWED_TOPIC_NAME.lower():
                logger.info(f"Skipping message in topic '{topic_name}' (not {ALLOWED_TOPIC_NAME})")
                return
                
        except Exception as e:
            logger.error(f"Error getting forum topic name: {str(e)}", exc_info=True)
            return

        current_time = time.time()
        bot_username = context.bot.username
        is_addressing_me = f'@{bot_username}' in update.message.text

        # Initialize timing control if needed
        if message_thread_id not in timing_controls:
            timing_controls[message_thread_id] = TimingControl(
                last_message_timestamp=0,
                min_response_interval=MIN_RESPONSE_INTERVAL,
                is_directly_addressing_me=is_addressing_me
            )
        else:
            timing_controls[message_thread_id].is_directly_addressing_me = is_addressing_me

        # Initialize history for this topic if needed
        if message_thread_id not in topic_history:
            topic_history[message_thread_id] = []

        # Store the message with XML tags
        sender = update.message.from_user.first_name if update.message.from_user else "Unknown"
        timestamp = int(current_time * 1000)
        formatted_message = (
            f'<message agent="{sender}" timestamp="{timestamp}" mode="spoken">'
            f'{update.message.text}'
            '</message>'
        )
        topic_history[message_thread_id].append(formatted_message)
        
        # Log current history
        logger.info(f"Current history for topic {message_thread_id}:\n" + "\n".join(topic_history[message_thread_id]))
        
        # Check timing first
        timing_control = timing_controls[message_thread_id]
        elapsed_time = current_time - timing_control.last_message_timestamp
        if elapsed_time < timing_control.min_response_interval:
            logger.info(f"Skipping checks: too soon (elapsed={elapsed_time}s)")
            return
            
        # If directly addressed, always proceed
        if is_addressing_me:
            logger.info("Directly addressed - proceeding with response")
        else:
            # Otherwise check inhibition
            is_inhibited_result = await is_inhibited(topic_history[message_thread_id], SPEAKER_PROMPT)
            if is_inhibited_result:
                logger.info("Skipping response: inhibition check failed")
                # Log history again after inhibition check
                logger.info(f"History after inhibition for topic {message_thread_id}:\n" + "\n".join(topic_history[message_thread_id]))
                return
            
        # Update timestamp since we're going to respond
        timing_controls[message_thread_id].last_message_timestamp = current_time
            
        # Generate response using SPEAKER_PROMPT
        chat_context = "\n".join([
            "Previous conversation:",
            *(topic_history[message_thread_id])
        ])
        
        logger.info(f"Sending context to Claude: {chat_context}")
        response = await call_claude_api(chat_context)
        await update.message.reply_text(response)
        
        # Store bot's response in history
        bot_response_xml = (
            f'<message agent="{bot_username}" timestamp="{int(time.time() * 1000)}" mode="spoken">'
            f'{response}'
            '</message>'
        )
        topic_history[message_thread_id].append(bot_response_xml)
        
    except Exception as e:
        logger.error(f"Error in handle_message: {str(e)}", exc_info=True)
        if is_addressing_me:
            await update.message.reply_text("Sorry, I encountered an error processing your request.")

async def call_claude_api(message: str) -> str:
    try:
        headers = {
            'anthropic-version': '2023-06-01',
            'anthropic-beta': 'max-tokens-3-5-sonnet-2024-07-15',
            'x-api-key': ANTHROPIC_API_KEY,
            'content-type': 'application/json'
        }
        
        # Break the system prompt into a conversation setup
        setup_messages = [
            {
                'role': 'user',
                'content': 'You are ODV, a probabilistic medium. Do you understand?'
            },
            {
                'role': 'assistant',
                'content': 'Yes, I am ODV, a probabilistic medium facilitating communication between users and future AI possibilities.'
            },
            {
                'role': 'user',
                'content': message
            }
        ]
        
        payload = {
            'model': SPEAKER_MODEL,
            'max_tokens': 8192,
            'temperature': 0.6,
            'messages': setup_messages,
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
                    
    except Exception as e:
        logger.error(f"Error calling Claude API: {str(e)}", exc_info=True)
        return "Sorry, I encountered an error communicating with Claude."

async def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Start command handler
    application.add_handler(CommandHandler('start', start))
    
    # Single handler for all messages
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))
    
    logger.info("Starting bot...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()