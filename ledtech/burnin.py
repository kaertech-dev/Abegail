# ledtech/burnin.py - Burn-in Board Depanel Handler
import mysql.connector
from mysql.connector import Error
from typing import Optional, Dict, List
from datetime import datetime, date
import re
from collections import defaultdict

class BurninHandler:
    """Handle queries for ledtech.burninboard_depanel table"""
    
    def __init__(self, host: str, user: str, password: str):
        self.host = host
        self.user = user
        self.password = password
        self.database = 'ledtech'
        self.table = 'burninboard_depanel'
        
        # Column schema
        self.columns = {
            'serial_num': 'VARCHAR',      # K20152590001
            'po_num': 'VARCHAR',          # 250219
            'operator_en': 'VARCHAR',     # KE0282
            'shift': 'VARCHAR',           # A, B, C
            'date_time': 'DATETIME',      # timestamp
            'panel_sn': 'VARCHAR',        # K1LTB52590001
            'series_num': 'INT'           # 1000
        }
        
        # Patterns for parsing
        self.serial_pattern = r'K\d{11}'      # K20152590001
        self.panel_pattern = r'K1LTB\d{8}'    # K1LTB52590001
        self.operator_pattern = r'KE\d{4}'    # KE0282
        self.po_pattern = r'\d{6}'            # 250219
    
    def connect(self):
        """Connect to ledtech database"""
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
            print(f"❌ Ledtech DB connection error: {e}")
            return None
    
    def search_by_serial(self, serial_num: str) -> Dict:
        """Search by serial number"""
        conn = self.connect()
        if not conn:
            return {'error': 'Database connection failed'}
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            query = f"""
                SELECT * FROM `{self.table}` 
                WHERE `serial_num` LIKE %s 
                ORDER BY `date_time` DESC
                LIMIT 100
            """
            
            cursor.execute(query, (f"%{serial_num}%",))
            records = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return {
                'search_type': 'serial',
                'search_term': serial_num,
                'count': len(records),
                'records': records
            }
            
        except Error as e:
            return {'error': f"Query error: {str(e)}"}
    
    def search_by_po(self, po_num: str) -> Dict:
        """Search by PO number"""
        conn = self.connect()
        if not conn:
            return {'error': 'Database connection failed'}
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            query = f"""
                SELECT * FROM `{self.table}` 
                WHERE `po_num` LIKE %s 
                ORDER BY `date_time` DESC
                LIMIT 100
            """
            
            cursor.execute(query, (f"%{po_num}%",))
            records = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return {
                'search_type': 'po',
                'search_term': po_num,
                'count': len(records),
                'records': records
            }
            
        except Error as e:
            return {'error': f"Query error: {str(e)}"}
    
    def search_by_operator(self, operator_en: str, date_filter: Optional[date] = None) -> Dict:
        """Search by operator"""
        conn = self.connect()
        if not conn:
            return {'error': 'Database connection failed'}
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            if date_filter:
                query = f"""
                    SELECT * FROM `{self.table}` 
                    WHERE `operator_en` LIKE %s 
                    AND DATE(`date_time`) = %s
                    ORDER BY `date_time` DESC
                    LIMIT 100
                """
                cursor.execute(query, (f"%{operator_en}%", date_filter))
            else:
                query = f"""
                    SELECT * FROM `{self.table}` 
                    WHERE `operator_en` LIKE %s 
                    ORDER BY `date_time` DESC
                    LIMIT 100
                """
                cursor.execute(query, (f"%{operator_en}%",))
            
            records = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return {
                'search_type': 'operator',
                'search_term': operator_en,
                'date_filter': date_filter,
                'count': len(records),
                'records': records
            }
            
        except Error as e:
            return {'error': f"Query error: {str(e)}"}
    
    def search_by_shift(self, shift: str, date_filter: Optional[date] = None) -> Dict:
        """Search by shift"""
        conn = self.connect()
        if not conn:
            return {'error': 'Database connection failed'}
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            if date_filter:
                query = f"""
                    SELECT * FROM `{self.table}` 
                    WHERE `shift` = %s 
                    AND DATE(`date_time`) = %s
                    ORDER BY `date_time` DESC
                    LIMIT 100
                """
                cursor.execute(query, (shift.upper(), date_filter))
            else:
                query = f"""
                    SELECT * FROM `{self.table}` 
                    WHERE `shift` = %s 
                    ORDER BY `date_time` DESC
                    LIMIT 100
                """
                cursor.execute(query, (shift.upper(),))
            
            records = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return {
                'search_type': 'shift',
                'search_term': shift.upper(),
                'date_filter': date_filter,
                'count': len(records),
                'records': records
            }
            
        except Error as e:
            return {'error': f"Query error: {str(e)}"}
    
    def get_records_by_date(self, target_date: date) -> Dict:
        """Get all burn-in records for a specific date"""
        conn = self.connect()
        if not conn:
            return {'error': 'Database connection failed'}
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            query = f"""
                SELECT * FROM `{self.table}` 
                WHERE DATE(`date_time`) = %s
                ORDER BY `date_time` DESC
            """
            
            cursor.execute(query, (target_date,))
            records = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Group by operator and shift
            by_operator = defaultdict(list)
            by_shift = defaultdict(list)
            
            for record in records:
                by_operator[record['operator_en']].append(record)
                by_shift[record['shift']].append(record)
            
            return {
                'date': target_date,
                'total_records': len(records),
                'by_operator': dict(by_operator),
                'by_shift': dict(by_shift),
                'records': records
            }
            
        except Error as e:
            return {'error': f"Query error: {str(e)}"}
    
    def get_statistics(self, date_filter: Optional[date] = None) -> Dict:
        """Get production statistics"""
        conn = self.connect()
        if not conn:
            return {'error': 'Database connection failed'}
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            if date_filter:
                # Statistics for specific date
                query = f"""
                    SELECT 
                        COUNT(*) as total_boards,
                        COUNT(DISTINCT operator_en) as unique_operators,
                        COUNT(DISTINCT po_num) as unique_pos,
                        shift,
                        COUNT(*) as shift_count
                    FROM `{self.table}` 
                    WHERE DATE(`date_time`) = %s
                    GROUP BY shift
                """
                cursor.execute(query, (date_filter,))
            else:
                # Overall statistics (last 30 days)
                query = f"""
                    SELECT 
                        COUNT(*) as total_boards,
                        COUNT(DISTINCT operator_en) as unique_operators,
                        COUNT(DISTINCT po_num) as unique_pos,
                        shift,
                        COUNT(*) as shift_count
                    FROM `{self.table}` 
                    WHERE `date_time` >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                    GROUP BY shift
                """
                cursor.execute(query)
            
            stats = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return {
                'date_filter': date_filter,
                'statistics': stats
            }
            
        except Error as e:
            return {'error': f"Query error: {str(e)}"}
    
    def format_response(self, result: Dict, query_type: str) -> str:
        """Format query results into readable response"""
        
        if 'error' in result:
            return f"❌ **Error:** {result['error']}"
        
        if query_type == 'search':
            search_type = result.get('search_type', 'general')
            count = result.get('count', 0)
            
            if count == 0:
                return f"❌ No burn-in records found for {search_type}: **{result['search_term']}**"
            
            output = f"# 🔍 Burn-in Records - {search_type.upper()} Search\n\n"
            output += f"**Search term:** {result['search_term']}\n"
            output += f"**Total records:** {count}\n\n"
            
            output += "## 📊 Records:\n\n"
            
            for idx, record in enumerate(result['records'][:20], 1):
                output += f"### {idx}. Serial: {record['serial_num']}\n"
                output += f"   - **PO Number:** {record['po_num']}\n"
                output += f"   - **Operator:** {record['operator_en']}\n"
                output += f"   - **Shift:** {record['shift']}\n"
                output += f"   - **Date/Time:** {record['date_time']}\n"
                output += f"   - **Panel SN:** {record['panel_sn']}\n"
                output += f"   - **Series:** {record['series_num']}\n\n"
            
            if count > 20:
                output += f"*Showing first 20 of {count} records*\n"
            
            return output
        
        elif query_type == 'date_summary':
            output = f"# 📅 Burn-in Production - {result['date']}\n\n"
            output += f"**Total Boards:** {result['total_records']}\n\n"
            
            output += "## 👥 By Operator:\n\n"
            for operator, records in sorted(result['by_operator'].items(), key=lambda x: len(x[1]), reverse=True):
                output += f"- **{operator}:** {len(records)} boards\n"
            
            output += "\n## 🔄 By Shift:\n\n"
            for shift, records in sorted(result['by_shift'].items()):
                output += f"- **Shift {shift}:** {len(records)} boards\n"
            
            return output
        
        elif query_type == 'statistics':
            date_info = f" for {result['date_filter']}" if result['date_filter'] else " (Last 30 days)"
            output = f"# 📈 Burn-in Statistics{date_info}\n\n"
            
            total_boards = sum(s['shift_count'] for s in result['statistics'])
            output += f"**Total Boards:** {total_boards}\n\n"
            
            output += "## 🔄 By Shift:\n\n"
            for stat in result['statistics']:
                output += f"### Shift {stat['shift']}\n"
                output += f"   - Boards: {stat['shift_count']}\n"
                output += f"   - Operators: {stat['unique_operators']}\n"
                output += f"   - PO Numbers: {stat['unique_pos']}\n\n"
            
            return output
        
        return "❓ Unknown query type"


