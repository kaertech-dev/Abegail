import mysql.connector
from mysql.connector import pooling
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

database = 'database'

# Create connection pool
db_config = {
    'host': '192.168.1.38',
    'user': 'readonly_user',
    'password': 'kts@tsd2025',
    'database': 'projectsdb',
    'pool_name': 'mypool',
    'pool_size': 5
}

pool = pooling.MySQLConnectionPool(**db_config)

def get_connection():
    """Get a connection from the pool"""
    return pool.get_connection()

def format_date(date):
    """Format date to MySQL datetime string"""
    if isinstance(date, str):
        date = datetime.fromisoformat(date)
    return date.strftime('%Y-%m-%d %H:%M:%S')

def calculate_shift(hour):
    """Calculate shift based on hour"""
    return "A" if 7 < hour < 19 else "B"

async def get_attendance_logs(start_date: Optional[str] = None, limit: int = 500) -> List[Dict]:
    """Get attendance logs with optional date filter"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        where = []
        params = []
        
        if start_date:
            formatted = format_date(start_date)
            where.append('timestamp >= %s')
            params.append(formatted)
        
        where_clause = f"WHERE {' AND '.join(where)}" if where else ''
        sql = f"""
            SELECT id, employee_num, employee_name, timestamp, device_ip, created_at
            FROM attendance.raw
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT %s
        """
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return rows
    except Exception as err:
        print(f'getAttendanceLogs error: {err}')
        return []

def get_active_db() -> List[Dict]:
    """Get active database schemas"""
    try:
        global database
        database = 'projectsdb'
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(f"SELECT schemadb FROM {database}.projects WHERE status = 'active'")
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return rows
    except Exception as err:
        print(err)
        print('Acquiring active database failed. Error caught. Continue')
        return []

def get_models(db: str) -> List[str]:
    """Get models from database"""
    try:
        global database
        database = db
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"SHOW TABLES IN {database}")
        rows = cursor.fetchall()
        models = [row[0].split("_")[0] for row in rows]
        
        cursor.close()
        conn.close()
        return models
    except Exception as err:
        print(err)
        print('Acquiring models failed. Error caught. Continue')
        return []

def get_tables(db: str) -> List:
    """Get all tables from database"""
    try:
        global database
        database = db
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"SHOW TABLES IN {database}")
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return rows
    except Exception as err:
        print(err)
        print('Acquiring tables failed. Error caught. Continue')
        return []

def get_columns(db: str, table: str) -> List:
    """Get columns from a table"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(f"SHOW COLUMNS FROM {db}.{table}")
        cols = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return cols
    except Exception as err:
        print(err)
        print('No such table. Error caught. Continue')
        return []

