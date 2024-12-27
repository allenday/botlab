import pytest
from datetime import datetime
from botlab.message import Message

def test_message_creation():
    msg = Message(
        role="user",
        content="test message",
        agent="testuser",
        chat_id=123,
        message_id=1
    )
    assert msg.role == "user"
    assert msg.content == "test message"
    assert msg.agent == "testuser"
    assert msg.message_id == 1

def test_message_to_xml():
    msg = Message(
        role="user",
        content="test",
        agent="testuser",
        chat_id=123,
        message_id=1,
        timestamp="2024-03-15T12:00:00"
    )
    xml = msg.to_xml()
    assert '<message ' in xml
    assert 'timestamp="2024-03-15T12:00:00"' in xml
    assert 'chat_id="123"' in xml
    assert 'id="1"' in xml

def test_message_with_reply():
    msg = Message(
        role="user",
        content="test reply",
        agent="testuser",
        chat_id=123,
        message_id=2,
        reply_to_message_id=1,
        reply_to_thread_id=456
    )
    xml = msg.to_xml()
    assert 'reply_to="1"' in xml
    assert 'reply_to_thread_id="456"' in xml

def test_timestamp_auto_generation():
    msg = Message(
        role="user",
        content="test",
        agent="testuser",
        chat_id=123
    )
    assert msg.timestamp is not None
    # Verify timestamp format
    datetime.strptime(msg.timestamp, "%Y-%m-%dT%H:%M:%S") 