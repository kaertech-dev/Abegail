# activity_handler/__init__.py - Package Initialization
"""
Activity Handler Package
Handles activity monitoring queries and API interactions
"""

try:
    # Try relative imports
    from .activity_handler import (
        get_all_activities,
        get_activities_for_employee,
        get_activities_for_date,
        get_activities_for_range,
        get_activity_summary,
        is_activity_query,
        get_activity_handler
    )
except ImportError:
    # Fall back to absolute imports
    from activity_handler import (
        get_all_activities,
        get_activities_for_employee,
        get_activities_for_date,
        get_activities_for_range,
        get_activity_summary,
        is_activity_query,
        get_activity_handler
    )

__all__ = [
    'get_all_activities',
    'get_activities_for_employee',
    'get_activities_for_date',
    'get_activities_for_range',
    'get_activity_summary',
    'is_activity_query',
    'get_activity_handler'
]