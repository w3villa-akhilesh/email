import pytest
from dotenv import load_dotenv

def pytest_sessionstart(session):
    """
    Called after the Session object has been created and
    before performing test collection and execution.

    This hook is used to load environment variables from the .env file
    at the beginning of the test session, ensuring they are available
    for all tests, whether run from an IDE or a terminal.
    """
    load_dotenv() 