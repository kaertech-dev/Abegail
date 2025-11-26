# project_abegail/MCP/chatbot_ai/utils.py
"""
Utility functions and decorators
"""
import asyncio
from functools import wraps


def async_route(f):
    """
    Decorator to handle async routes in Flask
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper