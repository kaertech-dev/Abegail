import asyncio
import json
import csv
from datetime import datetime, date, time, timedelta
from typing import Any, List, Dict, Optional
import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    'host': '192.168.1.38',
    'user': 'labeling',
    'password': 'labeling',
    'database': '',
    'autocommit': True,
    'use_unicode': True,
    'charset': 'utf8mb4'
}

class ProductionDB:
    """Handle production database operations"""
    
    def __init__(self):
        self.config = DB_CONFIG
    
    def connect(self, schema: str):
        """Create database connection"""
        try:
            self.config['database'] = schema
            return mysql.connector.connect(**self.config)
        except Error as e:
            raise Exception(f"Database connection error: {e}")
        
    def _get_columns(self, cursor, model: str):
        query = f""" SELECT * FROM {model}_main LIMIT 1"""
        cursor.execute(query)
        columns = [i[0] for i in cursor.description]
        cursor.fetchall()
        return columns[2:]
    
    def getProcessFlow(self, schema: str, model: str):
        conn = self.connect(schema.lower())
        try:
            cursor = conn.cursor(dictionary=True)
            columns = self._get_columns(cursor, model)
            records = cursor.fetchall()
            process = {'schema': schema, 'model': model, 'stations': columns}

            return str_formatter(process, 'Process Flow')
        
        finally:
            cursor.close()
            conn.close()
    
    def _find_schema(self, project: str, serial_num: str):
        try:
            conn = self.connect(project)
            cursor = conn.cursor()
            cursor.execute(""" SHOW TABLES """)
            all_tables = cursor.fetchall()
            cursor.close()

            # only look in tables with main
            main_tables = [table[0] for table in all_tables if '_main' in table[0]]

            cursor = conn.cursor(dictionary=True)
            for table in main_tables:
                query = """ SELECT * FROM """ + table + """ WHERE `serial_num` = %s """
                cursor.execute(query, (serial_num,))
                row = cursor.fetchall()
                if row:
                    return {'schema': project, 'model': table, 'details': row[0]}
            
            cursor.close()
            conn.close()
            return None
        except Exception:
            return None
    
    def _get_all_projects(self, serial_num: str):
        active_projects = []
        inactive_projects = []
        conn = self.connect('projectsdb')
        try:
            cursor = conn.cursor()
            query = """ SELECT * FROM `projects` """
            cursor.execute(query)
            for entry in cursor.fetchall():
                if entry[1] == 'Active':
                    active_projects.append(entry[0])
                elif entry[1] == 'Inactive':
                    inactive_projects.append(entry[0])
            # print('List of active projects: ', active_projects)
            # print('List of inactive projects: ', inactive_projects)

        finally:
            cursor.close()
            conn.close()
        
        for project in active_projects:
            found = self._find_schema(project, serial_num)
            if found:
                return found
        
        return None
    
    def serialQuery(self, serial_num: str):
        # Brute-force search all active projects
        found = self._get_all_projects(serial_num)

        if found is None:
            return f'Unit with serial {serial_num} either does not exist or not part of any active projects'

        schema = found['schema']
        model = found['model'].replace('_main', '')
        columns = list(found['details'].keys())[2:]
        
        conn = self.connect(schema)
        try:
            cursor = conn.cursor(dictionary=True)
            unit_history = {'schema': schema, 'model': model}

            # retrieve details per station
            for station in columns:
                table_name = f'{model}_{station}'
                query = """ SELECT serial_num, status, date_time, operator_en FROM """ + table_name + """ 
                WHERE `serial_num` LIKE %s
                """
                cursor.execute(query, (serial_num,))
                row = cursor.fetchall()
                if row:
                    unit_history[station] = row[0]
                else:
                    break
            
            return str_formatter(unit_history, f'Serial Query: {serial_num}')
        
        finally:
            cursor.close()
            conn.close()

    def getWIP(self, schema: str, model: str, PO_num: str, date_input: str, shift=''):
        conn = self.connect(schema.lower())

        if date_input == date.today().isoformat():
            date_query = ''
        elif shift == 'A':
            date_query = f"AND `date_time` <= '{date_input} 19:00:00'"
        elif shift == 'B':
            offset = date.fromisoformat(date_input) + timedelta(days=1)
            date_query = f"AND `date_time` <= '{offset} 07:00:00'"
        
        try:
            cursor = conn.cursor(dictionary=True)
            columns = self._get_columns(cursor, model)
            batch_summary = {'schema': schema, 'model': model, 'po_num': PO_num}

            # depanel
            query = """ SELECT * FROM """ + f'{model}_depanel' + """ 
            WHERE `po_num` LIKE %s
            """ + date_query
            cursor.execute(query, (PO_num,))
            out_entries = cursor.fetchall()
            batch_summary['depanel'] = {'out': len(out_entries),
                                        'in': len(out_entries),
                                        'fail': 0,
                                        'wip': 0}
            prev_out = len(out_entries)

            # cumulative_query = "SELECT * FROM " + f'{model}_main' + " WHERE `po_num` = %s AND `serial_num` NOT LIKE '%\\_%'"

            # rest of the process flow
            for col in columns:
                table_name = f'{model}_{col}'
                # retrieve units that passed
                query = """ SELECT serial_num, po_num, operator_en, shift, date_time, status FROM """ + table_name + """ 
                WHERE `po_num` = %s
                AND `serial_num` NOT LIKE '%\\_%'
                AND `status` = 1
                """ + date_query
                cursor.execute(query, (PO_num,))
                out_entries = cursor.fetchall()
                batch_summary[col] = {'out': len(out_entries), 'in': prev_out}

                # retrieve units that failed
                query = """ SELECT serial_num, po_num, operator_en, shift, date_time, status FROM """ + table_name + """ 
                WHERE `po_num` = %s
                AND `serial_num` NOT LIKE '%\\_%'
                AND `status` = 0
                """ + date_query
                cursor.execute(query, (PO_num,))
                fail_entries = cursor.fetchall()
                batch_summary[col].update({'fail': len(fail_entries)})

                wip = prev_out - (len(out_entries) + len(fail_entries))
                batch_summary[col].update({'wip': wip})
                # curr_query = cumulative_query + f" AND {col} = 0"
                # cursor.execute(curr_query, (PO_num,))
                # wip_entries = cursor.fetchall()
                # batch_summary[col].update({'wip': len(wip_entries)})

                prev_out = len(out_entries)
                # cumulative_query += f" AND {col} = 1"

            return str_formatter(batch_summary, f'WIP as of {date_input}')

        finally:
            cursor.close()
            conn.close()

