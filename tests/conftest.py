import pytest
import logging

@pytest.fixture(autouse=True)
def setup_logging():
    """Set up logging for all tests"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ) 