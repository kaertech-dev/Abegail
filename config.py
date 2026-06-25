# config.py - Configuration with Activity Monitoring Support
import os

# Database
DB_HOST = os.getenv('DB_HOST', '192.168.1.38')
DB_USER = os.getenv('DB_USER', 'readonly_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'kts@tsd2025')

DB_CONFIG = {
    'host': DB_HOST,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': '',
    'autocommit': True,
    'use_unicode': True,
    'charset': 'utf8mb4'
}

# Activity/Productivity Monitoring API
ACTIVITY_API_URL = os.getenv('ACTIVITY_API_URL', 'http://192.168.20.200/activity/api/operator_today')
PRODUCTIVITY_API = os.getenv('PRODUCTIVITY_API', 'http://192.168.20.200/productivity/api/operator_today')

# Limits
AUTO_QUERY_DEFAULT_LIMIT = 100
SEARCH_DEFAULT_LIMIT = 50
SAMPLE_DATA_LIMIT = 3

# Attendance
DEVICE_LOCATIONS = {
    '192.168.1.25': 'Building 6',
    '192.168.1.33': 'Canteen',
    '192.168.1.37': 'Lobby'
}

CHECKIN_TYPES = ['time in', 'check in', 'clock in', 'in', 'Time In', 'Check In']