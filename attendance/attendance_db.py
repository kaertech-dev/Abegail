# attendance/attendance_db.py - Database Connection Handler
import mysql.connector
from mysql.connector import Error
from typing import Optional
from datetime import date, time
from collections import defaultdict

try:
    from .attendance_config import (
        DATABASE_NAME, TABLE_NAME, LIST_TABLE, CHECKIN_TYPES,
        format_record_with_location
    )
except ImportError:
    from attendance_config import (
        DATABASE_NAME, TABLE_NAME, LIST_TABLE, CHECKIN_TYPES,
        format_record_with_location
    )

class AttendanceDB:
    """Handle database connections and queries"""
    
    def __init__(self, host: str, user: str, password: str):
        self.host = host
        self.user = user
        self.password = password
        self.database = DATABASE_NAME
    
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
    
    def get_records_by_date(self, target_date: date, employee_identifier: str = None) -> list:
        """Get attendance records for a specific date"""
        conn = self.connect()
        if not conn:
            return []
        
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
            records = [format_record_with_location(r) for r in records]
            
            cursor.close()
            conn.close()
            
            return records
            
        except Error as e:
            print(f"❌ Query error: {e}")
            return []
    
    def get_records_by_range(self, start_date: date, end_date: date, 
                            employee_identifier: str = None) -> list:
        """Get attendance records for a date range"""
        conn = self.connect()
        if not conn:
            return []
        
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
            records = [format_record_with_location(r) for r in records]
            
            cursor.close()
            conn.close()
            
            return records
            
        except Error as e:
            print(f"❌ Query error: {e}")
            return []
    
    def get_operators_present(self, target_date: date, start_time: time) -> list:
        """Get operators who clocked in after a specific time"""
        conn = self.connect()
        if not conn:
            return []
        
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
            
            operators = [format_record_with_location(op) for op in operators]
            
            cursor.close()
            conn.close()
            
            return operators
            
        except Error as e:
            print(f"❌ Query error: {e}")
            return []
    
    def get_all_employees(self) -> list:
        """Get all employees from the list table"""
        conn = self.connect()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT DISTINCT employee_name, employee_num
                FROM `list`
                ORDER BY employee_name
            """)
            employees = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return employees
            
        except Error as e:
            print(f"❌ Query error: {e}")
            return []
    
    def get_present_employees(self, target_date: date) -> list:
        """Get employees present on a specific date"""
        conn = self.connect()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT DISTINCT employee_name, employee_num
                FROM `raw`
                WHERE DATE(`timestamp`) = %s
            """, (target_date,))
            employees = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return employees
            
        except Error as e:
            print(f"❌ Query error: {e}")
            return []
    
    def get_latest_entries(self, limit: int = 10) -> list:
        """Get latest attendance entries"""
        conn = self.connect()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT * FROM `raw` 
                ORDER BY `timestamp` DESC 
                LIMIT %s
            """
            cursor.execute(query, (limit,))
            records = cursor.fetchall()
            
            records = [format_record_with_location(r) for r in records]
            
            cursor.close()
            conn.close()
            
            return records
            
        except Error as e:
            print(f"❌ Query error: {e}")
            return []