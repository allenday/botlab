import pytest
from pathlib import Path
from botlab.message import Message
from botlab.history import MessageHistory

@pytest.fixture
def message_history():
    """Create a MessageHistory instance for testing"""
    return MessageHistory()

def test_add_message(message_history):
    """Test adding a message to history"""
    msg = Message(
        content="Test message",
        role="user",
        agent="testuser",
        chat_id=123,
        thread_id=None
    )
    message_history.add_message(msg)
    assert 123 in message_history.messages
    assert None in message_history.messages[123]
    assert len(message_history.messages[123][None]) == 1
    assert message_history.messages[123][None][0].role == "user"
    assert message_history.messages[123][None][0].content == "Test message"

def test_add_message_with_thread(message_history):
    """Test adding a message to a specific thread"""
    msg = Message(
        content="Thread message",
        role="user",
        agent="testuser",
        chat_id=123,
        thread_id=456
    )
    message_history.add_message(msg)
    assert 456 in message_history.messages[123]
    assert len(message_history.messages[123][456]) == 1

def test_get_thread_history_empty(message_history):
    """Test getting history for nonexistent thread"""
    history = message_history.get_thread_history(123, None)
    assert history == "<history></history>"

def test_get_thread_history(message_history):
    """Test getting thread history as XML"""
    msg1 = Message(
        content="First message",
        role="user",
        agent="testuser",
        chat_id=123
    )
    msg2 = Message(
        content="Second message",
        role="assistant",
        agent="testbot",
        chat_id=123
    )
    message_history.add_message(msg1)
    message_history.add_message(msg2)
    
    history = message_history.get_thread_history(123)
    assert '<message role="user" agent="testuser"' in history
    assert '<message role="assistant" agent="testbot"' in history
    assert "<content>First message</content>" in history
    assert "<content>Second message</content>" in history

def test_clear_history_thread(message_history):
    """Test clearing history for a specific thread"""
    msg = Message(
        content="Test",
        role="user",
        agent="testuser",
        chat_id=123,
        thread_id=456
    )
    message_history.add_message(msg)
    message_history.clear_history(123, 456)
    assert len(message_history.messages[123][456]) == 0

def test_clear_history_chat(message_history):
    """Test clearing all history for a chat"""
    msg1 = Message(
        content="Test 1",
        role="user",
        agent="testuser",
        chat_id=123,
        thread_id=456
    )
    msg2 = Message(
        content="Test 2",
        role="user",
        agent="testuser",
        chat_id=123,
        thread_id=789
    )
    message_history.add_message(msg1)
    message_history.add_message(msg2)
    message_history.clear_history(123)
    assert len(message_history.messages[123]) == 0 

def test_xml_special_characters(message_history):
    """Test handling of special characters in XML content"""
    special_content = 'Message with <tags> & "quotes" & \'apostrophes\''
    msg = Message(
        content=special_content,
        role="user",
        agent="testuser",
        chat_id=123
    )
    message_history.add_message(msg)
    
    history = message_history.get_thread_history(123)
    assert "&lt;tags&gt;" in history
    assert '"quotes"' in history
    assert "\'apostrophes\'" in history
    assert "&amp;" in history

def test_thread_isolation(message_history):
    """Test that histories are properly isolated by thread"""
    # Add messages to different threads
    msg1 = Message(
        content="Thread 1 Message",
        role="user",
        agent="testuser",
        chat_id=123,
        thread_id=1
    )
    msg2 = Message(
        content="Thread 2 Message",
        role="user",
        agent="testuser",
        chat_id=123,
        thread_id=2
    )
    message_history.add_message(msg1)
    message_history.add_message(msg2)
    
    # Check thread 1
    history1 = message_history.get_thread_history(123, 1)
    assert "Thread 1 Message" in history1
    assert "Thread 2 Message" not in history1
    
    # Check thread 2
    history2 = message_history.get_thread_history(123, 2)
    assert "Thread 2 Message" in history2
    assert "Thread 1 Message" not in history2 