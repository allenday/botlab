"""BotLab - A Telegram bot framework for experimenting with LLM agents."""

from .xml_handler import (
    load_agent_config, 
    AgentConfig,
    Message,  # Export Message directly
    MomentumSequence
)
from .bot import Bot

__all__ = ['Bot', 'load_agent_config', 'AgentConfig', 'Message', 'MomentumSequence']

__version__ = "0.1.0" 