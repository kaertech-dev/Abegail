# attendance/attendance_config.py - Configuration and Constants
from datetime import time

# Device location mapping
DEVICE_LOCATIONS = {
    '192.168.1.25': 'Building 6',
    '192.168.1.33': 'Canteen',
    '192.168.1.37': 'Lobby'
}

# Database configuration
DATABASE_NAME = 'attendance'
TABLE_NAME = 'raw'
LIST_TABLE = 'list'

# Default time thresholds
DEFAULT_START_TIME = time(7, 0)

# Column schema
COLUMNS = {
    'id': 'INT',
    'employee_num': 'VARCHAR',
    'employee_name': 'VARCHAR',
    'timestamp': 'DATETIME',
    'type': 'VARCHAR',
    'device_ip': 'VARCHAR',
    'created_at': 'DATETIME'
}

# Valid check-in types
CHECKIN_TYPES = ['time in', 'check in', 'clock in', 'in', 'Time In', 'Check In']

def get_device_location(device_ip: str) -> str:
    """Get location name from device IP"""
    return DEVICE_LOCATIONS.get(device_ip, device_ip)

def format_record_with_location(record: dict) -> dict:
    """Add location info to record"""
    record['location'] = get_device_location(record.get('device_ip', ''))
    return record