def get_po(db: str, model: str) -> List[str]:
    """Get PO numbers for a model"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(f"SELECT po_num FROM {db}.{model}_depanel GROUP BY po_num")
        depa = cursor.fetchall()
        po_num = [po['po_num'] for po in depa]
        
        cursor.close()
        conn.close()
        return po_num
    except Exception as err:
        print(err)
        print('No PO. Error caught. Continue.')
        return []

def get_station_wip(db: str, table: str, po: str) -> Dict:
    """Get WIP for a specific station"""
    try:
        date_code = f"date_time < '{format_date(datetime.now())}'"
        table_split = table.split("_")
        main_table = table_split[0] + "_main"
        station = table_split[1]
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(f"SHOW COLUMNS FROM {db}.{main_table}")
        cols = cursor.fetchall()
        main_columns = [d['Field'] for d in cols]
        index_station = main_columns.index(station)
        
        if index_station > 2:
            sql = f"""
                SELECT COUNT(serial_num) as wip FROM {db}.{table_split[0]}_{main_columns[index_station-1]} 
                WHERE po_num = %s AND status = '1' AND {date_code} 
                AND serial_num NOT IN (
                    SELECT serial_num FROM {db}.{table_split[0]}_{main_columns[index_station]} 
                    WHERE po_num = %s AND {date_code}
                )
            """
            cursor.execute(sql, (po, po))
        else:
            sql = f"""
                SELECT COUNT(serial_num) as wip FROM {db}.{table_split[0]}_depanel 
                WHERE po_num = %s AND {date_code} 
                AND serial_num NOT IN (
                    SELECT serial_num FROM {db}.{table_split[0]}_{main_columns[2]} 
                    WHERE po_num = %s AND {date_code}
                )
            """
            cursor.execute(sql, (po, po))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return {'wip': result['wip'] if result else 0}
    except Exception as err:
        print(err)
        print('Station WIP Failed. Error caught. Continue.')
        return {'wip': ''}

def get_query(sn: str) -> Dict:
    """Query serial number across databases"""
    try:
        active_dbs = get_active_db()
        active_dbs_list = [f"'{act['schemadb']}'" for act in active_dbs]
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        sql = f"""
            SELECT table_schema as database_name, table_name 
            FROM information_schema.tables 
            WHERE table_type = 'BASE TABLE' 
            AND table_schema IN ({','.join(active_dbs_list)}) 
            AND table_name LIKE '%_depanel' 
            ORDER BY database_name, table_name
        """
        cursor.execute(sql)
        active_tables = cursor.fetchall()
        
        db_string = ', '.join([
            f"(SELECT serial_num FROM {db_table['database_name']}.{db_table['table_name']} WHERE serial_num = %s) as {db_table['database_name']}_{db_table['table_name']}"
            for db_table in active_tables
        ])
        
        cursor.execute(f'SELECT {db_string}', [sn] * len(active_tables))
        data = cursor.fetchone()
        
        keys = list(data.keys())
        values = list(data.values())
        filtered = next((i for i, v in enumerate(values) if v is not None), -1)
        
        if filtered < 0:
            cursor.close()
            conn.close()
            return {'schema': '', 'model': '', 'query': []}
        
        schema = keys[filtered].split("_")[0]
        model = keys[filtered].split("_")[1]
        
        cols = get_columns(schema, f"{model}_main")
        main_columns = [d['Field'] for d in cols]
        stations = len(main_columns) - 2
        
        queries = []
        for i in range(stations):
            sql = f"""
                SELECT status, date_time, operator_en 
                FROM {schema}.{model}_{main_columns[i+2]} 
                WHERE serial_num = %s
            """
            cursor.execute(sql, (sn,))
            result = cursor.fetchone()
            if result:
                result['process'] = main_columns[i+2]
                queries.append(result)
        
        cursor.close()
        conn.close()
        return {'schema': schema, 'model': model, 'query': queries}
    except Exception as err:
        print(err)
        print('Query Failed. Error caught. Continue')
        return {'schema': '', 'model': '', 'query': []}

def get_wip_all(db: str, model: str, po: str, date: str, shift: str) -> List[Dict]:
    """Get all WIP data for a model"""
    try:
        holder_date = datetime.fromisoformat(date)
        holder_date_tom = holder_date + timedelta(days=1)
        working_date_time_end_a = f"{date} 19:00:00"
        working_date_time_end_b = f"{holder_date_tom.strftime('%Y-%m-%d')} 07:00:00"
        
        date_code = f"date_time < '{working_date_time_end_a}'" if shift == 'a' else f"date_time < '{working_date_time_end_b}'"
        
        main_table = f"{model}_main"
        cols = get_columns(db, main_table)
        
        if not cols:
            return []
        
        main_columns = [d['Field'] for d in cols]
        stations = len(main_columns) - 2
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # OUT query
        out_parts = [f"(SELECT COUNT(*) FROM {db}.{model}_depanel WHERE po_num = %s AND {date_code}) as depanel"]
        for i in range(stations):
            out_parts.append(f"(SELECT COUNT(*) FROM {db}.{model}_{main_columns[i+2]} WHERE po_num = %s AND serial_num NOT LIKE '%\\_%' AND status = '1' AND {date_code}) as {main_columns[i+2]}")
        
        out_sql = "SELECT " + ", ".join(out_parts)
        cursor.execute(out_sql, [po] * (stations + 1))
        outs = cursor.fetchone()
        process = list(outs.keys())
        outed = list(outs.values())
        
        # FAIL query
        fail_parts = [f"(SELECT COUNT(*) FROM {db}.{model}_depanel WHERE po_num = %s AND {date_code}) as depanel"]
        for i in range(stations):
            fail_parts.append(f"(SELECT COUNT(*) FROM {db}.{model}_{main_columns[i+2]} WHERE po_num = %s AND serial_num NOT LIKE '%\\_%' AND status = '0' AND {date_code} AND serial_num NOT REGEXP '_') as {main_columns[i+2]}")
        
        fail_sql = "SELECT " + ", ".join(fail_parts)
        cursor.execute(fail_sql, [po] * (stations + 1))
        fails = cursor.fetchone()
        failures = list({**fails, 'depanel': 0}.values())
        
        # IN query
        in_parts = [
            f"(SELECT COUNT(serial_num) FROM {db}.{model}_depanel WHERE po_num = %s AND {date_code}) as depanel",
            f"(SELECT COUNT(serial_num) FROM {db}.{model}_depanel WHERE po_num = %s AND {date_code}) as {main_columns[2]}"
        ]
        for i in range(2, stations + 1):
            in_parts.append(f"(SELECT COUNT(serial_num) FROM {db}.{model}_{main_columns[i]} WHERE po_num = %s AND serial_num NOT LIKE '%\\_%' AND status = '1' AND {date_code}) as {main_columns[i+1]}")
        
        in_sql = "SELECT " + ", ".join(in_parts)
        cursor.execute(in_sql, [po] * (stations + 2))
        ins = cursor.fetchone()
        in_all_vals = list(ins.values())
        
        # WIP query
        wip_parts = [
            f"(SELECT COUNT(serial_num) FROM {db}.{model}_depanel WHERE po_num = %s AND {date_code} AND serial_num NOT LIKE '%\\_%' AND serial_num NOT IN (SELECT serial_num FROM {db}.{model}_depanel WHERE po_num = %s AND {date_code})) as depanel",
            f"(SELECT COUNT(serial_num) FROM {db}.{model}_depanel WHERE po_num = %s AND {date_code} AND serial_num NOT IN (SELECT serial_num FROM {db}.{model}_{main_columns[2]} WHERE po_num = %s AND {date_code})) as {main_columns[2]}"
        ]
        for i in range(2, stations + 1):
            wip_parts.append(f"(SELECT COUNT(serial_num) FROM {db}.{model}_{main_columns[i]} WHERE po_num = %s AND serial_num NOT LIKE '%\\_%' AND status = '1' AND {date_code} AND serial_num NOT IN (SELECT serial_num FROM {db}.{model}_{main_columns[i+1]} WHERE po_num = %s AND {date_code})) as {main_columns[i+1]}")
        
        wip_sql = "SELECT " + ", ".join(wip_parts)
        params = [po, po, po, po] + [po, po] * (stations - 1)
        cursor.execute(wip_sql, params)
        unprocs = cursor.fetchone()
        unprocs_all_vals = list(unprocs.values())
        
        cursor.close()
        conn.close()
        
        data = [
            {
                'process': process[i],
                'in': in_all_vals[i],
                'wip': unprocs_all_vals[i],
                'fail': failures[i],
                'out': outed[i]
            }
            for i in range(len(outed))
        ]
        
        return data
    except Exception as err:
        print(err)
        print('Acquiring WIP Failed. Error caught. Continue')
        return [{'process': '', 'in': '', 'wip': '', 'fail': '', 'out': ''}]

def get_row(db: str, table: str, prime_key: str, id: Any) -> Dict:
    """Get a single row from table"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(f"SELECT * FROM {db}.{table} WHERE {prime_key} = %s", (id,))
        row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        return row if row else {}
    except Exception as err:
        print(err)
        print('No such table. Error caught. Continue')
        return {}

