import re
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

CSV_PATH = "c:/Users/ai/OneDrive/Documents/project_abegail/Abegail/mcp-server-demo/mcp-server-demo/csv_files/"

class ProductionArguments:
    def __init__(self):
        self.command = ''
        self.schema = ''
        self.model = ''
        # self.station = ''
        self.stationList = []
        self.po_num = ''
        self.serial = ''
        self.date_time = []
    
    def __repr__(self):
        self.cont = [self.command, self.schema, self.model]
        self.cont.extend(self.stationList)
        self.cont.extend([self.po_num, self.serial])
        self.cont.extend(self.date_time)
        return str(self.cont)
    
    def __str__(self):
        to_str = f"Command: {self.command} -- Schema: {self.schema} -- Model: {self.model} \n"
        to_str += f"PO Number: {self.po_num} -- Stations: {self.stationList} \n"
        to_str += f"Serial Number: {self.serial} \n"
        to_str += f"Date: {self.date_time}"
        return to_str
    
    def check(self):
        if (self.command == 'get_wip' or self.command == 'rejects' or self.command == 'station_details' or self.command == 'raw_data'):
            if self.schema and self.model and self.po_num and len(self.stationList) > 0:
                return True
        # elif (self.command == 'station details' or self.command == 'raw data') and self.schema and self.model and (self.station or self.stationList):
        #     return True
        elif (self.command == 'process_flow') or (self.command == 'list_all_PO') or (self.command == 'last_running_PO'):
            if self.schema and self.model:
                return True
        elif (self.command == 'serial_query') and self.serial:
            return True
        elif (self.command == 'active_projects') or (self.command == 'running_models'):
            return True
        else:
            return False  
    
    def clear(self):
        self.command = ''
        self.schema = ''
        self.model = ''
        # self.station = ''
        self.stationList = []
        self.po_num = ''
        self.serial = ''
        self.date_time = []

_prod_args_instances = {}
def getProdArgs(session_id) -> ProductionArguments:
    global _prod_args_instances
    
    if session_id not in _prod_args_instances:
        _prod_args_instances[session_id] = ProductionArguments()
        print('Updated:', _prod_args_instances)
    
    return _prod_args_instances[session_id]

