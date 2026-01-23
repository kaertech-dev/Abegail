# attendance/attendance_handler.py - Main Attendance Handler
from typing import Dict
from datetime import date, time

try:
    from .attendance_db import AttendanceDB
    from .attendance_processor import AttendanceProcessor
    from .attendance_formatter import format_response
    from .attendance_config import DEFAULT_START_TIME
except ImportError:
    from attendance_db import AttendanceDB
    from attendance_processor import AttendanceProcessor
    from attendance_formatter import format_response
    from attendance_config import DEFAULT_START_TIME

class AttendanceHandler:
    """Main handler for attendance queries"""
    
    def __init__(self, host: str, user: str, password: str):
        self.db = AttendanceDB(host, user, password)
        self.processor = AttendanceProcessor(self.db)
    
    def is_present_today(self, employee_identifier: str, target_date: date = None) -> str:
        """Check if employee is present"""
        if target_date is None:
            target_date = date.today()
        
        result = self.processor.check_presence_today(employee_identifier, target_date)
        return format_response(result, 'presence_check')
    
    def get_attendance_by_date(self, target_date: date, 
                               employee_identifier: str = None) -> str:
        """Get attendance for a specific date"""
        result = self.processor.get_attendance_by_date(target_date, employee_identifier)
        return format_response(result, 'date_query')
    
    def get_attendance_range(self, start_date: date, end_date: date,
                            employee_identifier: str = None) -> str:
        """Get attendance for a date range"""
        result = self.processor.get_attendance_range(start_date, end_date, employee_identifier)
        return format_response(result, 'range_query')
    
    def count_present_operators(self, target_date: date, 
                               start_time: time = DEFAULT_START_TIME) -> str:
        """Count operators present"""
        result = self.processor.count_present_operators(target_date, start_time)
        return format_response(result, 'count_operators')
    
    def get_absent_employees(self, target_date: date) -> str:
        """Get list of absent employees"""
        result = self.processor.get_absent_employees(target_date)
        return format_response(result, 'absent')
    
    def get_latest_entries(self, limit: int = 10) -> str:
        """Get latest attendance entries"""
        result = self.processor.get_latest_entries(limit)
        return format_response(result, 'latest')