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

departments = ['Top Management',
            'Manufacturing', 'Quality Regulatory Affairs & EHS',
            'Business Development', 'HR & Admin',
            'Supply Chain Management', 'Facilities & Maintenance',
            'Information Technology', 'Research & Development',
            'Accounting', 'Finance & Administration']

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
        self.employees = []

        conn = self.connect()
        if conn is not None:
            cursor = conn.cursor(dictionary=True)
            query = " SELECT `employee_num`, `employee_name`, `department`, `division`, `job_title` FROM `list`"
            cursor.execute(query)
            self.employees = cursor.fetchall()
            cursor.close()
        # finally:
            # cursor.close()
            conn.close()
    
    def connect(self):
        """Create database connection"""
        try:
            return mysql.connector.connect(**self.config)
        except Error as e:
            # raise Exception(f"Database connection error: {e}")
            print(f"Database connection error: {e}")
            return None
    
    def get_attendance(self, target_date: List[str], identifier: Dict[str, List], order: str='ASC'):
        id_term = ''
        if identifier:
            id_list = []
            # Supports multiple identifiers of different kinds (name, num, department)
            for key, values in identifier.items():
                if type(values) == list:
                    for id in values:
                        if key == 'employee_num':
                            id_list.append(f't1.`employee_num` LIKE "%{id}%"')
                        elif key == 'department':
                            id_list.append(f't2.`department` LIKE "%{id}%"')
                        elif key == 'employee_name':
                            name_parts = id.lower().replace(',', '').split()
                            temp = []
                            for np in name_parts:
                                temp.append(f't1.`employee_name` LIKE "%{np}%"')
                            id_list.append(f"( {' AND '.join(temp)} )")
                elif type(values) == str and values != '':
                    if key == 'employee_num':
                        id_list.append(f't1.`employee_num` LIKE "%{values}%"')
                    elif key == 'department':
                        id_list.append(f't2.`department` LIKE "%{values}%"')
                    elif key == 'employee_name':
                        name_parts = values.lower().replace(',', '').split()
                        temp = []
                        for np in name_parts:
                            temp.append(f't1.`employee_name` LIKE "%{np}%"')
                        id_list.append(f"( {' AND '.join(temp)} )")
            if id_list:
                id_term = 'AND ( ' + ' OR '.join(id_list) + ' )'
                print('combined:', id_term)
        
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            query = f""" SELECT t1.`employee_num`, t1.`employee_name`, t1.`timestamp`, t1.`device_ip`, t2.`department` FROM `raw` t1
            LEFT JOIN `list` t2 ON t1.`employee_num`=t2.`employee_num` 
            WHERE DATE(`timestamp`) BETWEEN '{target_date[0]}' AND '{target_date[-1]}' """ + id_term + f""" ORDER BY `timestamp` {order} """
            # print('FINAL QUERY:', query)
            cursor.execute(query)
            records = cursor.fetchall()

            return self._add_locations(records)
        
        finally:
            cursor.close()
            conn.close()
    
    def dept_rate(self, target_date: List[str], departments: List):
        
        if type(departments) == list:
            dept_list = [f" `department` LIKE '%{dept}%' " for dept in departments]
        elif type(departments) == str:
            dept_list = [f" `department` LIKE '%{departments}%' "]
        
        if dept_list:
            dept_term = ' AND ' + 'OR'.join(dept_list)
        else:
            dept_term = ''
        
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            query = """ SELECT `employee_num`, `employee_name`, `department` FROM `list` """
            if dept_term:
                query += " WHERE " + 'OR'.join(dept_list)
            cursor.execute(query)
            all_emp = cursor.fetchall()

            query = f""" SELECT t1.`employee_num`, t1.`employee_name`, t2.`department`, MIN(`timestamp`) AS 'first_log', t1.`device_ip` FROM `raw` t1
            LEFT JOIN `list` t2 ON t1.`employee_num`=t2.`employee_num` 
            WHERE DATE(`timestamp`) BETWEEN '{target_date[0]}' AND '{target_date[-1]}' """ + dept_term + """ 
            GROUP BY t1.`employee_num`, t1.`employee_name`, t1.`device_ip` """
            cursor.execute(query)
            present = cursor.fetchall()

            # absent = []
            for emp in all_emp:
                emp.update({'first_log': 'absent', 'device_ip': 'none'})
                for p_e in present:
                    if p_e['employee_num'] == emp['employee_num']:
                        emp['first_log'] = p_e['first_log']
                        emp['device_ip'] = p_e['device_ip']
                # if emp['first_log'] == 'none':
                #     absent.append(emp['employee_name'])
            
            # print(len(all_emp))
            # print(len(present))
            return {'raw_records': self._add_locations(all_emp), 'total': len(all_emp), 'present': len(present)}

        finally:
            cursor.close()
            conn.close()
    
    def find_person(self, identifiers: Dict[str, List]):
        # identifiers = {'employee_name':[], 'employee_num':[], 'department':[], 'division':[], 'job_title':[]}
        filters = ''
        temp = []
        for key,value in identifiers.items():
            if type(value) == list:
                temp.extend([f' `{key}` LIKE "%{v}%" ' for v in value])
                # filters += " OR ".join(temp)
            elif type(value) == str:
                temp.append(f' `{key}` LIKE "%{value}%" ')
        filters += " OR ".join(temp)
        
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            query = " SELECT * FROM `list` "
            if filters:
                query += "WHERE" + filters
            cursor.execute(query)
            records = cursor.fetchall()
            return records
        finally:
            cursor.close()
            conn.close()
    
    def get_records_by_date(self, target_date: date, employee_identifier: str = '') -> List[Dict]:
        """Get attendance records for a specific date"""
        conn = self.connect()
        try:
            cursor = conn.cursor(dictionary=True)
            
            if employee_identifier == '':
                query = """ SELECT t1.*, t2.`department` FROM `raw` t1
                INNER JOIN `list` t2 ON t1.`employee_num` = t2.`employee_num`
                WHERE DATE(`timestamp`) = %s 
                ORDER BY `timestamp` ASC """
                cursor.execute(query, (target_date, ))
                records = cursor.fetchall()
            else:
                name_parts = employee_identifier.lower().replace(',', '').split()
                query = """ SELECT t1.*, t2.`department` FROM `raw` t1
                INNER JOIN `list` t2 ON t1.`employee_num` = t2.`employee_num`
                WHERE DATE(`timestamp`) = %s 
                AND (
                    t1.`employee_name` LIKE %s 
                    OR t1.`employee_num` LIKE %s
                )
                ORDER BY `timestamp` ASC """
                cursor.execute(query, (target_date, f"%{name_parts[0]}%", f"{employee_identifier}"))
                records = cursor.fetchall()

                filtered_records = []
                if len(name_parts) > 1:
                    for rec in records:
                        near_match = [part for part in name_parts[1:] if part in rec['employee_name'].lower()]
                        if near_match:
                            filtered_records.append(rec)
                    records = filtered_records

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
            if not employee_identifier:
                query = """
                    SELECT * FROM `raw` 
                    WHERE DATE(`timestamp`) BETWEEN %s AND %s 
                    ORDER BY `timestamp` ASC
                """
                cursor.execute(query, (start_date, end_date))
                records = cursor.fetchall()
                return self._add_locations(records)

            name_parts = employee_identifier.lower().replace(',', '').split()
            query = """
SELECT t1.*, t2.`department` FROM `raw` t1
INNER JOIN `list` t2 ON t1.`employee_num` = t2.`employee_num`
WHERE DATE(`timestamp`) BETWEEN %s AND %s 
AND (
    t1.`employee_name` LIKE %s 
    OR t1.`employee_num` LIKE %s
)
ORDER BY `timestamp` ASC
            """
            search_pattern = f"%{name_parts[0]}%"
            cursor.execute(query, (start_date, end_date, search_pattern, search_pattern))
            records = cursor.fetchall()

            filtered_records = []
            if len(name_parts) > 1:
                for rec in records:
                    near_match = [part for part in name_parts[1:] if part in rec['employee_name'].lower()]
                    if near_match:
                        filtered_records.append(rec)
                records = filtered_records
            
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
                    SELECT DISTINCT `employee_name`, `employee_num`, `department`
                    FROM `list`
                    ORDER BY `employee_name`
                """)
            else:
                cursor.execute("""
                    SELECT DISTINCT `employee_name`, `employee_num`, `department`
                    FROM `list`
                    WHERE `department` LIKE %s
                    ORDER BY `employee_name`
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
            if dept == 'all': # get all departments
                cursor.execute("""
                    SELECT DISTINCT employee_name, employee_num
                    FROM `raw`
                    WHERE DATE(`timestamp`) = %s
                    AND TIME(`timestamp`) <= %s
                """, (target_date, start_time))
            else:
                cursor.execute("""
SELECT t1.`employee_num`, t1.`employee_name`, t1.`department`, MIN(t2.`timestamp`) as 'timestamp' FROM `list` t1
LEFT JOIN `raw` t2 ON t1.`employee_num` = t2.`employee_num` 
WHERE t1.`department` = %s
AND DATE(t2.`timestamp`) = %s
AND TIME(t2.`timestamp`) <= %s
GROUP BY t1.`employee_num`
ORDER BY MIN(t2.`timestamp`)
                """, (f'%{dept}%', target_date, start_time,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    
    def get_latest_entries(self, start_time: Optional[str], end_time: Optional[str], where: str = 'last', limit: int = 20) -> List[Dict]:
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

_attendance_db = None
def attendance_DB():
    global _attendance_db
    if _attendance_db is None:
        _attendance_db = AttendanceDB()
    return _attendance_db


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
    curr_time = datetime.now().strftime("%H:%M")
    if not records:
        return f"❌ **{employee_id}** was **NOT PRESENT** on {target_date} as of {curr_time}"
    
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