class ProductionDB:
    """Handle production database operations"""
    
    def __init__(self):
        self.config = DB_CONFIG
        self.models = {}

        conn = self.connect('INFORMATION_SCHEMA')
        if conn is not None:
            cursor = conn.cursor(dictionary=True)
            # is depanel better? although if may depanel but no main, walang process flow
            query = """ SELECT DISTINCT `TABLE_SCHEMA`, `TABLE_NAME` FROM `COLUMNS` 
            WHERE `TABLE_NAME` LIKE '%\\_main' """
            cursor.execute(query)
            records = cursor.fetchall()
            for row in records:
                schema = row['TABLE_SCHEMA']
                model = row['TABLE_NAME'].split('_')[0]
                if schema not in self.models:
                    self.models[schema] = [model]
                else:
                    self.models[schema].append(model)
            cursor.close()
        # finally:
            # cursor.close()
            conn.close()
            # print(self.models)
    
    def detectAlias(self, user_query: str):
        word_bank = {'functional test': 'ft', 'visual inspection': 'vi', 'final visual inspection': 'fvi'}
        for word, meaning in word_bank.items():
            if word in user_query:
                user_query = user_query.replace(word, meaning)
        return user_query
    
    def execute(self, command: str, args: ProductionArguments):
        # print('entered kts handler -- ', getProdArgs())
        if 'get_wip' in command:
            result = self.getWIP(args.schema, args.model, args.po_num, args.stationList, args.date_time)
        
        elif 'rejects' in command:
            result = self.getRejects(args.schema, args.model, args.po_num, args.stationList)

        elif 'station_details' in command or 'raw_data' in command:
            result = self.getStationDetails(args.schema, args.model, args.po_num, args.stationList, args.date_time)
        
        elif 'list_all_PO' in command:
            result = self.listPO(args.schema, args.model)
        
        elif 'last_running_PO' in command:
            result = self.getLatestPO(args.schema, args.model)

        elif 'process_flow' in command:
            result = self.getProcessFlow(args.schema, args.model)
        
        elif 'active_projects' in command:
            result = self.getActiveProjects()
        
        elif 'serial_query' in command:
            result = self.serialQuery(args.serial)
        
        elif 'running_models' in command:
            result = self.getRunningModels(args.date_time)

        else:
            result = {'preformat': '', 'response_type': 'KTS'}

        if type(result) == str:
            # Final check for outputs of type string
            result = {'preformat': result, 'response_type': 'KTS'}
        
        # getProdArgs().clear()
        return result
    
    def connect(self, schema: str):
        """Create database connection"""
        try:
            self.config['database'] = schema
            return mysql.connector.connect(**self.config)
        except Error as e:
            # raise Exception(f"Database connection error: {e}")
            print(f"Database connection error: {e}")
            return None
    
    # ======= Private Functions ======= #
    def _get_columns(self, schema: str, model: str):
        conn = self.connect('INFORMATION_SCHEMA')
        table = f"{model}_main"
        try:
            cursor = conn.cursor()
            query = """ SELECT `COLUMN_NAME` FROM `COLUMNS` WHERE `TABLE_SCHEMA` = %s AND `TABLE_NAME` = %s """
            cursor.execute(query, (schema, table))
            columns = [d[0] for d in cursor.fetchall() if d[0] != 'serial_num' and d[0] != 'po_num']
            return columns

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

            # only look in depanel tables
            main_tables = [table[0] for table in all_tables if '_depanel' in table[0]]

            cursor = conn.cursor(dictionary=True)
            for table in main_tables:
                # SELECT t1.`date_time`, t2.* FROM `sp101_depanel` as t1 JOIN `sp101_main` as t2 ON t1.`serial_num` = t2.`serial_num` ORDER BY t1.`date_time` DESC
                query = """ SELECT * FROM """ + table + """ WHERE `serial_num` = %s """
                cursor.execute(query, (serial_num,))
                row = cursor.fetchall()
                if row:
                    model = table.split('_')[0]
                    # details = self._get_columns(project, model)
                    return {'schema': project, 'model': model}
            
            cursor.close()
            conn.close()
            return None
        except Exception:
            return None
    
    def _get_all_projects(self, inactive=False):
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

            if inactive:
                return active_projects + inactive_projects
            
            return active_projects

        finally:
            cursor.close()
            conn.close()
    
    def _show_all_PO(self, schema: str, model: str):
        columns = self._get_columns(schema, model)
        conn = self.connect(schema)
        try:
            cursor = conn.cursor(dictionary=True)
            query = " SELECT DISTINCT `po_num`, MAX(`date_time`) as `timestamp` FROM " + f"{model}_{columns[0]}" + " GROUP BY `po_num` ORDER BY `timestamp` DESC "
            cursor.execute(query)
            return cursor.fetchall()

        finally:
            cursor.close()
            conn.close()
    
    # ======= Public Functions ======= #
    def getProcessFlow(self, schema: str, model: str):
        columns = self._get_columns(schema, model)

        output = "## Process Flow \n\n"
        output += f"**Schema:** {schema.title()} \n\n"
        output += f"**Model:** {model.title()} \n\n"
        for i, text in enumerate(columns, 1):
            output += f" {i}. {text} \n\n"
        return {'preformat': output, 'raw_records': columns, 'response_type': 'KTS'}
    
    def getActiveProjects(self):
        projList = self._get_all_projects()

        output = "## List of Active Projects \n\n"
        for i, text in enumerate(projList, 1):
            output += f" {i}. {text} \n\n"
        return {'preformat': output, 'raw_records': projList, 'response_type': 'KTS'}
    
    def serialQuery(self, serial_num: str):
        # Brute-force search all active projects
        projectList = self._get_all_projects()
        for project in projectList:
            found = self._find_schema(project, serial_num)
            if found:
                break

        if found is None:
            output = f'Unit with serial {serial_num} is either invalid or not part of an active project'
            return {'preformat': output, 'response_type': 'KTS'}

        schema = found['schema']
        model = found['model']
        columns = self._get_columns(schema, model)
        
        conn = self.connect(schema)
        try:
            cursor = conn.cursor(dictionary=True)
            unit_history = {}

            # Add depanel info
            query = """ SELECT serial_num, date_time, operator_en FROM """ + f'{model}_depanel' + """ 
            WHERE `serial_num` LIKE %s """
            cursor.execute(query, (serial_num,))
            row = cursor.fetchall()
            if row:
                unit_history['depanel'] = row[0]
                unit_history['depanel'].update({'status': '1'})

            # Retrieve details per station
            for station in columns:
                table_name = f'{model}_{station}'
                query = """ SELECT serial_num, status, date_time, operator_en FROM """ + table_name + """ 
                WHERE `serial_num` LIKE %s """
                cursor.execute(query, (serial_num,))
                row = cursor.fetchall()
                if row:
                    unit_history[station] = row[0]
                # else:
                #     break
            
            output = f"## Serial Query: {serial_num} \n\n"
            output += f"**Schema:** {schema} \n\n"
            output += f"**Model:** {model} \n\n"
            table_headers = ['process', 'status', 'date_time', 'operator_en']
            output += makeTable(table_headers, unit_history)
            return {'preformat': output, 'raw_records': unit_history, 'response_type': 'KTS'}
        
        except Exception as e:
            return {'preformat': str(e), 'response_type': 'Error'}
        
        finally:
            cursor.close()
            conn.close()

    def getWIP(self, schema: str, model: str, PO_num: str, station_list: list, date_input: List[str]):
        if len(date_input) == 0:
            date_query = ''
            offset = date.today()
            date_input = [offset.isoformat()]
        elif len(date_input) > 1:
            offset = date.fromisoformat(date_input[1]) + timedelta(days=1)
            date_query = f"AND `date_time` < '{offset} 07:00:00' "
        else:
            offset = date.fromisoformat(date_input[0]) + timedelta(days=1)
            date_query = f"AND `date_time` < '{offset} 07:00:00' "
        
        conn = self.connect(schema.lower())
        try:
            cursor = conn.cursor(dictionary=True)
            columns = self._get_columns(schema, model)
            batch_summary = {'schema': schema, 'model': model, 'po_num': PO_num, 'date': date_input}
            po_input = f"%{PO_num}%"

            query = """ SELECT * FROM """ + f'{model}_depanel' + """ 
            WHERE `po_num` LIKE %s
            """ + date_query
            cursor.execute(query, (po_input,))
            out_entries = cursor.fetchall()
            if 'depanel' in station_list:
                batch_summary['depanel'] = {'in': len(out_entries),
                                            'wip': 0,
                                            'fail': 0,
                                            'out': len(out_entries)}
            prev_out = len(out_entries)
            prev_col = 'depanel'

            for col in columns:
                table_name = f'{model}_{col}'
                # retrieve units that passed
                query = """ SELECT serial_num, po_num, operator_en, shift, date_time, status FROM """ + table_name + """ 
                WHERE `po_num` LIKE %s
                AND `serial_num` NOT LIKE '%\\_%'
                AND `status` = 1
                """ + date_query
                cursor.execute(query, (po_input,))
                out_entries = cursor.fetchall()
                if col in station_list:
                    batch_summary[col] = {'out': len(out_entries), 'in': prev_out}

                # retrieve units that failed
                query = """ SELECT serial_num, po_num, operator_en, shift, date_time, status FROM """ + table_name + """ 
                WHERE `po_num` LIKE %s
                AND `serial_num` NOT LIKE '%\\_%'
                AND `status` = 0
                """ + date_query
                cursor.execute(query, (po_input,))
                fail_entries = cursor.fetchall()
                if col in station_list:
                    batch_summary[col].update({'fail': len(fail_entries)})
                
                query = " SELECT * FROM " + table_name + " t2 RIGHT JOIN " + f'{model}_{prev_col}' + " t1 ON t1.`serial_num`=t2.`serial_num` "
                query += f" WHERE t1.`po_num` LIKE %s AND t1.`date_time` < '{offset} 07:00:00' "
                query += f" AND (NOT t2.`date_time` < '{offset} 07:00:00' OR t2.`serial_num` IS NULL)"
                if prev_col != 'depanel':
                    query += f" AND t1.`status` = 1 "
                
                cursor.execute(query, (PO_num,))
                wip_entries = cursor.fetchall()
                if col in station_list:
                    batch_summary[col].update({'wip': len(wip_entries)})

                prev_out = len(out_entries)
                prev_col = col

            csv_data = []
            for col, values in batch_summary.items():
                if col == 'schema' or col == 'model' or col == 'po_num' or col == 'date':
                    continue
                data = {'process': col}
                data.update(values)
                csv_data.append(data)

            statlist = [st[0] for st in station_list]
            filename = f'wip_{model}_{''.join(statlist)}_{'_'.join(date_input)}.csv'
            exportCSV(filename, csv_data)
            result = str_formatter(batch_summary, f'Work in Progress')
            batch_summary.update({'schema': schema, 'model': model, 'po_num': PO_num, 'date': date_input})
            return {'preformat': result, 'raw_records': batch_summary, 'csv_file': filename, 'response_type': 'KTS'}

        finally:
            cursor.close()
            conn.close()
    
    def getStationDetails(self, schema: str, model: str, po_num: str, station_list: list, date_input: List[str]):
        if len(date_input) == 0:
            date_input = []
            date_arg = ''
        elif len(date_input) > 1:
            offset = date.fromisoformat(date_input[1]) + timedelta(days=1)
            date_arg = f" AND `date_time` BETWEEN '{date_input[0]} 07:00:00' AND '{offset} 06:59:59' "
        else:
            offset = date.fromisoformat(date_input[0]) + timedelta(days=1)
            date_arg = f" AND `date_time` BETWEEN '{date_input[0]} 07:00:00' AND '{offset} 06:59:59' "

        record_summary = {'po_num': po_num, 'date': ' to '.join(date_input)}
        filename_comp = []
        conn = self.connect(schema)
        try:
            cursor = conn.cursor(dictionary=True)
            columns = self._get_columns(schema, model)

            query = """ SELECT * FROM """ + f" {model}_depanel " + """ 
            WHERE `po_num` = %s AND `shift` = 'A' """ + date_arg + " ORDER BY `date_time` DESC "
            cursor.execute(query, (po_num,))
            A_records = cursor.fetchall()

            query = """ SELECT * FROM """ + f" {model}_depanel " + """ 
            WHERE `po_num` = %s AND `shift` = 'B' """ + date_arg + " ORDER BY `date_time` DESC "
            cursor.execute(query, (po_num,))
            B_records = cursor.fetchall()
            
            if 'depanel' in station_list:
                record_summary['depanel'] = {'A_pass': len(A_records), 'A_fail': 0, 'B_pass': len(B_records), 'B_fail': 0}
                filename = f'{model}_depanel_{'-'.join(date_input)}.csv'
                exportCSV(filename, A_records + B_records)
                filename_comp.append(filename)
                record_summary['depanel'].update({'csv': filename})

            for station in columns:
                if station not in station_list:
                    continue

                query = """ SELECT * FROM """ + f" {model}_{station} " + """ 
                WHERE `po_num` = %s AND `shift` = 'A' """ + date_arg + " ORDER BY `date_time` DESC "
                cursor.execute(query, (po_num,))
                A_records = cursor.fetchall()
                
                query = """ SELECT * FROM """ + f" {model}_{station} " + """ 
                WHERE `po_num` = %s AND `shift` = 'B' """ + date_arg + " ORDER BY `date_time` DESC "
                cursor.execute(query, (po_num,))
                B_records = cursor.fetchall()

                record_summary[station] = {'A_pass': 0, 'A_fail': len(A_records),
                                            'B_pass': 0, 'B_fail': len(B_records)}
                for rec in A_records:
                    record_summary[station]['A_pass'] += int(rec['status'])
                    record_summary[station]['A_fail'] -= int(rec['status'])
                    if '_' in rec['serial_num']:
                        record_summary[station]['A_fail'] -= 1
                for rec in B_records:
                    record_summary[station]['B_pass'] += int(rec['status'])
                    record_summary[station]['B_fail'] -= int(rec['status'])
                    if '_' in rec['serial_num']:
                        record_summary[station]['B_fail'] -= 1
                filename = f'{model}_{station}_{'-'.join(date_input)}.csv'
                exportCSV(filename, A_records + B_records)
                filename_comp.append(filename)
                record_summary[station].update({'csv': filename})

            result = str_formatter(record_summary, f"Station Details for {schema} {model}")
            record_summary.update({'schema': schema, 'model': model, 'po_num': po_num, 'date': ' to '.join(date_input)})
            return {'preformat': result, 'raw_records': record_summary, 'csv_file': ' '.join(filename_comp), 'response_type': 'KTS'}
        
        except Exception as e:
            print("Error:", e)
            conn.close()
            return {'preformat': 'No records found with the given parameters.', 'response_type': 'KTS'}

        finally:
            cursor.close()
            conn.close()
    
    def getRunningModels(self, date_input: List[str]):
        if len(date_input) == 0:
            date_query = f"WHERE DATE(`date_time`) = {date.today()}"
        elif len(date_input) > 1:
            date_query = f" WHERE DATE(`date_time`) BETWEEN '{date_input[0]}' AND '{date_input[1]}' "
        else:
            date_query = f" WHERE DATE(`date_time`) = '{date_input[0]}' "

        projectList = self._get_all_projects()
        all_summary = {'date': ' to '.join(date_input)}
        csv_data = []
        for schema in projectList:
            schema_summary = {}
            try:
                conn = self.connect(schema)
                cursor = conn.cursor()
                cursor.execute(""" SHOW TABLES """)
                all_tables = [d[0] for d in cursor.fetchall()]
                cursor.close()

                cursor = conn.cursor(dictionary=True)
                for table in all_tables:
                    try:
                        query = """ SELECT `date_time` FROM """ + table + date_query
                        cursor.execute(query)
                        output = cursor.fetchall()
                        if len(output) > 0:
                            schema_summary.update({table: len(output)})
                            csv_data.append({'schema': schema, 'table': table, 'output': len(output)})
                    except:
                        continue
                
                cursor.close()
                conn.close()

            except Exception as e:
                # print('Exit at', schema, e)
                continue

            if len(schema_summary) > 0:
                all_summary.update({schema: schema_summary})

        if len(csv_data) == 0:
            return {'preformat': "No data available", 'response_type': 'KTS'}
        
        filename = f"running_models_{'_'.join(date_input)}.csv"
        exportCSV(filename, csv_data)
        result = str_formatter(all_summary, 'Running Models')
        return {'preformat': result, 'raw_records': all_summary, 'csv_file': filename, 'response_type': 'KTS'}
        # return {'preformat': text, 'raw_records': result, 'csv_file': filename}

    def listPO(self, customer: str, model: str):
        po_list = self._show_all_PO(customer, model)
        if len(po_list) == 0:
            return {'preformat': "No purchase orders found."}

        output = f"## List of PO for {customer} \n\n"
        output += f"**Model:** {model} \n\n"
        output += "<table> <tr> <th>PO Number</th> <th>Last Depanel Date</th> </tr>"
        for po in po_list:
            output += f"<tr> <td>{po['po_num']}</td> <td>{po['timestamp']}</td> </tr>"
        output += "</table>"

        # return {'answer': output, 'response_type': 'KTS'}
        return {'preformat': output, 'raw_records': po_list, 'response_type': 'KTS'}

    def getLatestPO(self, customer: str, model: str):
        columns = self._get_columns(customer, model)
        recent_activity = []
        conn = self.connect(customer)
        try:
            cursor = conn.cursor(dictionary=True)
            # get most recent entries per process/station
            for station in columns:
                query = """ SELECT `serial_num`, `po_num`, `date_time` FROM """ + f"{model}_{station}" + " ORDER BY `date_time` DESC LIMIT 1"
                cursor.execute(query)
                records = cursor.fetchall()
                recent_activity.extend(records)
            
            # print(recent_activity)

            running = None
            for act in recent_activity:
                time_diff = datetime.now() - act['date_time']
                if time_diff.days == 0:
                    running = act['date_time']
                    break
            
            # print("Most recent PO: ", recent_activity[0]['po_num'])
            # print("Running? ", running)

            result = f"Latest PO: {recent_activity[0]['po_num']} \n\nMost recent activity: {running}"
            return {'preformat': result, 'raw_records': recent_activity, 'response_type': 'KTS'}
            
        finally:
            cursor.close()
            conn.close()

    def getRejects(self, schema: str, model: str, PO_num: str, station_list: list):
        process_flow = self._get_columns(schema, model)
        all_fails = {}
        conn = self.connect(schema)
        cursor = conn.cursor(dictionary=True)
        try:
            for station in station_list:
                if station not in process_flow:
                    return {'preformat': f"Invalid station name {station}"}

                query = " SELECT * FROM " + f" {model}_{station} " + """ WHERE `po_num` LIKE %s AND `status` = 0 AND `serial_num` NOT LIKE "%\\_%" """
                cursor.execute(query, (PO_num,))
                records = cursor.fetchall()
                all_fails[station] = records
            
            formatted = f"## Failed Units in {model.title()} \n\n"
            formatted += f"**Schema:** {schema} \n\n"
            formatted += f"**Model:** {model} \n\n"
            formatted += f"**PO number:** {PO_num} \n\n"

            filename = f"{model}_fail-units.csv"
            output_file = open(CSV_PATH + filename, 'w', newline='')
            writer = csv.DictWriter(output_file, ['serial_num', 'po_num', 'station', 'operator_en', 'shift', 'date_time', 'test_rep', 'remarks'], extrasaction='ignore')
            writer.writeheader()
            
            for stat, rec in all_fails.items():
                formatted += f"### {stat.title()}: {len(rec)} unit/s \n\n"
                if len(rec) == 0:
                    continue
                
                # formatted += f"### {stat.title()}: {len(rec)} unit/s \n\n"
                for i, entry in enumerate(rec, 1):
                    entry.update({'station': stat})
                    entry.pop('status')
                    writer.writerow(entry)
                    if i <= 10:
                        formatted += f"{i}. {entry['serial_num']} -- {entry['remarks']} \n\n"
                
                if len(rec) > 10:
                    formatted += f"* Showing 10 of {len(rec)} units * \n\n"
            
            output_file.close()
            return {'preformat': formatted, 'raw_records': all_fails, 'csv_file': filename, 'response_type': 'KTS'}
        
        finally:
            cursor.close()
            conn.close()

