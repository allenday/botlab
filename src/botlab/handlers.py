from typing import Optional, Dict
import logging
from telegram import Update
from datetime import datetime
from .message import Message
from .history import MessageHistory
from .momentum import MomentumManager
from .services.anthropic import AnthropicService

logger = logging.getLogger(__name__)

class MessageHandler:
    """Handles message processing and response generation"""
    
    def __init__(
        self,
        history: MessageHistory,
        momentum: MomentumManager,
        llm_service: AnthropicService,
        agent_username: str,
        allowed_topic: Optional[str] = None
    ):
        logger.info("Initializing MessageHandler")
        self.history = history
        self.momentum = momentum
        self.llm_service = llm_service
        self.agent_username = agent_username
        self.allowed_topic = allowed_topic
        logger.debug(f"Configured with agent: {agent_username}, topic: {allowed_topic}")
        
    def _extract_message_data(self, update: Update) -> Dict:
        """Extract relevant data from telegram update"""
        logger.debug(f"Extracting data from update {update.message.message_id}")
        data = {
            'text': update.message.text,
            'from_user': update.message.from_user.username,
            'channel': update.message.message_thread_id,
            'message_id': update.message.message_id,
            'reply_to_channel': update.message.reply_to_message.message_thread_id if update.message.reply_to_message else None,
            'reply_to_message_id': update.message.reply_to_message.message_id if update.message.reply_to_message else None
        }
        logger.debug(f"Extracted message data: {data}")
        return data
        
    async def process_message(self, update: Update, pipeline: list) -> Optional[str]:
        """Process message and generate response"""
        try:
            chat_id = update.message.chat_id
            logger.info(f"Processing message for chat {chat_id}")
            msg_data = self._extract_message_data(update)
            
            # Add user message to history
            logger.debug("Adding user message to history")
            self.history.add_message(
                chat_id,
                'user',
                msg_data['text'],
                msg_data['from_user'],
                msg_data['channel'],
                msg_data['message_id'],
                msg_data['reply_to_channel'],
                msg_data['reply_to_message_id']
            )
            
            # Initialize momentum if needed
            if chat_id not in self.momentum.initialized_chats:
                logger.info(f"First message in chat {chat_id}, initializing momentum")
                if not await self.momentum.initialize(chat_id):
                    logger.error(f"Failed to initialize momentum for chat {chat_id}")
                    return "I apologize, but I encountered an error during initialization."
            
            # Create pipeline message
            logger.debug("Creating pipeline message")
            message = {
                'history_xml': self.history.get_history_xml(chat_id),
                'chat_id': chat_id,
                'update': update,
                'text': msg_data['text'],
                'thread_id': msg_data['channel'],
                'timestamp': datetime.now().isoformat()
            }
            
            # Process through pipeline
            logger.info("Running message through pipeline")
            result = await self._run_pipeline(message, pipeline)
            if not result:
                logger.error("Pipeline processing failed")
                raise Exception("Pipeline processing failed")
            
            # Get response from LLM
            logger.debug("Generating LLM response")
            response = await self._generate_response(result)
            if not response:
                logger.error("Failed to generate LLM response")
                raise Exception("Failed to generate response")
                
            # Add response to history
            logger.debug("Adding bot response to history")
            self.history.add_message(
                chat_id,
                'assistant',
                response,
                self.agent_username,
                msg_data['channel'],
                msg_data['message_id'],
                msg_data['channel'],
                msg_data['message_id']
            )
            
            logger.info(f"Successfully processed message for chat {chat_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            if await self.momentum.recover(chat_id):
                logger.info(f"Successfully recovered momentum for chat {chat_id}")
                return "I needed to realign my context. Could you please repeat your message?"
            logger.error(f"Failed to recover momentum for chat {chat_id}")
            return "I apologize, but I encountered an error while processing your message."
            
    async def _run_pipeline(self, message: Dict, pipeline: list) -> Optional[Dict]:
        """Run message through processing pipeline"""
        current_message = message
        
        for agent in pipeline:
            result = await agent.process_message(current_message)
            if not result:
                return None
                
            if result.get('code', '500').startswith(('4', '5')):
                return result
                
            current_message.update(result)
            
        return current_message 

    async def _generate_response(self, pipeline_result: Dict) -> Optional[str]:
        """Generate response using LLM"""
        try:
            # Get initialization sequence for system prompt and momentum
            init_sequence = self.momentum.config.get_momentum_sequence('initialization')
            system_msg = ""
            momentum_messages = []
            
            for msg in init_sequence:
                if msg.role_type == 'system':
                    system_msg = msg.content
                else:
                    momentum_messages.append({
                        'role': msg.role_type,
                        'content': msg.content
                    })
            
            # Create message list for LLM
            messages = momentum_messages + [{
                'role': 'user',
                'content': f"""
                Here is the conversation history in XML format:
                {pipeline_result.get('history_xml', '')}
                
                Based on this history and the latest message, please provide a response.
                """
            }]
            
            return await self.llm_service.call_api(system_msg, messages)
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return None