# Singleton instance
_burnin_handler = None

def get_burnin_handler():
    """Get singleton burnin handler"""
    global _burnin_handler
    if _burnin_handler is None:
        from config import DB_HOST, DB_USER, DB_PASSWORD
        _burnin_handler = BurninHandler(DB_HOST, DB_USER, DB_PASSWORD)
    return _burnin_handler


# Convenience functions

def search_burnin_serial(serial_num: str) -> str:
    """Search burn-in records by serial number"""
    handler = get_burnin_handler()
    result = handler.search_by_serial(serial_num)
    return handler.format_response(result, 'search')


def search_burnin_po(po_num: str) -> str:
    """Search burn-in records by PO number"""
    handler = get_burnin_handler()
    result = handler.search_by_po(po_num)
    return handler.format_response(result, 'search')


def search_burnin_operator(operator_en: str, target_date: Optional[date] = None) -> str:
    """Search burn-in records by operator"""
    handler = get_burnin_handler()
    result = handler.search_by_operator(operator_en, target_date)
    return handler.format_response(result, 'search')


def search_burnin_shift(shift: str, target_date: Optional[date] = None) -> str:
    """Search burn-in records by shift"""
    handler = get_burnin_handler()
    result = handler.search_by_shift(shift, target_date)
    return handler.format_response(result, 'search')


def get_burnin_by_date(target_date: date) -> str:
    """Get burn-in production summary for a date"""
    handler = get_burnin_handler()
    result = handler.get_records_by_date(target_date)
    return handler.format_response(result, 'date_summary')


def get_burnin_statistics(target_date: Optional[date] = None) -> str:
    """Get burn-in production statistics"""
    handler = get_burnin_handler()
    result = handler.get_statistics(target_date)
    return handler.format_response(result, 'statistics')