# ======= Helper Functions ======= #

def str_formatter(raw_data: List|Dict|Any, data_name: str):
    output = f"## {data_name} \n\n"  

    if 'Running Models' in data_name:
        output += f"**Date Coverage:** {raw_data.pop('date')} \n\n"
        output += "<table><tr> <th>Customer</th> <th>Model &amp; Station</th> <th>Output</th> </tr>"
        for schema, models in raw_data.items():
            span = len(models)
            spanner = f"<td rowspan={span}>{schema}</td>"
            for key, value in models.items():
                output += "<tr>" + spanner + f"<td>{key}</td> <td>{value}</td> </tr>"
                spanner = ''
        
        output += "</table>"

    elif 'Work in Progress' in data_name:
        output += f"**Date Coverage:** {' to '.join(raw_data.pop('date'))} \n\n"
        output += f"**Schema:** {raw_data.pop('schema')} \n\n"
        output += f"**Model:** {raw_data.pop('model')} \n\n"
        output += f"**PO number:** {raw_data.pop('po_num')} \n\n"
        table_headers = ['process', 'in', 'wip', 'fail', 'out']
        output += makeTable(table_headers, raw_data)
    
    elif 'Station Details' in data_name:
        date_cover = raw_data.get('date', 'All')
        raw_data.pop('date')
        output += f"**Date Coverage:** {date_cover} \n\n"
        output += f"**PO number:** {raw_data.pop('po_num')} \n\n"
        table_headers = ['process', 'A_pass', 'A_fail', 'B_pass', 'B_fail', 'csv']
        output += makeTable(table_headers, raw_data)

    else:
        output += str(raw_data)
    
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

def exportCSV(filename: str, data: list|dict):
    if type(data) == list:
        with open(CSV_PATH + filename, 'w', newline='') as output_file:
            writer = csv.DictWriter(output_file, list(data[0].keys()), extrasaction='ignore')
            writer.writeheader()
            for entry in data:
                writer.writerow(entry)
    
    elif type(data) == dict:
        with open(CSV_PATH + filename, 'w', newline='') as output_file:
            writer = csv.DictWriter(output_file, list(data.keys()), extrasaction='ignore')
            writer.writeheader()
            for entry in data.items():
                writer.writerow(entry)