def create_row(db: str, table: str, data: Dict) -> Dict:
    """Create a new row in table"""
    try:
        global database
        database = db
        conn = get_connection()
        cursor = conn.cursor()
        
        keys = list(data.keys())
        values = list(data.values())
        
        column_string = "(" + ", ".join(keys) + ")"
        values_string = "(" + ", ".join(["%s"] * len(values)) + ")"
        
        cursor.execute(f"INSERT INTO {database}.{table} {column_string} VALUES {values_string}", values)
        conn.commit()
        
        result = get_row(db, table, 'serial_num', data['serial_num'])
        
        cursor.close()
        conn.close()
        return result
    except Exception as err:
        print(err)
        print('No such table. Error caught. Continue')
        return {}

def edit_row(db: str, table: str, id: Any, data: Dict) -> Dict:
    """Edit a row in table"""
    try:
        global database
        database = db
        conn = get_connection()
        cursor = conn.cursor()
        
        values = list(data.values())
        cursor.execute(f"UPDATE {database}.{table} SET {values[0]} = %s WHERE serial_num = %s", (values[1], id))
        conn.commit()
        
        result = get_row(db, table, 'serial_num', id)
        
        cursor.close()
        conn.close()
        return result
    except Exception as err:
        print(err)
        print('No such table. Error caught. Continue')
        return {}

