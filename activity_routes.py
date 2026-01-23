# activity_routes.py - Activity Query Handler
from typing import Dict, Optional
from datetime import date
from activity_handler import (
    get_all_activities,
    get_activities_for_employee,
    get_activities_for_date,
    get_activities_for_range,
    get_activity_summary,
    is_activity_query
)
from query_processor import extract_employee_name
from date_filter import parse_date_from_message

def handle_activity_query(message: str) -> Optional[Dict[str, str]]:
    """
    Handle activity monitoring queries
    Returns: dict with 'answer' and 'response_type'
    """
    if not is_activity_query(message):
        return None
    
    msg_lower = message.lower()
    
    # Check for summary request
    if 'summary' in msg_lower:
        return {
            'answer': get_activity_summary(),
            'response_type': 'activity_summary'
        }
    
    # Check for employee-specific activity
    if any(word in msg_lower for word in ['activity for', 'activities for', 'what is', 'what are']):
        employee_name = extract_employee_name(message)
        
        if employee_name:
            return {
                'answer': get_activities_for_employee(employee_name),
                'response_type': 'activity_employee'
            }
        else:
            return {
                'answer': "❓ Please specify an employee name.\n\nExample: \"show activities for Ryan\" or \"what is KE0152 doing?\"",
                'response_type': 'activity_help'
            }
    
    # Check for date-based activity queries
    date_info = parse_date_from_message(message)
    
    if date_info:
        # Date range query
        if date_info['start_date'] != date_info['end_date']:
            answer = get_activities_for_range(
                date_info['start_date'],
                date_info['end_date']
            )
        else:
            answer = get_activities_for_date(date_info['start_date'])
        
        return {
            'answer': answer,
            'response_type': 'activity_date'
        }
    
    # General activity query
    return {
        'answer': get_all_activities(),
        'response_type': 'activity_general'
    }