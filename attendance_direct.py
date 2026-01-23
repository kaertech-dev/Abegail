# attendance_direct.py - Direct attendance handler (fallback without MCP)
"""
This is a direct implementation that doesn't use MCP.
Use this as a fallback if MCP has issues.
"""

from datetime import date, time, datetime, timedelta
from typing import Optional, Dict, List
import re

# Import your existing attendance system
try:
    from attendance.attendance_db import AttendanceDB
    from attendance.attendance_processor import AttendanceProcessor
    from attendance.attendance_formatter import format_response
    from config import DB_HOST, DB_USER, DB_PASSWORD
    ATTENDANCE_AVAILABLE = True
except ImportError:
    ATTENDANCE_AVAILABLE = False
    print("⚠️  Warning: Attendance module not available")


class DirectAttendanceHandler:
    """Direct attendance handler without MCP"""
    
    def __init__(self):
        if not ATTENDANCE_AVAILABLE:
            raise ImportError("Attendance modules not available")
        
        self.db = AttendanceDB(DB_HOST, DB_USER, DB_PASSWORD)
        self.processor = AttendanceProcessor(self.db)
    
    def check_presence(self, employee_identifier: str, target_date: date = None) -> str:
        """Check if employee is present"""
        if target_date is None:
            target_date = date.today()
        
        result = self.processor.check_presence_today(employee_identifier, target_date)
        return format_response(result, 'presence_check')
    
    def check_attendance(self, target_date: date = None, employee_identifier: str = None) -> str:
        """Check attendance for date"""
        if target_date is None:
            target_date = date.today()
        
        result = self.processor.get_attendance_by_date(target_date, employee_identifier)
        return format_response(result, 'date_query')
    
    def get_attendance_range(self, start_date: date, end_date: date, 
                            employee_identifier: str = None) -> str:
        """Get attendance for date range"""
        result = self.processor.get_attendance_range(start_date, end_date, employee_identifier)
        return format_response(result, 'range_query')
    
    def count_present_operators(self, target_date: date = None, 
                               start_time: time = time(7, 0)) -> str:
        """Count present operators"""
        if target_date is None:
            target_date = date.today()
        
        result = self.processor.count_present_operators(target_date, start_time)
        return format_response(result, 'count_operators')
    
    def get_absent_employees(self, target_date: date = None) -> str:
        """Get absent employees"""
        if target_date is None:
            target_date = date.today()
        
        result = self.processor.get_absent_employees(target_date)
        return format_response(result, 'absent')
    
    def get_latest_entries(self, limit: int = 10) -> str:
        """Get latest entries"""
        result = self.processor.get_latest_entries(limit)
        return format_response(result, 'latest')


# Singleton
_direct_handler = None

def get_direct_handler() -> Optional[DirectAttendanceHandler]:
    """Get direct handler instance"""
    global _direct_handler
    if not ATTENDANCE_AVAILABLE:
        return None
    
    if _direct_handler is None:
        try:
            _direct_handler = DirectAttendanceHandler()
        except Exception as e:
            print(f"❌ Failed to initialize direct handler: {e}")
            return None
    
    return _direct_handler


def detect_attendance_query(message: str) -> Optional[Dict]:
    """Detect attendance queries"""
    msg_lower = message.lower()
    
    # Check for attendance keywords
    attendance_keywords = [
        'attendance', 'present', 'absent', 'time in', 'clock in',
        'check in', 'who is here', 'who is in', 'attendance record'
    ]
    
    if not any(keyword in msg_lower for keyword in attendance_keywords):
        return None
    
    query_info = {'type': None, 'params': {}}
    
    # 1. Presence check
    presence_patterns = [
        r'is\s+(\w+)\s+(?:present|here)',
        r'is\s+(KE\d{4})\s+(?:present|here)',
        r'check\s+(\w+)(?:\'s)?\s+attendance',
    ]
    
    for pattern in presence_patterns:
        match = re.search(pattern, msg_lower, re.IGNORECASE)
        if match:
            query_info['type'] = 'presence_check'
            query_info['params']['employee_identifier'] = match.group(1)
            break
    
    # 2. Operator count
    if re.search(r'how many.*(?:operator|employee|people)', msg_lower):
        query_info['type'] = 'count_operators'
    
    # 3. Absent employees
    if 'absent' in msg_lower or 'not present' in msg_lower:
        if not query_info['type']:
            query_info['type'] = 'absent_list'
    
    # 4. Latest entries
    if 'latest' in msg_lower or 'recent' in msg_lower:
        query_info['type'] = 'latest_entries'
    
    # 5. General attendance
    if not query_info['type']:
        query_info['type'] = 'general_attendance'
    
    # Extract date
    today = date.today()
    
    if 'today' in msg_lower:
        query_info['params']['date'] = today
    elif 'yesterday' in msg_lower:
        query_info['params']['date'] = today - timedelta(days=1)
    elif 'last week' in msg_lower:
        query_info['params']['start_date'] = today - timedelta(days=7)
        query_info['params']['end_date'] = today
        query_info['type'] = 'attendance_range'
    elif match := re.search(r'last\s+(\d+)\s+days?', msg_lower):
        days = int(match.group(1))
        query_info['params']['start_date'] = today - timedelta(days=days)
        query_info['params']['end_date'] = today
        query_info['type'] = 'attendance_range'
    
    # Extract employee name/ID
    if 'employee_identifier' not in query_info['params']:
        id_match = re.search(r'\b(KE\d{4})\b', message, re.IGNORECASE)
        if id_match:
            query_info['params']['employee_identifier'] = id_match.group(1).upper()
        else:
            name_patterns = [
                r'for\s+(\w+)',
                r'of\s+(\w+)',
                r'attendance\s+(\w+)',
            ]
            for pattern in name_patterns:
                match = re.search(pattern, msg_lower)
                if match and match.group(1) not in ['today', 'yesterday', 'the', 'all']:
                    query_info['params']['employee_identifier'] = match.group(1).title()
                    break
    
    return query_info if query_info['type'] else None


def handle_attendance_query_direct(message: str) -> Optional[str]:
    """Handle attendance query directly (no MCP)"""
    query_info = detect_attendance_query(message)
    
    if not query_info:
        return None
    
    handler = get_direct_handler()
    if not handler:
        return "❌ Attendance system not available"
    
    try:
        query_type = query_info['type']
        params = query_info['params']
        
        if query_type == 'presence_check':
            return handler.check_presence(
                params['employee_identifier'],
                params.get('date')
            )
        
        elif query_type == 'count_operators':
            return handler.count_present_operators(
                params.get('date'),
                params.get('start_time', time(7, 0))
            )
        
        elif query_type == 'absent_list':
            return handler.get_absent_employees(params.get('date'))
        
        elif query_type == 'latest_entries':
            return handler.get_latest_entries(params.get('limit', 10))
        
        elif query_type == 'attendance_range':
            return handler.get_attendance_range(
                params['start_date'],
                params['end_date'],
                params.get('employee_identifier')
            )
        
        elif query_type == 'general_attendance':
            return handler.check_attendance(
                params.get('date'),
                params.get('employee_identifier')
            )
        
        return None
        
    except Exception as e:
        return f"❌ **Attendance Error:** {str(e)}"