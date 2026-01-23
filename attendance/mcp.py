#!/usr/bin/env python3
"""
Attendance MCP Server
Provides attendance tracking tools via Model Context Protocol
"""

import asyncio
import json
from datetime import date, time, datetime, timedelta
from typing import Any, Optional
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

# Configuration
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


class AttendanceDB:
    """Database connection handler"""
    
    def __init__(self):
        self.config = DB_CONFIG
    
    def connect(self):
        """Create database connection"""
        try:
            return mysql.connector.connect(**self.config)
        except Error as e:
            raise Exception(f"Database connection error: {e}")
    
    def get_records_by_date(self, target_date: date, employee_identifier: str = None):
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
    
    def get_records_by_range(self, start_date: date, end_date: date, employee_identifier: str = None):
        """Get attendance records for a date range"""
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
    
    def get_operators_present(self, target_date: date, start_time: time):
        """Get operators who clocked in after a specific time"""
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT DISTINCT `employee_name`, `employee_num`, MIN(`timestamp`) as first_entry,
                       (SELECT `device_ip` FROM `raw` r2 
                        WHERE r2.`employee_num` = r1.`employee_num` 
                        AND DATE(r2.`timestamp`) = %s
                        AND TIME(r2.`timestamp`) >= %s
                        ORDER BY r2.`timestamp` ASC LIMIT 1) as device_ip
                FROM `raw` r1
                WHERE DATE(`timestamp`) = %s
                AND TIME(`timestamp`) >= %s
                AND `type` IN ({})
                GROUP BY `employee_name`, `employee_num`
                ORDER BY first_entry ASC
            """.format(','.join(['%s'] * len(CHECKIN_TYPES)))
            
            params = (target_date, start_time, target_date, start_time) + tuple(CHECKIN_TYPES)
            cursor.execute(query, params)
            operators = cursor.fetchall()
            return self._add_locations(operators)
            
        finally:
            cursor.close()
            conn.close()
    
    def get_all_employees(self):
        """Get all employees from the list table"""
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT DISTINCT employee_name, employee_num
                FROM `list`
                ORDER BY employee_name
            """)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    
    def get_present_employees(self, target_date: date):
        """Get employees present on a specific date"""
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT DISTINCT employee_name, employee_num
                FROM `raw`
                WHERE DATE(`timestamp`) = %s
            """, (target_date,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    
    def _add_locations(self, records):
        """Add location information to records"""
        for record in records:
            device_ip = record.get('device_ip', '')
            record['location'] = DEVICE_LOCATIONS.get(device_ip, device_ip)
        return records


def format_records_as_text(records, title="Attendance Records"):
    """Format records as readable text"""
    if not records:
        return "No records found."
    
    output = [f"# {title}", f"Total records: {len(records)}\n"]
    
    for i, record in enumerate(records, 1):
        ts = record.get('timestamp', '')
        if isinstance(ts, datetime):
            ts = ts.strftime('%Y-%m-%d %I:%M %p')
        
        output.append(f"{i}. {record.get('employee_name', 'Unknown')} ({record.get('employee_num', 'N/A')})")
        output.append(f"   Time: {ts}")
        output.append(f"   Type: {record.get('type', 'N/A')}")
        output.append(f"   Location: {record.get('location', 'Unknown')}\n")
    
    return "\n".join(output)


# Initialize MCP server
server = Server("attendance-server")
db = AttendanceDB()


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available attendance tools"""
    return [
        Tool(
            name="check_presence",
            description="Check if an employee is present on a specific date. Returns attendance records.",
            inputSchema={
                "type": "object",
                "properties": {
                    "employee_identifier": {
                        "type": "string",
                        "description": "Employee name or ID (e.g., 'Ryan' or 'KE0152')"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (default: today)",
                        "default": date.today().isoformat()
                    }
                },
                "required": ["employee_identifier"]
            }
        ),
        Tool(
            name="get_attendance_by_date",
            description="Get all attendance records for a specific date, optionally filtered by employee.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format"
                    },
                    "employee_identifier": {
                        "type": "string",
                        "description": "Optional: Filter by employee name or ID"
                    }
                },
                "required": ["date"]
            }
        ),
        Tool(
            name="get_attendance_range",
            description="Get attendance records for a date range, optionally filtered by employee.",
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
                        "description": "Optional: Filter by employee name or ID"
                    }
                },
                "required": ["start_date", "end_date"]
            }
        ),
        Tool(
            name="count_operators_present",
            description="Count operators who clocked in after a specific time on a given date.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (default: today)",
                        "default": date.today().isoformat()
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Time threshold in HH:MM format (default: 07:00)",
                        "default": "07:00"
                    }
                }
            }
        ),
        Tool(
            name="get_absent_employees",
            description="Get list of employees who are absent on a specific date.",
            inputSchema={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format (default: today)",
                        "default": date.today().isoformat()
                    }
                }
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution"""
    
    try:
        if name == "check_presence":
            employee_id = arguments["employee_identifier"]
            target_date = date.fromisoformat(arguments.get("date", date.today().isoformat()))
            
            records = db.get_records_by_date(target_date, employee_id)
            
            if not records:
                result = f"❌ {employee_id} is NOT PRESENT on {target_date}\n\nNo attendance records found."
            else:
                result = f"✅ {employee_id} is PRESENT on {target_date}!\n\n"
                result += format_records_as_text(records, "Timeline")
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_attendance_by_date":
            target_date = date.fromisoformat(arguments["date"])
            employee_id = arguments.get("employee_identifier")
            
            records = db.get_records_by_date(target_date, employee_id)
            
            title = f"Attendance for {target_date}"
            if employee_id:
                title += f" - {employee_id}"
            
            result = format_records_as_text(records, title)
            return [TextContent(type="text", text=result)]
        
        elif name == "get_attendance_range":
            start_date = date.fromisoformat(arguments["start_date"])
            end_date = date.fromisoformat(arguments["end_date"])
            employee_id = arguments.get("employee_identifier")
            
            records = db.get_records_by_range(start_date, end_date, employee_id)
            
            title = f"Attendance from {start_date} to {end_date}"
            if employee_id:
                title += f" - {employee_id}"
            
            result = format_records_as_text(records, title)
            return [TextContent(type="text", text=result)]
        
        elif name == "count_operators_present":
            target_date = date.fromisoformat(arguments.get("date", date.today().isoformat()))
            start_time_str = arguments.get("start_time", "07:00")
            start_time = time.fromisoformat(start_time_str)
            
            operators = db.get_operators_present(target_date, start_time)
            
            result = f"# Operators Present on {target_date}\n"
            result += f"Time threshold: After {start_time_str}\n"
            result += f"Total operators: {len(operators)}\n\n"
            
            if operators:
                for i, op in enumerate(operators, 1):
                    first_entry = op['first_entry']
                    if isinstance(first_entry, datetime):
                        first_entry = first_entry.strftime('%I:%M %p')
                    result += f"{i}. {op['employee_name']} ({op['employee_num']}) - {first_entry} 📍 {op['location']}\n"
            else:
                result += "No operators clocked in after the specified time."
            
            return [TextContent(type="text", text=result)]
        
        elif name == "get_absent_employees":
            target_date = date.fromisoformat(arguments.get("date", date.today().isoformat()))
            
            all_employees = db.get_all_employees()
            present_employees = db.get_present_employees(target_date)
            
            present_nums = {emp['employee_num'] for emp in present_employees}
            absent = [emp for emp in all_employees if emp['employee_num'] not in present_nums]
            
            result = f"# Absent Employees on {target_date}\n"
            result += f"Total employees: {len(all_employees)}\n"
            result += f"Present: {len(present_employees)}\n"
            result += f"Absent: {len(absent)}\n\n"
            
            if absent:
                for i, emp in enumerate(absent, 1):
                    result += f"{i}. {emp['employee_name']} ({emp['employee_num']})\n"
            else:
                result += "✅ All employees are present!"
            
            return [TextContent(type="text", text=result)]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


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