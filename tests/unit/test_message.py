import pytest
from datetime import datetime
from botlab.message import Message

def test_message_creation():
    msg = Message(
        role="user",
        content="test message",
        agent="testuser",
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
        channel="general",
        message_id=1,
        timestamp="2024-03-15T12:00:00"
    )
    xml = msg.to_xml()
    assert '<message ' in xml
    assert 'timestamp="2024-03-15T12:00:00"' in xml
    assert 'channel="general"' in xml
    assert 'id="1"' in xml 