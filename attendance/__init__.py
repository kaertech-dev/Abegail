# attendance/__init__.py - Package Initialization
"""
Attendance Handler Package
Handles attendance tracking and queries
"""

try:
    from .attendance_handler import AttendanceHandler
except ImportError:
    from attendance_handler import AttendanceHandler

__all__ = ['AttendanceHandler']