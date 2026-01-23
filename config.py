# config.py - Configuration with Activity Monitoring Support
import os

# Database
DB_HOST = os.getenv('DB_HOST', '192.168.1.38')
DB_USER = os.getenv('DB_USER', 'labeling')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'labeling')

# Activity Monitoring API - FIXED: Correct IP and port
ACTIVITY_API_URL = os.getenv('ACTIVITY_API_URL', 'http://localhost/activity')

# Additional Activity API endpoints (for future use)
ACTIVITY_SUMMARY_URL = 'http://localhost/activity/summary'
ACTIVITY_EMPLOYEE_URL = 'http://localhost/activity/employee'

# AI Model
MODEL_NAME = "deepseek-r1:14b"

# Limits
AUTO_QUERY_DEFAULT_LIMIT = 100
SEARCH_DEFAULT_LIMIT = 50
SAMPLE_DATA_LIMIT = 3

# Database Keywords
DATABASE_KEYWORDS = {
    'schema_inspection': [
        'analyze database', 'database structure', 'show schema',
        'table details', 'what fields', 'what columns'
    ],
    'smart_search': [
        'search for', 'find in database', 'search database'
    ],
    'auto_query': [
        'show me all', 'get all', 'list all', 'show data'
    ],
    'table_operations': [
        'show tables', 'list tables', 'what tables', 'all tables'
    ],
    'attendance': [
        'attendance', 'present', 'absent', 'time in', 'time out',
        'clock in', 'clock out', 'check in', 'check out',
        'attendance record', 'attendance data', 'who is present',
        'who is absent', 'is present', 'is absent', 'was present',
        'was absent', 'attendance today', 'attendance yesterday',
        'attendance report', 'show attendance', 'get attendance',
        'list attendance', 'view attendance'
    ],
    'activity': [
        'activity', 'activities', 'monitoring',
        'what are they doing', 'what is doing', 'who is doing',
        'show activity', 'activity log', 'activity report',
        'activity data', 'activity for', 'activity summary',
        'all activities', 'recent activity', 'current activity',
        'activity monitoring', 'monitor activity', 'track activity'
    ]
}

# Attendance-specific settings
ATTENDANCE_DATABASE = 'attendance'
ATTENDANCE_TABLE = 'raw'
ATTENDANCE_DEFAULT_LIMIT = 100

# Date-related keywords
ATTENDANCE_DATE_KEYWORDS = [
    'today', 'yesterday', 'this week', 'last week',
    'this month', 'last month', 'last 7 days', 'past 7 days',
    'last 30 days', 'past 30 days', 'from', 'to', 'between'
]

# Employee ID patterns
EMPLOYEE_ID_PATTERN = r'\b(KE\d{4})\b'  # Matches KE0001, KE0152, etc.