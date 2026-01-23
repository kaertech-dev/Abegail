# attendance_routes.py - Attendance Query Handler
from typing import Dict, Optional
from datetime import date, time
from attendance_caller import (
    check_employee_presence,
    get_attendance_for_date,
    get_attendance_for_range,
    count_operators_present,
    get_latest_attendance_entries,
    get_absent_employees_for_date
)
from query_processor import (
    is_attendance_query,
    is_operator_count_query,
    extract_employee_name
)
from date_filter import parse_date_from_message

def handle_attendance_query(message: str) -> Optional[Dict[str, str]]:
    """
    Handle attendance queries
    Returns: dict with 'answer' and 'response_type', or None if not an attendance query
    """
    if not is_attendance_query(message):
        return None
    
    msg_lower = message.lower()
    
    # Check for debug/latest entries command
    if 'latest' in msg_lower and ('entries' in msg_lower or 'attendance' in msg_lower):
        return {
            'answer': get_latest_attendance_entries(20),
            'response_type': 'attendance_debug'
        }
    
    # Check for operator count query
    if is_operator_count_query(message):
        date_info = parse_date_from_message(message)
        target_date = date_info['start_date'] if date_info else date.today()
        
        return {
            'answer': count_operators_present(target_date, time(7, 0)),
            'response_type': 'attendance_count'
        }
    
    # Check for absent employees query
    if any(word in msg_lower for word in ['absent', 'who is absent', 'not present']):
        date_info = parse_date_from_message(message)
        target_date = date_info['start_date'] if date_info else date.today()
        
        return {
            'answer': get_absent_employees_for_date(target_date),
            'response_type': 'attendance_absent'
        }
    
    # Check for "is [name] present" queries
    if any(word in msg_lower for word in ['is', 'are', 'was', 'were']) and \
       any(word in msg_lower for word in ['present', 'here', 'in', 'absent']):
        employee_name = extract_employee_name(message)
        
        if not employee_name:
            return {
                'answer': "❓ Please specify an employee name or ID.\n\nExample: \"is Ryan present today?\" or \"is KE0152 present?\"",
                'response_type': 'attendance_help'
            }
        
        date_info = parse_date_from_message(message)
        
        if date_info:
            if date_info['start_date'] != date_info['end_date']:
                answer = get_attendance_for_range(
                    date_info['start_date'],
                    date_info['end_date'],
                    employee_name
                )
            else:
                answer = get_attendance_for_date(
                    date_info['start_date'],
                    employee_name
                )
            response_type = 'attendance'
        else:
            answer = check_employee_presence(employee_name)
            response_type = 'attendance_presence'
        
        return {'answer': answer, 'response_type': response_type}
    
    # General attendance query with date/range
    date_info = parse_date_from_message(message)
    employee_name = extract_employee_name(message)
    
    if not date_info:
        date_info = {
            'type': 'today',
            'start_date': date.today(),
            'end_date': date.today(),
            'description': 'today'
        }
    
    if date_info['start_date'] != date_info['end_date']:
        answer = get_attendance_for_range(
            date_info['start_date'],
            date_info['end_date'],
            employee_name
        )
    else:
        answer = get_attendance_for_date(
            date_info['start_date'],
            employee_name
        )
    
    return {'answer': answer, 'response_type': 'attendance'}