def str_formatter(raw_data: List|Dict|Any, data_name: str):
    output = ''
    if 'Process Flow' in data_name:
        output = f"## {data_name.title()} \n\n"
        output += f"**Schema:** {raw_data.pop('schema')} \n\n"
        output += f"**Model:** {raw_data.pop('model')} \n\n"

        for i, text in enumerate(raw_data['stations'], 1):
            output += f" {i}. {text} \n\n"

    elif 'Serial Query' in data_name:
        output = f"## {data_name.title()} \n\n"
        output += f"**Schema:** {raw_data.pop('schema')} \n\n"
        output += f"**Model:** {raw_data.pop('model')} \n\n"
        table_headers = ['process', 'status', 'date_time', 'operator_en']
        output += makeTable(table_headers, raw_data)

    elif 'WIP' in data_name:
        output = f"## {data_name} \n\n"
        output += f"**Schema:** {raw_data.pop('schema')} \n\n"
        output += f"**Model:** {raw_data.pop('model')} \n\n"
        output += f"**PO number:** {raw_data.pop('po_num')} \n\n"
        table_headers = ['process', 'in', 'wip', 'fail', 'out']
        output += makeTable(table_headers, raw_data)

    else:
        output = str(raw_data)
    
    return output

def makeTable(headers: List, data: Dict):
    head_row = ''
    contents = ''
    for h in headers:
        head_row += f"<th>{h.upper()}</th>"
    head_row = "<tr>" + head_row + "</tr>"
    
    for key, value in data.items():
        curr_row = f"<td><b>{key}</b></td>"
        for h in headers[1:]:
            curr_row += f"<td>{str(value.get(h, ''))}</td>"
        contents += "<tr>" + curr_row + "</tr>"
    
    return "<table>" + head_row + contents + "</table>"