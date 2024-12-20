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

// ... rest of the file unchanged ... 