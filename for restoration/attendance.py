# attendance.py - Comprehensive Attendance Handler with Device Location
import mysql.connector
from mysql.connector import Error
from typing import Optional, Dict, List, Tuple
from datetime import datetime, date, time, timedelta
import re
from collections import defaultdict

class AttendanceHandler:
    """Handle all attendance-related queries"""
    
    # Device location mapping
    DEVICE_LOCATIONS = {
        '192.168.1.25': 'Building 6',
        '192.168.1.33': 'Canteen',
        '192.168.1.37': 'Lobby'
    }
    
    def __init__(self, host: str, user: str, password: str):
        self.host = host
        self.user = user
        self.password = password
        self.database = 'attendance'
        self.table = 'raw'
        
        # Column schema
        self.columns = {
            'id': 'INT',
            'employee_num': 'VARCHAR',
            'employee_name': 'VARCHAR',
            'timestamp': 'DATETIME',
            'type': 'VARCHAR',
            'device_ip': 'VARCHAR',
            'created_at': 'DATETIME'
        }
    
    def get_device_location(self, device_ip: str) -> str:
        """Get location name from device IP"""
        return self.DEVICE_LOCATIONS.get(device_ip, device_ip)
    
    def format_record_with_location(self, record: Dict) -> Dict:
        """Add location info to record"""
        record['location'] = self.get_device_location(record.get('device_ip', ''))
        return record
    
    def connect(self):
        """Connect to attendance database"""
        try:
            return mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                autocommit=True,
                use_unicode=True,
                charset='utf8mb4'
            )
        except Error as e:
            print(f"❌ Attendance DB connection error: {e}")
            return None
    
    def is_present_today(self, employee_identifier: str) -> Dict:
        """
        Check if employee is present today
        Args:
            employee_identifier: Can be employee name (partial or full) or employee number
        Returns:
            Dict with presence info and records
        """
        conn = self.connect()
        if not conn:
            return {'error': 'Database connection failed'}
        
        try:
            cursor = conn.cursor(dictionary=True)
            today = date.today()
            
            query = """
                SELECT * FROM `raw` 
                WHERE DATE(`timestamp`) = %s 
                AND (
                    `employee_name` LIKE %s 
                    OR `employee_num` LIKE %s
                )
                ORDER BY `timestamp` DESC
            """
            
            search_pattern = f"%{employee_identifier}%"
            
            print(f"🔍 DEBUG: Searching for '{employee_identifier}' on {today}")
            print(f"   Pattern: {search_pattern}")
            
            cursor.execute(query, (today, search_pattern, search_pattern))
            records = cursor.fetchall()
            
            # Add location info to each record
            records = [self.format_record_with_location(r) for r in records]
            
            print(f"   Found {len(records)} records")
            
            if records:
                for r in records[:3]:
                    print(f"   - {r['employee_name']} ({r['employee_num']}) at {r['timestamp']} - {r['location']}")
            
            cursor.close()
            conn.close()
            
            if not records:
                return {
                    'present': False,
                    'employee_identifier': employee_identifier,
                    'date': today,
                    'records': [],
                    'message': f"No records found for '{employee_identifier}' today"
                }
            
            # Group by employee if multiple matches
            by_employee = defaultdict(list)
            for record in records:
                key = f"{record['employee_name']} ({record['employee_num']})"
                by_employee[key].append(record)
            
            return {
                'present': True,
                'employee_identifier': employee_identifier,
                'date': today,
                'matches': len(by_employee),
                'employees': dict(by_employee),
                'total_records': len(records)
            }
            
        except Error as e:
            print(f"❌ Database error: {e}")
            return {'error': f"Query error: {str(e)}"}
    
    def get_attendance_by_date(self, target_date: date, employee_identifier: Optional[str] = None) -> Dict:
        """
        Get attendance records for a specific date
        Args:
            target_date: Date to query
            employee_identifier: Optional employee name/number filter
        """
        conn = self.connect()
        if not conn:
            return {'error': 'Database connection failed'}
        
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
            
            # Add location info to each record
            records = [self.format_record_with_location(r) for r in records]
            
            cursor.close()
            conn.close()
            
            if not records:
                return {
                    'date': target_date,
                    'employee_identifier': employee_identifier,
                    'records': [],
                    'count': 0,
                    'total_records': 0,
                    'unique_employees': 0,
                    'employees': {},
                    'message': 'No records found'
                }
            
            # Group by employee
            by_employee = defaultdict(list)
            for record in records:
                key = f"{record['employee_name']} ({record['employee_num']})"
                by_employee[key].append(record)
            
            return {
                'date': target_date,
                'employee_identifier': employee_identifier,
                'employees': dict(by_employee),
                'total_records': len(records),
                'unique_employees': len(by_employee),
                'count': len(records)
            }
            
        except Error as e:
            return {'error': f"Query error: {str(e)}"}
    
    def get_attendance_range(self, start_date: date, end_date: date, 
                            employee_identifier: Optional[str] = None) -> Dict:
        """Get attendance records for a date range"""
        conn = self.connect()
        if not conn:
            return {'error': 'Database connection failed'}
        
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
            
            # Add location info to each record
            records = [self.format_record_with_location(r) for r in records]
            
            cursor.close()
            conn.close()
            
            if not records:
                return {
                    'start_date': start_date,
                    'end_date': end_date,
                    'employee_identifier': employee_identifier,
                    'records': [],
                    'count': 0,
                    'total_records': 0,
                    'unique_employees': 0,
                    'employees': {}
                }
            
            # Group by employee and date
            by_employee = defaultdict(lambda: defaultdict(list))
            for record in records:
                emp_key = f"{record['employee_name']} ({record['employee_num']})"
                record_date = record['timestamp'].date()
                by_employee[emp_key][record_date].append(record)
            
            return {
                'start_date': start_date,
                'end_date': end_date,
                'employee_identifier': employee_identifier,
                'employees': {emp: dict(dates) for emp, dates in by_employee.items()},
                'total_records': len(records),
                'unique_employees': len(by_employee),
                'count': len(records)
            }
            
        except Error as e:
            return {'error': f"Query error: {str(e)}"}
    
    def count_present_operators(self, target_date: date, start_time: time = time(7, 0)) -> Dict:
        """
        Count how many operators clocked in after a specific time
        Args:
            target_date: Date to check
            start_time: Time threshold (default 7:00 AM)
        """
        conn = self.connect()
        if not conn:
            return {'error': 'Database connection failed'}
        
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
                AND `type` IN ('time in', 'check in', 'clock in', 'in', 'Time In', 'Check In')
                GROUP BY `employee_name`, `employee_num`
                ORDER BY first_entry ASC
            """
            
            cursor.execute(query, (target_date, start_time, target_date, start_time))
            operators = cursor.fetchall()
            
            # Add location info to each operator
            operators = [self.format_record_with_location(op) for op in operators]
            
            cursor.close()
            conn.close()
            
            return {
                'date': target_date,
                'start_time': start_time.strftime('%H:%M'),
                'count': len(operators),
                'operators': operators
            }
            
        except Error as e:
            return {'error': f"Query error: {str(e)}"}
    def get_absent_employees(self, target_date: date) -> Dict:
        """Return list of employees who have NO attendance record for the given date"""
        conn = self.connect()
        if not conn:
            return {'error': 'Database connection failed'}
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Get all unique employees from the system
            cursor.execute("""
                SELECT DISTINCT employee_name, employee_num
                FROM `list`
                ORDER BY employee_name
            """)
            all_employees = cursor.fetchall()
            
            # Get employees present on target date
            cursor.execute("""
                SELECT DISTINCT employee_name, employee_num
                FROM `raw`
                WHERE DATE(`timestamp`) = %s
            """, (target_date,))
            present_employees = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Create set of present employee numbers for fast lookup
            present_nums = {emp['employee_num'] for emp in present_employees}
            
            # Find absent employees
            absent = [
                {'name': emp['employee_name'], 'num': emp['employee_num']}
                for emp in all_employees
                if emp['employee_num'] not in present_nums
            ]
            
            return {
                "date": target_date,
                "total_employees": len(all_employees),
                "present": len(present_employees),
                "absent": len(absent),
                "absent_list": absent
            }
            
        except Error as e:
            return {"error": f"Query error: {str(e)}"}
    def get_latest_entries(self, limit: int = 10) -> Dict:
        """Get latest attendance entries for debugging"""
        conn = self.connect()
        if not conn:
            return {'error': 'Database connection failed'}
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT * FROM `raw` 
                ORDER BY `timestamp` DESC 
                LIMIT %s
            """
            cursor.execute(query, (limit,))
            records = cursor.fetchall()
            
            # Add location info to each record
            records = [self.format_record_with_location(r) for r in records]
            
            cursor.close()
            conn.close()
            
            return {
                'latest_entries': records,
                'count': len(records)
            }
            
        except Error as e:
            return {'error': f"Query error: {str(e)}"}
    
    def format_presence_response(self, result: Dict, query_type: str) -> str:
        """Format attendance results into readable response"""
        
        if 'error' in result:
            return f"❌ **Error:** {result['error']}"
        
        # Handle "is present today" queries
        if query_type == 'presence_check':
            if not result['present']:
                return f"❌ **{result['employee_identifier']}** is **NOT PRESENT** today ({result['date']}).\n\n💡 They have no attendance records for today."
            
            if result['matches'] == 1:
                # Single employee found
                emp_name = list(result['employees'].keys())[0]
                records = result['employees'][emp_name]
                
                output = f"✅ **Yes, {result['employee_identifier']}** is **PRESENT** today!\n\n"
                output += f"**Employee:** {emp_name}\n"
                output += f"**Records today:** {len(records)}\n\n"
                output += "**Timeline:**\n"
                
                for idx, record in enumerate(records, 1):
                    timestamp = record['timestamp'].strftime('%I:%M %p')
                    rec_type = record.get('type', 'Entry')
                    location = record.get('location', 'Unknown')
                    output += f"{idx}. {timestamp} - {rec_type} 📍 **{location}**\n"
                
                return output
            
            else:
                # Multiple employees matched
                output = f"🔍 Found **{result['matches']} employees** matching '{result['employee_identifier']}':\n\n"
                
                for idx, (emp_name, records) in enumerate(result['employees'].items(), 1):
                    output += f"### {idx}. {emp_name}\n"
                    output += f"   - Records: {len(records)}\n"
                    first_entry = records[0]['timestamp'].strftime('%I:%M %p')
                    location = records[0].get('location', 'Unknown')
                    output += f"   - First entry: {first_entry} 📍 {location}\n\n"
                
                output += "💡 **Tip:** Use full name or employee number for specific results."
                return output
        
        # Handle date-specific queries
        elif query_type == 'date_query':
            total_records = result.get('total_records', 0)
            
            if total_records == 0:
                msg = f"❌ **{result.get('employee_identifier', 'No one')}** was **NOT PRESENT** on **{result['date']}**"
                if result.get('employee_identifier'):
                    msg += "\n\n💡 They have no attendance records for this date."
                return msg
            
            # Check if this is a single employee query
            if result.get('employee_identifier') and result['unique_employees'] <= 3:
                if result['unique_employees'] == 1:
                    emp_name = list(result['employees'].keys())[0]
                    records = result['employees'][emp_name]
                    
                    output = f"✅ **Yes, {result['employee_identifier']}** was **PRESENT** on **{result['date']}**!\n\n"
                    output += f"**Employee:** {emp_name}\n"
                    output += f"**Records:** {len(records)}\n\n"
                    output += "**Timeline:**\n"
                    
                    for idx, record in enumerate(records, 1):
                        timestamp = record['timestamp'].strftime('%I:%M %p')
                        rec_type = record.get('type', 'Entry')
                        location = record.get('location', 'Unknown')
                        output += f"{idx}. {timestamp} - {rec_type} 📍 **{location}**\n"
                    
                    return output
                else:
                    output = f"🔍 Found **{result['unique_employees']} employees** matching '{result['employee_identifier']}' on **{result['date']}**:\n\n"
                    
                    for idx, (emp_name, records) in enumerate(result['employees'].items(), 1):
                        output += f"### {idx}. {emp_name}\n"
                        output += f"   - Records: {len(records)}\n"
                        first_entry = records[0]['timestamp'].strftime('%I:%M %p')
                        location = records[0].get('location', 'Unknown')
                        output += f"   - First entry: {first_entry} 📍 {location}\n\n"
                    
                    output += "💡 **Tip:** Use full name or employee number for specific results."
                    return output
            
            # General date query
            output = f"# 📅 Attendance for {result['date']}\n\n"
            
            if result.get('employee_identifier'):
                output += f"**Employee Filter:** {result['employee_identifier']}\n"
            
            output += f"**Unique Employees:** {result['unique_employees']}\n"
            output += f"**Total Records:** {result['total_records']}\n\n"
            
            output += "## 👥 Employee Records:\n\n"
            for emp_name, records in list(result['employees'].items())[:20]:
                output += f"### {emp_name}\n"
                output += f"**Entries:** {len(records)}\n"
                for record in records[:5]:
                    timestamp = record['timestamp'].strftime('%I:%M %p')
                    rec_type = record.get('type', 'Entry')
                    location = record.get('location', 'Unknown')
                    output += f"   - {timestamp}: {rec_type} 📍 {location}\n"
                output += "\n"
            
            if result['unique_employees'] > 20:
                output += f"*Showing first 20 of {result['unique_employees']} employees*\n"
            
            return output
        
        # Handle date range queries
        elif query_type == 'range_query':
            total_records = result.get('total_records', 0)
            
            if total_records == 0:
                msg = f"❌ "
                if result.get('employee_identifier'):
                    msg += f"**{result['employee_identifier']}** has no records from {result['start_date']} to {result['end_date']}"
                else:
                    msg += f"No records found from {result['start_date']} to {result['end_date']}"
                return msg
            
            output = f"# 📊 Attendance Report\n\n"
            output += f"**Period:** {result['start_date']} to {result['end_date']}\n"
            
            if result.get('employee_identifier'):
                output += f"**Employee:** {result['employee_identifier']}\n"
            
            output += f"**Unique Employees:** {result['unique_employees']}\n"
            output += f"**Total Records:** {result['total_records']}\n\n"
            
            output += "## 📅 Daily Breakdown:\n\n"
            
            for emp_name, dates in list(result['employees'].items())[:10]:
                output += f"### {emp_name}\n"
                output += f"**Days present:** {len(dates)}\n\n"
                
                for record_date, records in sorted(dates.items())[:7]:
                    output += f"**{record_date}:** {len(records)} entries\n"
                    for record in records[:3]:
                        timestamp = record['timestamp'].strftime('%I:%M %p')
                        rec_type = record.get('type', 'Entry')
                        location = record.get('location', 'Unknown')
                        output += f"   - {timestamp}: {rec_type} 📍 {location}\n"
                output += "\n"
            
            if result['unique_employees'] > 10:
                output += f"*Showing first 10 of {result['unique_employees']} employees*\n"
            
            return output
        
        # Handle operator count queries
        elif query_type == 'count_operators':
            if 'error' in result:
                return f"❌ **Error:** {result['error']}"
            
            output = f"# 👥 Operators Present\n\n"
            output += f"**Date:** {result['date']}\n"
            output += f"**Time threshold:** After {result['start_time']}\n"
            output += f"**Total operators:** {result['count']}\n\n"
            
            if result['count'] > 0:
                output += "## Operators List:\n\n"
                for idx, op in enumerate(result['operators'], 1):
                    first_entry = op['first_entry'].strftime('%I:%M %p')
                    location = op.get('location', 'Unknown')
                    output += f"{idx}. **{op['employee_name']}** ({op['employee_num']}) - {first_entry} 📍 **{location}**\n"
            else:
                output += "❌ No operators clocked in after the specified time.\n"
            
            return output
        
        return "❓ Unknown query type"
