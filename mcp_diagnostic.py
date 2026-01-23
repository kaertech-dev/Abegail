#!/usr/bin/env python3
"""
MCP Attendance Debug & Test Script
Run this to diagnose MCP server issues
"""

import sys
import os
import subprocess
import mysql.connector
from datetime import date

print("="*70)
print("🔍 MCP Attendance Server - Diagnostic Tool")
print("="*70)

# Test 1: Check if files exist
print("\n📁 Test 1: Checking required files...")
files_to_check = [
    'mcp_attendance_server.py',
    'mcp_attendance_client.py',
]

for file in files_to_check:
    if os.path.exists(file):
        print(f"   ✅ {file} - Found")
    else:
        print(f"   ❌ {file} - NOT FOUND")
        print(f"      Location checked: {os.path.abspath(file)}")

# Test 2: Check Python packages
print("\n📦 Test 2: Checking Python packages...")
required_packages = {
    'mcp': 'MCP SDK',
    'mysql.connector': 'MySQL Connector',
    'flask': 'Flask',
    'flask_cors': 'Flask-CORS'
}

for package, name in required_packages.items():
    try:
        __import__(package)
        print(f"   ✅ {name} - Installed")
    except ImportError:
        print(f"   ❌ {name} - NOT INSTALLED")
        if package == 'mysql.connector':
            print(f"      Install with: pip install mysql-connector-python")
        elif package == 'mcp':
            print(f"      Install with: pip install mcp")
        else:
            print(f"      Install with: pip install {package.replace('_', '-')}")

# Test 3: Test database connection
print("\n🗄️  Test 3: Testing database connection...")
DB_CONFIG = {
    'host': '192.168.1.38',
    'user': 'labeling',
    'password': 'labeling',
    'database': 'attendance'
}

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    print(f"   ✅ Database connection successful")
    
    # Test if tables exist
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [table[0] for table in cursor.fetchall()]
    print(f"   📊 Found tables: {', '.join(tables)}")
    
    # Test raw table
    if 'raw' in tables:
        cursor.execute("SELECT COUNT(*) FROM `raw`")
        count = cursor.fetchone()[0]
        print(f"   📝 Records in 'raw' table: {count:,}")
        
        # Get sample record
        cursor.execute("SELECT * FROM `raw` ORDER BY `timestamp` DESC LIMIT 1")
        sample = cursor.fetchone()
        if sample:
            print(f"   📄 Latest record exists: {sample[1] if len(sample) > 1 else 'N/A'}")
    
    # Test list table
    if 'list' in tables:
        cursor.execute("SELECT COUNT(*) FROM `list`")
        count = cursor.fetchone()[0]
        print(f"   👥 Employees in 'list' table: {count:,}")
    
    cursor.close()
    conn.close()
    
except mysql.connector.Error as e:
    print(f"   ❌ Database connection failed: {e}")
    print(f"      Check your database credentials and network connection")

# Test 4: Try to run MCP server directly
print("\n🚀 Test 4: Testing MCP server startup...")
if os.path.exists('mcp_attendance_server.py'):
    try:
        print("   Attempting to start MCP server...")
        print("   (This should run for 3 seconds then stop)")
        
        # Try to run the server with a timeout
        process = subprocess.Popen(
            [sys.executable, 'mcp_attendance_server.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            stdout, stderr = process.communicate(timeout=3)
            print(f"   ⚠️  Server exited immediately")
            if stdout:
                print(f"   📝 STDOUT: {stdout[:200]}")
            if stderr:
                print(f"   ❌ STDERR: {stderr[:200]}")
        except subprocess.TimeoutExpired:
            process.kill()
            print(f"   ✅ Server started successfully (killed after 3 seconds)")
            
    except Exception as e:
        print(f"   ❌ Failed to start server: {e}")
else:
    print("   ❌ mcp_attendance_server.py not found")

# Test 5: Test MCP client import
print("\n🔌 Test 5: Testing MCP client import...")
try:
    from mcp_attendance_client import get_attendance_service, detect_attendance_query
    print("   ✅ MCP client imports successfully")
    
    # Test query detection
    test_queries = [
        "is Ryan present today?",
        "how many operators are present?",
        "show attendance"
    ]
    
    print("   🧪 Testing query detection:")
    for query in test_queries:
        result = detect_attendance_query(query)
        if result:
            print(f"      ✅ '{query}' -> {result['type']}")
        else:
            print(f"      ❌ '{query}' -> Not detected")
            
except ImportError as e:
    print(f"   ❌ Failed to import MCP client: {e}")
except Exception as e:
    print(f"   ❌ Error testing client: {e}")

# Test 6: Direct database query test (bypass MCP)
print("\n🔬 Test 6: Direct database query test...")
try:
    from attendance.attendance_db import AttendanceDB
    from attendance.attendance_config import DB_CONFIG as OLD_CONFIG
    
    print("   ℹ️  Testing with OLD attendance system (non-MCP)")
    
    # You can use your existing attendance system
    print("   ✅ Old attendance system available as fallback")
    
except ImportError as e:
    print(f"   ⚠️  Old attendance system not available: {e}")

# Summary and recommendations
print("\n" + "="*70)
print("📋 DIAGNOSIS SUMMARY")
print("="*70)

print("""
🔧 Common Issues & Solutions:

1. ❌ MCP package not installed:
   Solution: pip install mcp

2. ❌ Database connection failed:
   Solution: Check credentials in mcp_attendance_server.py
   - Host: 192.168.1.38
   - User: labeling
   - Password: labeling
   - Database: attendance

3. ❌ Files not found:
   Solution: Make sure you're in the correct directory
   - mcp_attendance_server.py should be in project root
   - mcp_attendance_client.py should be in project root

4. ❌ Server exits immediately:
   Solution: The MCP server needs to be called via stdio
   - It's designed to be spawned by the client
   - Don't run it directly in production

5. ⚠️  Connection closed error:
   Solution: This usually means Python path issues
   - Try: python -m mcp_attendance_server
   - Or use absolute path in client

📝 Next Steps:
1. Fix any ❌ issues shown above
2. Run this script again to verify fixes
3. Try the simple test below
""")

print("\n🧪 SIMPLE CLIENT TEST")
print("="*70)
print("""
Run this in Python to test the client directly:

from mcp_attendance_client import get_attendance_service

try:
    service = get_attendance_service()
    result = service.get_latest_entries(5)
    print("✅ SUCCESS!")
    print(result[:200])
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
""")

print("\n" + "="*70)
print("✨ Diagnostic complete!")
print("="*70)