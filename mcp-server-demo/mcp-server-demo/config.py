# config.py - Streamlined Configuration
import os

# Database
DB_HOST = os.getenv('DB_HOST', '192.168.1.38')
DB_USER = os.getenv('DB_USER', 'labeling')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'labeling')

# AI Model
MODEL_NAME = "deepseek-r1:1.5b"

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
    ]
}