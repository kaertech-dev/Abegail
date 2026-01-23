# ledtech/__init__.py - Ledtech Module Initialization
"""
Ledtech Database Handler Module

This module provides specialized handlers for various tables in the ledtech database.
Each table has its own handler module with specific query functions.

Available modules:
- burnin: Handle burninboard_depanel table queries
"""

from .burnin import (
    get_burnin_handler,
    search_burnin_serial,
    search_burnin_po,
    search_burnin_operator,
    search_burnin_shift,
    get_burnin_by_date,
    get_burnin_statistics
)

__all__ = [
    'get_burnin_handler',
    'search_burnin_serial',
    'search_burnin_po',
    'search_burnin_operator',
    'search_burnin_shift',
    'get_burnin_by_date',
    'get_burnin_statistics'
]

__version__ = '1.0.0'