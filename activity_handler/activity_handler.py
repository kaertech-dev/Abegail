# activity_handler.py - Main Activity Handler (Refactored)
from typing import Optional, Dict
from datetime import date

try:
    # Try relative import (when used as package)
    from .activity_api import ActivityAPI
    from .activity_formatter import format_activity_response, format_activity_summary
except ImportError:
    # Fall back to absolute import (when used standalone)
    from activity_api import ActivityAPI
    from activity_formatter import format_activity_response, format_activity_summary

class ActivityHandler:
    """Main handler for activity monitoring queries"""
    
    def __init__(self, api_url: Optional[str] = None):
        self.api = ActivityAPI(api_url)
    
    def get_all_activities(self) -> str:
        """Get all activities from API"""
        result = self.api.fetch_activity_data()
        return format_activity_response(result, 'general')
    
    def get_activities_for_employee(self, employee_name: str) -> str:
        """Get activities for specific employee"""
        result = self.api.fetch_activity_data()
        
        if result['success']:
            filters = {'employee_name': employee_name}
            return format_activity_response(result, 'employee', filters)
        else:
            return format_activity_response(result, 'employee')
    
    def get_activities_for_date(self, target_date: date) -> str:
        """Get activities for specific date"""
        result = self.api.fetch_activity_data()
        
        if result['success']:
            filters = {'date': target_date}
            return format_activity_response(result, 'date', filters)
        else:
            return format_activity_response(result, 'date')
    
    def get_activities_for_range(self, start_date: date, end_date: date) -> str:
        """Get activities for date range"""
        result = self.api.fetch_activity_data()
        
        if result['success']:
            filters = {'start_date': start_date, 'end_date': end_date}
            return format_activity_response(result, 'range', filters)
        else:
            return format_activity_response(result, 'range')
    
    def get_activity_summary(self) -> str:
        """Get activity summary"""
        result = self.api.fetch_activity_data()
        return format_activity_summary(result)

# Singleton instance
_activity_handler = None

def get_activity_handler():
    """Get singleton activity handler"""
    global _activity_handler
    if _activity_handler is None:
        _activity_handler = ActivityHandler()
    return _activity_handler

# Convenience functions for use in app.py

def get_all_activities() -> str:
    """Get all activities from API"""
    return get_activity_handler().get_all_activities()

def get_activities_for_employee(employee_name: str) -> str:
    """Get activities for specific employee"""
    return get_activity_handler().get_activities_for_employee(employee_name)

def get_activities_for_date(target_date: date) -> str:
    """Get activities for specific date"""
    return get_activity_handler().get_activities_for_date(target_date)

def get_activities_for_range(start_date: date, end_date: date) -> str:
    """Get activities for date range"""
    return get_activity_handler().get_activities_for_range(start_date, end_date)

def get_activity_summary() -> str:
    """Get activity summary"""
    return get_activity_handler().get_activity_summary()

def is_activity_query(message: str) -> bool:
    """Check if message is an activity monitoring query"""
    msg_lower = message.lower()
    activity_keywords = [
        'activity', 'activities', 'monitoring',
        'what are they doing', 'what is', 'who is doing',
        'show activity', 'activity log', 'activity report',
        'activity data', 'activity for','show activities for','show activities',
        'can you show activity', 'I want to see activity',
        'can you show activity today?','what is the activity?'
    ]
    return any(keyword in msg_lower for keyword in activity_keywords)