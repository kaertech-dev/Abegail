# attendance/attendance_processor.py - Data Processing Logic
from typing import Dict
from datetime import date, time
from collections import defaultdict

try:
    from .attendance_db import AttendanceDB
    from .attendance_config import DEFAULT_START_TIME
except ImportError:
    from attendance_db import AttendanceDB
    from attendance_config import DEFAULT_START_TIME

class AttendanceProcessor:
    """Process attendance data into structured results"""
    
    def __init__(self, db: AttendanceDB):
        self.db = db
    
    def check_presence_today(self, employee_identifier: str, target_date: date) -> Dict:
        """Check if employee is present on a specific date"""
        records = self.db.get_records_by_date(target_date, employee_identifier)
        
        print(f"🔍 DEBUG: Searching for '{employee_identifier}' on {target_date}")
        print(f"   Found {len(records)} records")
        
        if records:
            for r in records[:3]:
                print(f"   - {r['employee_name']} ({r['employee_num']}) at {r['timestamp']} - {r['location']}")
        
        if not records:
            return {
                'present': False,
                'employee_identifier': employee_identifier,
                'date': target_date,
                'records': [],
                'message': f"No records found for '{employee_identifier}' on this date"
            }
        
        # Group by employee if multiple matches
        by_employee = defaultdict(list)
        for record in records:
            key = f"{record['employee_name']} ({record['employee_num']})"
            by_employee[key].append(record)
        
        return {
            'present': True,
            'employee_identifier': employee_identifier,
            'date': target_date,
            'matches': len(by_employee),
            'employees': dict(by_employee),
            'total_records': len(records)
        }
    
    def get_attendance_by_date(self, target_date: date, employee_identifier: str = None) -> Dict:
        """Get attendance records for a specific date"""
        records = self.db.get_records_by_date(target_date, employee_identifier)
        
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
    
    def get_attendance_range(self, start_date: date, end_date: date, 
                            employee_identifier: str = None) -> Dict:
        """Get attendance records for a date range"""
        records = self.db.get_records_by_range(start_date, end_date, employee_identifier)
        
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
    
    def count_present_operators(self, target_date: date, 
                               start_time: time = DEFAULT_START_TIME) -> Dict:
        """Count operators present after a specific time"""
        operators = self.db.get_operators_present(target_date, start_time)
        
        return {
            'date': target_date,
            'start_time': start_time.strftime('%H:%M'),
            'count': len(operators),
            'operators': operators
        }
    
    def get_absent_employees(self, target_date: date) -> Dict:
        """Get list of employees absent on a specific date"""
        all_employees = self.db.get_all_employees()
        present_employees = self.db.get_present_employees(target_date)
        
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
    
    def get_latest_entries(self, limit: int = 10) -> Dict:
        """Get latest attendance entries"""
        records = self.db.get_latest_entries(limit)
        
        return {
            'latest_entries': records,
            'count': len(records)
        }