def get_user(id: int) -> Dict:
    """Get user by ID"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM users.admin WHERE id = %s", (id,))
        row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        return row if row else {}
    except Exception as err:
        print(err)
        print('No such table. Error caught. Continue')
        return {}

def create_user(user: str, password: str) -> Dict:
    """Create a new user"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("INSERT INTO users.admin (user, password) VALUES (%s, %s)", (user, password))
        conn.commit()
        user_id = cursor.lastrowid
        
        result = get_user(user_id)
        
        cursor.close()
        conn.close()
        return result
    except Exception as err:
        print(err)
        print('No such table. Error caught. Continue')
        return {}

def find_user(user: str) -> Dict:
    """Find user by username"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT password FROM users.admin WHERE user = %s", (user,))
        row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        return row if row else {}
    except Exception as err:
        print(err)
        print('No such table. Error caught. Continue')
        return {}

def log_break_event(operator_en: str, station: str, schema_name: str, action_type: str, 
                    reason: str, reason_text: str = '', leader: Optional[str] = None) -> Dict:
    """Log break/downtime event"""
    try:
        now = datetime.utcnow()
        manila_time = now + timedelta(hours=8)
        current_hour = manila_time.hour
        curr_shift = calculate_shift(current_hour)
        
        timestamp = manila_time.strftime('%Y-%m-%d %H:%M:%S')
        
        reason_code = None
        if reason == 'lunch break':
            reason_code = 999
        elif reason == 'downtime':
            try:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute('SELECT id FROM projectsdb.downtime_reasons WHERE reason_text = %s', (reason_text,))
                reason_row = cursor.fetchone()
                reason_code = reason_row['id'] if reason_row else None
                cursor.close()
                conn.close()
            except Exception as err:
                print(f'Failed to get downtime reason ID: {err}')
                reason_code = None
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO projectsdb.break_logs 
            (operator_en, station, schema_name, action_type, reason_code, reason_text, leader, timestamp, shift) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (operator_en, station, schema_name, action_type, reason_code, reason_text, leader, timestamp, curr_shift)
        )
        conn.commit()
        insert_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        return {'success': True, 'id': insert_id}
    except Exception as err:
        print(err)
        print('Break log failed. Error caught. Continue')
        return {'success': False}

def get_operator_status(operator_en: str, station: str, schema_name: str) -> Dict:
    """Get operator's current status"""
    try:
        now = datetime.utcnow()
        manila_time = now + timedelta(hours=8)
        current_hour = manila_time.hour
        current_shift = calculate_shift(current_hour)
        current_date = manila_time.strftime('%Y-%m-%d')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(
            """SELECT action_type, reason_code, reason_text, leader, timestamp 
            FROM projectsdb.break_logs 
            WHERE operator_en = %s AND station = %s AND schema_name = %s 
            AND DATE(timestamp) = %s AND shift = %s 
            ORDER BY id DESC LIMIT 1""",
            (operator_en, station, schema_name, current_date, current_shift)
        )
        row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return row if row else {'action_type': 'stop', 'reason_code': None, 'reason_text': '', 'leader': None, 'timestamp': None}
    except Exception as err:
        print(err)
        print('Get operator status failed. Error caught. Continue')
        return {'action_type': 'stop', 'reason_code': None, 'reason_text': '', 'leader': None, 'timestamp': None}

