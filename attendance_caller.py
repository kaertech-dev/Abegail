# attendance_caller.py - Convenience Functions for App
"""
This file provides simple functions that app.py can call.
It acts as a bridge to the attendance package.
"""

from datetime import date, time
from attendance import AttendanceHandler
from config import DB_HOST, DB_USER, DB_PASSWORD

# Singleton instance
_attendance_handler = None

def get_attendance_handler() -> AttendanceHandler:
    """Get singleton attendance handler"""
    global _attendance_handler
    if _attendance_handler is None:
        _attendance_handler = AttendanceHandler(DB_HOST, DB_USER, DB_PASSWORD)
    return _attendance_handler

# Convenience functions for app.py

def check_employee_presence(employee_identifier: str, target_date: date = None) -> str:
    """Check if employee is present"""
    handler = get_attendance_handler()
    return handler.is_present_today(employee_identifier, target_date)

def get_attendance_for_date(target_date: date, employee_name: str = None) -> str:
    """Get attendance for a specific date"""
    handler = get_attendance_handler()
    return handler.get_attendance_by_date(target_date, employee_name)

def get_attendance_for_range(start_date: date, end_date: date, employee_name: str = None) -> str:
    """Get attendance for a date range"""
    handler = get_attendance_handler()
    return handler.get_attendance_range(start_date, end_date, employee_name)

def count_operators_present(target_date: date, start_time: time) -> str:
    """Count operators present after a specific time"""
    handler = get_attendance_handler()
    return handler.count_present_operators(target_date, start_time)

def get_absent_employees_for_date(target_date: date) -> str:
    """Get list of absent employees"""
    handler = get_attendance_handler()
    return handler.get_absent_employees(target_date)

def get_latest_attendance_entries(limit: int = 20) -> str:
    """Get latest attendance entries for debugging"""
    handler = get_attendance_handler()
    return handler.get_latest_entries(limit)