#!/usr/bin/env python3
"""
Attendance MCP Server
Provides attendance tracking and querying capabilities via MCP protocol
"""

import asyncio
import json
import csv
from datetime import datetime, date, time, timedelta
from typing import Any, List, Dict, Optional
import mysql.connector
from mysql.connector import Error

# MCP SDK imports
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

# ==================== CONFIGURATION ====================

DB_CONFIG = {
    'host': '192.168.1.38',
    'user': 'labeling',
    'password': 'labeling',
    'database': 'attendance',
    'autocommit': True,
    'use_unicode': True,
    'charset': 'utf8mb4'
}

DEVICE_LOCATIONS = {
    '192.168.1.25': 'Building 6',
    '192.168.1.33': 'Canteen',
    '192.168.1.37': 'Lobby'
}

CHECKIN_TYPES = ['time in', 'check in', 'clock in', 'in', 'Time In', 'Check In']

path_name = './csv_files/'

# ==================== DATABASE HANDLER ====================

class AttendanceDB:
    """Handle attendance database operations"""
    
    def __init__(self):
        self.config = DB_CONFIG
    
    def connect(self):
        """Create database connection"""
        try:
            return mysql.connector.connect(**self.config)
        except Error as e:
            raise Exception(f"Database connection error: {e}")
    
    def get_records_by_date(self, target_date: date, employee_identifier: str = None) -> List[Dict]:
        """Get attendance records for a specific date"""
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            
            if employee_identifier:
                query = """
                    SELECT * FROM `raw` 
                    WHERE DATE(`timestamp`) = %s 
                    AND (
                        `employee_name` LIKE %s 
                        OR `employee_num` LIKE %s
                    )
                    ORDER BY `timestamp` ASC
                """
                search_pattern = f"%{employee_identifier}%"
                cursor.execute(query, (target_date, search_pattern, search_pattern))
            else:
                query = "SELECT * FROM `raw` WHERE DATE(`timestamp`) = %s ORDER BY `timestamp` ASC"
                cursor.execute(query, (target_date,))
            
            records = cursor.fetchall()
            return self._add_locations(records)
            
        finally:
            cursor.close()
            conn.close()
    
    def get_records_by_range(self, start_date: date, end_date: date, 
                            employee_identifier: str = None) -> List[Dict]:
        """Get attendance records for date range"""
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            
            if employee_identifier:
                query = """
                    SELECT * FROM `raw` 
                    WHERE DATE(`timestamp`) BETWEEN %s AND %s 
                    AND (
                        `employee_name` LIKE %s 
                        OR `employee_num` LIKE %s
                    )
                    ORDER BY `timestamp` ASC
                """
                search_pattern = f"%{employee_identifier}%"
                cursor.execute(query, (start_date, end_date, search_pattern, search_pattern))
            else:
                query = """
                    SELECT * FROM `raw` 
                    WHERE DATE(`timestamp`) BETWEEN %s AND %s 
                    ORDER BY `timestamp` ASC
                """
                cursor.execute(query, (start_date, end_date))
            
            records = cursor.fetchall()
            return self._add_locations(records)
            
        finally:
            cursor.close()
            conn.close()
    
    def get_operators_present(self, target_date: date, start_time: time) -> List[Dict]:
        """Get operators who clocked in after specific time"""
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT DISTINCT r1.`employee_name`, r1.`employee_num`, MIN(r1.`timestamp`) as first_entry,
                       (SELECT `device_ip` FROM `raw` r2 
                        WHERE r2.`employee_num` = r1.`employee_num` 
                        AND DATE(r2.`timestamp`) = %s
                        AND TIME(r2.`timestamp`) <= %s
                        ORDER BY r2.`timestamp` ASC LIMIT 1) as device_ip
                FROM `raw` r1
                INNER JOIN `list` t2 ON r1.employee_name = t2.employee_name
                WHERE t2.job_title LIKE '%Operator%'
                AND DATE(`timestamp`) = %s
                AND TIME(`timestamp`) <= %s
                GROUP BY `employee_name`, `employee_num`
                ORDER BY first_entry ASC
            """
            
            params = (target_date, start_time, target_date, start_time)
            cursor.execute(query, params)
            operators = cursor.fetchall()
            return self._add_locations(operators)
            
        finally:
            cursor.close()
            conn.close()
    
    def get_all_employees(self, dept: Optional[str]) -> List[Dict]:
        """Get all employees from list"""
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            if dept is None: # all departments
                cursor.execute("""
                    SELECT DISTINCT employee_name, employee_num
                    FROM `list`
                    ORDER BY employee_name
                """)
            else:
                cursor.execute("""
                    SELECT DISTINCT employee_name, employee_num
                    FROM `list`
                    WHERE `department` LIKE %s
                    ORDER BY employee_name
                """, (f'%{dept}%',))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    
    def get_present_employees(self, target_date: date, start_time: Optional[time], dept: Optional[str]) -> List[Dict]:
        """Get employees present on date"""
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            if start_time is None:
                start_time = time(7, 0)
            if dept is None: # get all departments
                cursor.execute("""
                    SELECT DISTINCT employee_name, employee_num
                    FROM `raw`
                    WHERE DATE(`timestamp`) = %s
                    AND TIME(`timestamp`) <= %s
                """, (target_date, start_time))
            else:
                cursor.execute("""
                    SELECT DISTINCT t1.employee_name, t1.employee_num, t2.department
                    FROM `raw` t1
                    INNER JOIN `list` t2 ON t1.employee_num = t2.employee_num
                    WHERE t2.department LIKE %s
                    AND DATE(t1.`timestamp`) = %s
                    AND TIME(t1.`timestamp`) <= %s
                    ORDER BY employee_name
                """, (f'%{dept}%', target_date, start_time,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    
    def get_latest_entries(self, start_time: Optional[str], end_time: Optional[str], where: str = 'last', limit: int = 10) -> List[Dict]:
        """Get latest attendance entries"""
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            if where == 'last':
                query = """
                    SELECT * FROM `raw` 
                    ORDER BY `timestamp` DESC 
                    LIMIT %s
                """
                cursor.execute(query, (limit,))
            elif where == 'first':
                today = date.today().isoformat()
                query = """
                    SELECT * FROM `raw` 
                    WHERE DATE(timestamp) LIKE %s
                    ORDER BY `timestamp` ASC 
                    LIMIT %s
                """
                cursor.execute(query, (today, limit,))
            elif where == 'middle':
                today = date.today().isoformat()
                query = """
                    SELECT * FROM `raw` 
                    WHERE DATE(timestamp) LIKE %s
                    AND TIME(`timestamp`) BETWEEN %s AND %s
                    ORDER BY `timestamp` ASC
                    LIMIT 30
                """
                cursor.execute(query, (today, start_time, end_time,))
            
            records = cursor.fetchall()
            return self._add_locations(records)
        finally:
            cursor.close()
            conn.close()
    
    def _add_locations(self, records: List[Dict]) -> List[Dict]:
        """Add location info to records"""
        for record in records:
            device_ip = record.get('device_ip', '')
            record['location'] = DEVICE_LOCATIONS.get(device_ip, device_ip)
        return records

# ==================== UTILITY FUNCTIONS ====================
departments = ['Top Management',
               'Manufacturing', 'Quality Regulatory Affairs & EHS',
               'Business Development', 'HR & Admin',
               'Supply Chain Management', 'Facilities & Maintenance',
               'Information Technology', 'Research & Development',
               'Accounting', 'Finance & Administration']

def parse_date_string(date_str: str) -> Optional[date]:
    """Parse date string to date object"""
    try:
        return date.fromisoformat(date_str)
    except:
        return None

def parse_time_string(time_str: str) -> Optional[time]:
    """Parse time string to time object"""
    try:
        return time.fromisoformat(time_str)
    except:
        return None

def format_attendance_record(record: Dict) -> str:
    """Format a single attendance record"""
    ts = record.get('timestamp', '')
    if isinstance(ts, datetime):
        ts = ts.strftime('%Y-%m-%d %I:%M %p')
    
    return (f"**{record.get('employee_name')}** ({record.get('employee_num')})\n"
            f"   - Time: {ts}\n"
            # f"   - Type: {record.get('type')}\n"
            f"   - Location: 📍 {record.get('location')}\n")

def format_presence_summary(records: List[Dict], employee_id: str, target_date: date) -> str:
    """Format presence check summary"""
    if not records:
        return f"❌ **{employee_id}** was **NOT PRESENT** on {target_date}"
    
    # Group by employee
    by_employee = {}
    for record in records:
        key = f"{record['employee_name']} ({record['employee_num']})"
        if key not in by_employee:
            by_employee[key] = []
        by_employee[key].append(record)
    
    if len(by_employee) == 1:
        emp_name = list(by_employee.keys())[0]
        emp_records = by_employee[emp_name]
        
        output = f"✅ **Yes, {employee_id}** was **PRESENT** on {target_date}!\n\n"
        output += f"**Employee:** {emp_name}\n"
        output += f"**Records:** {len(emp_records)}\n\n"
        output += "**Timeline:**\n"
        
        for i, record in enumerate(emp_records, 1):
            ts = record['timestamp'].strftime('%I:%M %p') if isinstance(record['timestamp'], datetime) else str(record['timestamp'])
            output += f"{i}. {ts} - {record.get('type')} 📍 {record.get('location')}\n"
        
        return output
    else:
        output = f"🔍 Found **{len(by_employee)} employees** matching '{employee_id}':\n\n"
        for i, (emp_name, emp_records) in enumerate(by_employee.items(), 1):
            first_entry = emp_records[0]['timestamp'].strftime('%I:%M %p') if isinstance(emp_records[0]['timestamp'], datetime) else str(emp_records[0]['timestamp'])
            output += f"{i}. {emp_name}\n"
            output += f"   - Records: {len(emp_records)}\n"
            output += f"   - First entry: {first_entry} 📍 {emp_records[0].get('location')}\n\n"
        
        return output

# ==================== MCP SERVER ====================

server = Server("attendance-server")
attendance_db = AttendanceDB()

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List all available attendance tools"""
    return [
        Tool(
            name="check_attendance",
            description="Check attendance records for a specific date with optional employee filter. Returns detailed attendance records including timestamps, check-in/out types, and locations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (default: today)"
                    },
                    "employee_identifier": {
                        "type": "string",
                        "description": "Optional: Employee name or ID to filter (supports partial matching)"
                    }
                }
            }
        ),
        Tool(
            name="check_presence",
            description="Check if a specific employee is present on a given date. Returns YES/NO with detailed timeline.",
            inputSchema={
                "type": "object",
                "properties": {
                    "employee_identifier": {
                        "type": "string",
                        "description": "Employee name or ID to check"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (default: today)"
                    }
                },
                "required": ["employee_identifier"]
            }
        ),
        Tool(
            name="get_attendance_range",
            description="Get attendance records for a date range with optional employee filter.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    },
                    "employee_identifier": {
                        "type": "string",
                        "description": "Optional: Employee name or ID to filter"
                    }
                },
                "required": ["start_date", "end_date"]
            }
        ),
        Tool(
            name="count_present_operators",
            description="Count operators who clocked in after a specific time on a given date.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (default: today)"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Time in HH:MM format (default: 07:00)"
                    }
                }
            }
        ),
        Tool(
            name="department_headcount",
            description="Count employees under a certain department who clocked in after a specific time on a given date.",
            inputSchema={
                "type": "object",
                "properties": {
                    "department": {
                        "type": "string",
                        "description": "Department designation"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (default: today)"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Time in HH:MM format (default: 07:00)"
                    }
                }
            }
        ),
        Tool(
            name="get_absent_employees",
            description="Get list of employees who are absent on a specific date by comparing registered employees with attendance records.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (default: today)"
                    }
                }
            }
        ),
        Tool(
            name="get_latest_entries",
            description="Get the most recent attendance entries for debugging or monitoring purposes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_time": {
                        "type": "string",
                        "description": "Optional start time"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "Optional end time"
                    },
                    "where": {
                        "type": "string",
                        "description": "Setting whether to get earliest, latest, or entries between given time"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of entries to retrieve (default: 10, max: 100)"
                    }
                },
                "required": ["where"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution"""
    
    try:
        if name == "check_attendance":
            return await handle_check_attendance(arguments)
        
        elif name == "check_presence":
            return await handle_check_presence(arguments)
        
        elif name == "get_attendance_range":
            return await handle_attendance_range(arguments)
        
        elif name == "department_headcount":
            return await handle_dept_headcount(arguments)
        
        elif name == "count_present_operators":
            return await handle_count_operators(arguments)
        
        elif name == "get_absent_employees":
            return await handle_absent_employees(arguments)
        
        elif name == "get_latest_entries":
            return await handle_latest_entries(arguments)
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Error: {str(e)}")]

# ==================== TOOL HANDLERS ====================

async def handle_check_attendance(arguments: dict) -> list[TextContent]:
    """Handle attendance check"""
    target_date = date.today()
    if arguments.get("date"):
        target_date = parse_date_string(arguments["date"]) or date.today()
    
    employee_id = arguments.get("employee_identifier")
    
    records = attendance_db.get_records_by_date(target_date, employee_id)
    
    if not records:
        text = f"❌ No attendance records found for **{target_date}**"
        if employee_id:
            text += f" for **{employee_id}**"
    else:
        # prepare a csv file while formatting the output string
        filename = 'attendance_' + target_date.isoformat() + '.csv'
        csvfile = open(path_name + filename, 'w', newline='', encoding='utf-8')
        writer = csv.DictWriter(csvfile, fieldnames=['employee_name', 'employee_num', 'timestamp', 'location'], extrasaction='ignore')
        writer.writeheader()

        text = filename + f"# 📅 Attendance Records - {target_date}\n\n"
        if employee_id:
            text += f"**Filter:** {employee_id}\n"
        text += f"**Total records:** {len(records)}\n\n"
        
        for i, record in enumerate(records, 1):
            if i <= 20:
                text += f"{i}. {format_attendance_record(record)}\n"
            writer.writerow(record)
        
        if len(records) > 20:
            text += f"\n*Showing first 20 of {len(records)} records*"
    
    return [TextContent(type="text", text=text)]

async def handle_check_presence(arguments: dict) -> list[TextContent]:
    """Handle presence check"""
    employee_id = arguments["employee_identifier"]
    
    target_date = date.today()
    if arguments.get("date"):
        target_date = parse_date_string(arguments["date"]) or date.today()
    
    records = attendance_db.get_records_by_date(target_date, employee_id)
    text = format_presence_summary(records, employee_id, target_date)
    
    return [TextContent(type="text", text=text)]

async def handle_attendance_range(arguments: dict) -> list[TextContent]:
    """Handle attendance range query"""
    start_date = parse_date_string(arguments["start_date"])
    end_date = parse_date_string(arguments["end_date"])
    
    if not start_date or not end_date:
        return [TextContent(type="text", text="❌ Invalid date format. Use YYYY-MM-DD")]
    
    employee_id = arguments.get("employee_identifier")
    
    records = attendance_db.get_records_by_range(start_date, end_date, employee_id)

    if not records:
        text = f"❌ No records found from {start_date} to {end_date}"
        if employee_id:
            text += f" for {employee_id}"
    else:
        # prepare a csv file while formatting the output string
        filename = '_'.join([employee_id, start_date.isoformat(), end_date.isoformat()]) + '.csv'
        csvfile = open(path_name + filename, 'w', newline='', encoding='utf-8')
        writer = csv.DictWriter(csvfile, fieldnames=['employee_name', 'employee_num', 'timestamp'], extrasaction='ignore')
        writer.writeheader()

        text = filename + f"# 📊 Attendance Report\n\n"
        text += f"**Period:** {start_date} to {end_date}\n"
        if employee_id:
            text += f"**Employee:** {employee_id}\n"
        text += f"**Total records:** {len(records)}\n\n"
        
        # Group by date
        by_date = {}
        for record in records:
            record_date = record['timestamp'].date() if isinstance(record['timestamp'], datetime) else date.today()
            if record_date not in by_date:
                by_date[record_date] = []
            by_date[record_date].append(record)
        
        text += "## Daily Breakdown:\n\n"
        for record_date, day_records in sorted(by_date.items()):
            text += f"### {record_date} ({len(day_records)} records)\n"
            for record in day_records[:10]:
                text += f"- {format_attendance_record(record)}"
                writer.writerow(record)
            if len(day_records) > 10:
                text += f"*...and {len(day_records) - 10} more*\n"
            text += "\n"
            # continue writing to file
            for record in day_records[10:]:
                writer.writerow(record)
    
    return [TextContent(type="text", text=text)]

async def handle_count_operators(arguments: dict) -> list[TextContent]:
    """Handle operator counting"""
    target_date = date.today()
    if arguments.get("date"):
        target_date = parse_date_string(arguments["date"]) or date.today()
    
    start_time = time(7, 0)
    if arguments.get("start_time"):
        start_time = parse_time_string(arguments["start_time"]) or time(7, 0)
    
    operators = attendance_db.get_operators_present(target_date, start_time)
    
    text = f"# 👥 Operators Present - {target_date}\n\n"
    text += f"**Time threshold:** After {start_time.strftime('%H:%M')}\n"
    text += f"**Total operators:** {len(operators)}\n\n"
    
    if operators:
        text += "## Operators List:\n\n"
        for i, op in enumerate(operators, 1):
            first_entry = op['first_entry']
            if isinstance(first_entry, datetime):
                first_entry = first_entry.strftime('%I:%M %p')
            text += f"{i}. **{op['employee_name']}** ({op['employee_num']}) - {first_entry} 📍 {op['location']}\n"
    else:
        text += "❌ No operators clocked in after the specified time."
    
    return [TextContent(type="text", text=text)]

async def handle_dept_headcount(arguments: dict) -> list[TextContent]:
    target_date = date.today()
    if arguments.get("date"):
        target_date = parse_date_string(arguments["date"]) or date.today()
    
    start_time = time(7, 0)
    if arguments.get("start_time"):
        start_time = parse_time_string(arguments["start_time"]) or time(7, 0)
    
    dept_input = arguments.get("department")
    
    all_employees = attendance_db.get_all_employees(dept_input)
    present_employees = attendance_db.get_present_employees(target_date, start_time, dept_input)

    # prepare a csv file while formatting the output string
    filename = dept_input.replace(" ", "_") + '_' + target_date.isoformat() + '.csv'
    csvfile = open(path_name + filename, 'w', newline='', encoding='utf-8')
    writer = csv.DictWriter(csvfile, fieldnames=['employee_name', 'employee_num', 'department'], extrasaction='ignore')
    writer.writeheader()
    
    text = filename + f"# {dept_input} Department - {target_date}\n\n"
    text += f"**Total employees:** {len(all_employees)}\n"
    text += f"**Present:** {len(present_employees)}\n"
    rate = 100 * len(present_employees)/len(all_employees)
    text += f" ({rate:.2f}%)\n\n"

    text += "## Attendance List:\n\n"
    for i, emp in enumerate(present_employees[:30], 1):
        text += f"{i}. **{emp['employee_name']}** ({emp['employee_num']})\n"
        writer.writerow(emp)
    
    if len(present_employees) > 30:
        text += f"\n*Showing first 30 of {len(present_employees)} employees*"
    
    for emp in present_employees[30:]:
        writer.writerow(emp)

    return [TextContent(type="text", text=text)]

async def handle_absent_employees(arguments: dict) -> list[TextContent]:
    """Handle absent employee listing"""
    target_date = date.today()
    if arguments.get("date"):
        target_date = parse_date_string(arguments["date"]) or date.today()
    
    all_employees = attendance_db.get_all_employees()
    present_employees = attendance_db.get_present_employees(target_date)
    
    present_nums = {emp['employee_num'] for emp in present_employees}
    absent = [emp for emp in all_employees if emp['employee_num'] not in present_nums]
    
    text = f"# 🚫 Absent Employees - {target_date}\n\n"
    text += f"**Total employees:** {len(all_employees)}\n"
    # text += f"**Present:** {len(present_employees)}\n"
    text += f"**Absent:** {len(absent)}"
    rate = absent/len(all_employees)
    text += f" ({rate:.2f}%)\n\n"

    if absent:
        text += "## Absent List:\n\n"
        for i, emp in enumerate(absent, 1):
            text += f"{i}. **{emp['employee_name']}** ({emp['employee_num']})\n"
    else:
        text += "✅ All employees are present!"
    
    return [TextContent(type="text", text=text)]

async def handle_latest_entries(arguments: dict) -> list[TextContent]:
    """Handle latest entries retrieval"""
    today = date.today().isoformat()
    limit = min(arguments.get("limit", 10), 100)
    where = arguments["where"]
    start_time = arguments.get("start_time")
    end_time = arguments.get("end_time")
    
    records = attendance_db.get_latest_entries(start_time, end_time, where, limit)

    if where == 'last':
        filename = 'latest_entries_' + today + '.csv'
        text = filename + f"# 🕐 Latest Attendance Entries\n\n"
    elif where == 'first':
        filename = 'earliest_entries_' + today + '.csv'
        text = filename + f"# 🕐 Earliest Attendance Entries\n\n"
        text += f"**Date:** {today}\n\n"
    elif where == 'middle':
        filename = 'entries_' + today + '_' + start_time + '_' + end_time + '.csv'
        text = filename + f"# 🕐 Attendance Entries\n\n"
        text += f"**Date:** {today} from {start_time} to {end_time}\n\n"

    # prepare a csv file while formatting the output string
    csvfile = open(path_name + filename, 'w', newline='', encoding='utf-8')
    writer = csv.DictWriter(csvfile, fieldnames=['timestamp', 'employee_name', 'employee_num', 'location'], extrasaction='ignore')
    writer.writeheader()
    
    text += f"**Count:** {len(records)}\n\n"
    
    for i, record in enumerate(records, 1):
        text += f"{i}. {format_attendance_record(record)}\n"
        writer.writerow(record)
    
    return [TextContent(type="text", text=text)]

# ==================== MAIN ====================

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="attendance-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())