def check_operator_active_station(operator_en: str, current_station: str, current_schema: str) -> Dict:
    """Check if operator is active at another station"""
    try:
        now = datetime.utcnow()
        manila_time = now + timedelta(hours=8)
        current_hour = manila_time.hour
        current_shift = calculate_shift(current_hour)
        current_date = manila_time.strftime('%Y-%m-%d')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(
            """SELECT DISTINCT station, schema_name FROM projectsdb.break_logs 
            WHERE operator_en = %s AND DATE(timestamp) = %s AND shift = %s
            AND (station != %s OR schema_name != %s)
            AND id IN (
                SELECT MAX(id) FROM projectsdb.break_logs 
                WHERE operator_en = %s AND DATE(timestamp) = %s AND shift = %s
                GROUP BY station, schema_name
            ) AND action_type = 'start'""",
            (operator_en, current_date, current_shift, current_station, current_schema, 
             operator_en, current_date, current_shift)
        )
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if rows:
            return {
                'isActive': True,
                'activeStation': rows[0]['station'],
                'activeSchema': rows[0]['schema_name']
            }
        
        return {'isActive': False}
    except Exception as err:
        print(err)
        print('Check operator active station failed. Error caught. Continue')
        return {'isActive': False}

def get_cycle_target(po: Optional[str] = None, schema: Optional[str] = None, 
                     station: Optional[str] = None) -> int:
    """Get cycle target time"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        target_rows = []
        
        if po:
            cursor.execute(
                """SELECT process_time FROM production_plan.target_time 
                WHERE model = (SELECT model FROM production_plan.main WHERE po_num = %s LIMIT 1) 
                LIMIT 1""",
                (po,)
            )
            target_rows = cursor.fetchall()
        
        if not target_rows and schema and station:
            model_name = station.split('_')[0]
            station_name = station.split('_')[1]
            cursor.execute(
                """SELECT process_time FROM production_plan.target_time 
                WHERE customer = %s AND model = %s AND station = %s LIMIT 1""",
                (schema, model_name, station_name)
            )
            target_rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return target_rows[0]['process_time'] if target_rows else 0
    except Exception as err:
        print(err)
        print('Could not get cycle target. Error caught. Continue')
        return 0

def get_server_time() -> Dict:
    """Get server time and shift"""
    try:
        now = datetime.utcnow()
        manila_time = now + timedelta(hours=8)
        current_hour = manila_time.hour
        shift = calculate_shift(current_hour)
        
        timestamp = manila_time.strftime('%Y-%m-%d %H:%M:%S')
        
        return {'timestamp': timestamp, 'shift': shift}
    except Exception as err:
        print(err)
        print('Could not get server time. Error caught. Continue')
        return {'timestamp': None, 'shift': None}

def get_downtime_reasons() -> List[Dict]:
    """Get all downtime reasons"""
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT id, reason_text FROM projectsdb.downtime_reasons ORDER BY reason_text')
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return rows
    except Exception as err:
        print(err)
        print('Could not get downtime reasons. Error caught. Continue')
        return []

def get_shift_yield(operator_en: str, current_schema: Optional[str] = None, 
                   current_station: Optional[str] = None) -> Dict:
    """Get shift yield data for operator"""
    try:
        now = datetime.utcnow()
        manila_time = now + timedelta(hours=8)
        current_hour = manila_time.hour
        current_shift = calculate_shift(current_hour)
        current_date = manila_time.strftime('%Y-%m-%d')
        current_timestamp = manila_time.strftime('%Y-%m-%d %H:%M:%S')
        
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get first start time
        cursor.execute(
            """SELECT MIN(timestamp) as start_time FROM projectsdb.break_logs 
            WHERE operator_en = %s AND action_type = 'start' AND shift = %s AND DATE(timestamp) = %s""",
            (operator_en, current_shift, current_date)
        )
        start_rows = cursor.fetchone()
        
        # Calculate total work time
        cursor.execute(
            """SELECT 
                SUM(CASE 
                    WHEN stop_time IS NOT NULL THEN TIMESTAMPDIFF(SECOND, start_time, stop_time)
                    ELSE TIMESTAMPDIFF(SECOND, start_time, %s)
                END) as total_work_seconds
            FROM (
                SELECT 
                    b1.timestamp as start_time,
                    (SELECT MIN(b2.timestamp) FROM projectsdb.break_logs b2 
                     WHERE b2.operator_en = %s AND b2.action_type = 'stop' AND b2.timestamp > b1.timestamp 
                     AND b2.shift = %s AND DATE(b2.timestamp) = %s) as stop_time
                FROM projectsdb.break_logs b1
                WHERE b1.operator_en = %s AND b1.action_type = 'start' AND b1.shift = %s AND DATE(b1.timestamp) = %s
            ) work_intervals""",
            (current_timestamp, operator_en, current_shift, current_date, operator_en, current_shift, current_date)
        )
        work_time_rows = cursor.fetchone()
        
        station_processed_units = 0
        station_work_time = 0
        
        if current_schema and current_station:
            try:
                cursor.execute(
                    f"""SELECT COUNT(*) as units FROM {current_schema}.{current_station} 
                    WHERE operator_en = %s AND shift = %s AND DATE(date_time) = %s AND status = 1""",
                    (operator_en, current_shift, current_date)
                )
                station_units_rows = cursor.fetchone()
                station_processed_units = station_units_rows['units'] if station_units_rows else 0
                
                cursor.execute(
                    """SELECT 
                        SUM(CASE 
                            WHEN stop_time IS NOT NULL THEN TIMESTAMPDIFF(SECOND, start_time, stop_time)
                            ELSE TIMESTAMPDIFF(SECOND, start_time, %s)
                        END) as station_work_seconds
                    FROM (
                        SELECT 
                            b1.timestamp as start_time,
                            (SELECT MIN(b2.timestamp) FROM projectsdb.break_logs b2 
                             WHERE b2.operator_en = %s AND b2.action_type = 'stop' AND b2.timestamp > b1.timestamp 
                             AND b2.shift = %s AND DATE(b2.timestamp) = %s AND b2.station = %s AND b2.schema_name = %s) as stop_time
                        FROM projectsdb.break_logs b1
                        WHERE b1.operator_en = %s AND b1.action_type = 'start' AND b1.shift = %s 
                        AND DATE(b1.timestamp) = %s AND b1.station = %s AND b1.schema_name = %s
                    ) station_intervals""",
                    (current_timestamp, operator_en, current_shift, current_date, current_station, current_schema,
                     operator_en, current_shift, current_date, current_station, current_schema)
                )
                station_work_time_rows = cursor.fetchone()
                station_work_time = max(0, station_work_time_rows['station_work_seconds'] or 0)
            except Exception as err:
                print(f'Error getting station-specific data: {err}')
        
        # Get total processed units across all stations
        cursor.execute(
            """SELECT DISTINCT schema_name FROM projectsdb.break_logs 
            WHERE operator_en = %s AND DATE(timestamp) = %s""",
            (operator_en, current_date)
        )
        schemas_rows = cursor.fetchall()
        
        total_processed_units = 0
        
        for schema_row in schemas_rows:
            schema_name = schema_row['schema_name']
            try:
                cursor.execute(
                    """SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name NOT LIKE '%%_main' 
                    AND table_name NOT LIKE '%%_depanel'""",
                    (schema_name,)
                )
                tables_rows = cursor.fetchall()
                
                for table_row in tables_rows:
                    table_name = list(table_row.values())[0]
                    try:
                        cursor.execute(
                            f"""SELECT COUNT(*) as units FROM {schema_name}.{table_name} 
                            WHERE operator_en = %s AND shift = %s AND DATE(date_time) = %s AND status = 1""",
                            (operator_en, current_shift, current_date)
                        )
                        units_rows = cursor.fetchone()
                        units = units_rows['units'] if units_rows else 0
                        total_processed_units += units
                    except Exception:
                        continue
            except Exception:
                continue
        
        start_time = start_rows['start_time'] if start_rows else None
        work_seconds = max(0, work_time_rows['total_work_seconds'] or 0)
        
        cursor.close()
        conn.close()
        
        if not start_time:
            return {'startTime': None, 'workTime': 0, 'cycleTime': 0, 'processedUnits': 0}
        
        # Calculate cycle time based on current station only
        cycle_time = round(station_work_time / station_processed_units) if station_processed_units > 0 else 0
        
        return {
            'startTime': start_time,
            'workTime': work_seconds,
            'cycleTime': max(0, cycle_time),
            'processedUnits': total_processed_units
        }
    except Exception as err:
        print(err)
        print('Get shift yield failed. Error caught. Continue')
        return {'startTime': None, 'workTime': 0, 'cycleTime': 0, 'processedUnits': 0}