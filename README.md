# BotLab

A Telegram bot framework for experimenting with LLM agents. BotLab provides a flexible XML-based configuration system for defining agent behaviors, conversation momentum, and interaction patterns.

## Features

- XML-based agent configuration
- Momentum-based conversation management
- Topic-based filtering
- Rate limiting and timing control
- Conversation history tracking
- DTD validation for configurations

## Installation

```bash
pip install -e ".[dev]"  # Install with development dependencies
# or
pip install -e .         # Install only runtime dependencies
```

## Configuration

1. Create a `.env` file with your API keys:
```env
ALLOWED_TOPIC_NAME=your_topic
ANTHROPIC_API_VERSION=2023-06-01
SPEAKER_MODEL=claude-3-sonnet-latest
INHIBITOR_MODEL=claude-3-haiku-latest
ANTHROPIC_API_KEY=your_key
TELEGRAM_TOKEN=your_token

SPEAKER_PROMPT_FILE=config/agents/odv.xml
INHIBITOR_PROMPT_FILE=config/agents/inhibitor.xml
```

2. Configure your agents in `config/agents/`:
- `odv.xml` - Main speaker agent configuration
- `inhibitor.xml` - Conversation flow control agent
- Additional agents as needed

## Usage

1. Start the bot:
```bash
python -m botlab.bot
```

2. Add the bot to a Telegram group

3. Create a topic named as specified in `ALLOWED_TOPIC_NAME`

4. Interact with the bot in the designated topic

## Development

Run tests:
```bash
pytest
```

## Project Structure

```
botlab/
├── src/
│   └── botlab/
│       ├── __init__.py
│       ├── bot.py
│       └── xml_handler.py
├── config/
│   ├── agents/
│   │   ├── odv.xml
│   │   └── inhibitor.xml
│   └── dtd/
│       ├── agent.dtd
│       └── messages.dtd
├── tests/
│   ├── integration/
│   │   └── test_bot.py
│   └── unit/
│       └── test_xml_handler.py
├── setup.py
└── README.md
```

## License

MIT License