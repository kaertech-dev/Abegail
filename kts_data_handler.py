import re
import csv
from datetime import datetime, date, time, timedelta
from typing import Any, List, Dict, Optional
import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG

CSV_PATH = "./csv_files/"

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
        # print(self)
        if self.command in ['get_wip', 'rejects', 'failure_details', 'station_details', 'raw_data', 'station_yield']:
            if self.schema and self.model and self.po_num and len(self.stationList) > 0:
                return True
        elif self.command in ['show_process_flow', 'show_purchase_orders', 'show_target_time']:
            if self.schema and self.model:
                return True
        elif (self.command == 'serial_query') and self.serial:
            return True
        elif (self.command == 'show_active_projects') or (self.command == 'show_running_models'):
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
        # print('Updated:', _prod_args_instances)
    
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
        
        elif 'rejects' in command or 'failure_details' in command:
            result = self.getRejects(args.schema, args.model, args.po_num, args.stationList)

        elif 'station_details' in command or 'raw_data' in command or 'station_yield' in command:
            result = self.getStationDetails(args.schema, args.model, args.po_num, args.stationList, args.date_time)
        
        elif 'show_purchase_orders' in command:
            result = self.listPO(args.schema, args.model)
        
        elif 'show_target_time' in command:
            result = self.showTargetTime(args.schema, args.model)

        elif 'show_process_flow' in command:
            result = self.getProcessFlow(args.schema, args.model)
        
        # elif 'show_active_projects' in command:
        #     result = self.getActiveProjects()
        
        elif 'serial_query' in command:
            result = self.serialQuery(args.serial)
        
        elif 'show_running_models' in command:
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
        if "_" in model:
            table = model
        else:
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
                query = " SELECT * FROM " + table + " WHERE `serial_num` LIKE %s "
                try:
                # SELECT t1.`date_time`, t2.* FROM `sp101_depanel` as t1 JOIN `sp101_main` as t2 ON t1.`serial_num` = t2.`serial_num` ORDER BY t1.`date_time` DESC
                    cursor.execute(query, (serial_num,))
                    row = cursor.fetchall()
                    if row:
                        model = table.split('_')[0]
                        # details = self._get_columns(project, model)
                        return {'schema': project, 'model': model, 'po_num': row[0]['po_num']}
                except Exception as e:
                    # print('some error', e)
                    continue
            
            cursor.close()
            conn.close()
            return None
        except Exception as e:
            print('some error', e)
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
            total = {}
            cursor = conn.cursor(dictionary=True)
            for col in columns:
                try:
                    query = " SELECT DISTINCT `po_num`, MAX(`date_time`) as `timestamp` FROM " + f"{model}_{col}" + " GROUP BY `po_num` ORDER BY `timestamp` DESC "
                    cursor.execute(query)
                    records = cursor.fetchall()

                    for rec in records:
                        # print(rec)
                        key = rec['po_num']
                        if key not in total:
                            total[key] = rec['timestamp']
                        else:
                            curr = total[key]
                            if curr < rec['timestamp']:
                                total[key] = rec['timestamp']
                except:
                    continue
            
            # print('TOTAL:', total)
            return [{'po_num': po, 'last_activity': tstamp} for po, tstamp in total.items() if po != '']

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
        
        try:
            conn = self.connect(schema)
        except Exception as e:
            conn.close()
            return {'preformat': str(e), 'response_type': 'Error'}
        try:
            cursor = conn.cursor(dictionary=True)
            unit_history = {}

            # Add depanel info
            try:
                query = """ SELECT serial_num, date_time, operator_en FROM """ + f'{model}_depanel' + """ 
                WHERE `serial_num` LIKE %s """
                cursor.execute(query, (serial_num,))
                row = cursor.fetchall()
                if row:
                    unit_history['depanel'] = row[0]
                    unit_history['depanel'].update({'status': '1'})
            except:
                pass

            # Retrieve details per station
            for station in columns:
                try:
                    table_name = f'{model}_{station}'
                    query = """ SELECT serial_num, status, date_time, operator_en FROM """ + table_name + """ 
                    WHERE `serial_num` LIKE %s """
                    cursor.execute(query, (serial_num,))
                    row = cursor.fetchall()
                    if row:
                        unit_history[station] = row[0]
                    else:
                        unit_history[station] = {'serial_num':'', 'status':'0', 'date_time':'n/a', 'operator_en':'n/a'}
                except:
                    unit_history[station] = {'serial_num':'', 'status':'0', 'date_time':'n/a', 'operator_en':'n/a'}
            
            filename = f"{serial_num}_{schema}_{model}.csv"
            with open(CSV_PATH + filename, 'w', newline='') as output_file:
                writer = csv.DictWriter(output_file, ['process', 'status', 'date_time', 'operator_en'], extrasaction='ignore')
                writer.writeheader()
                for station, values in unit_history.items():
                    row = {'process', station}
                    row.update(values)
                    writer.writerow(row)
            
            output = f"## Serial Query: {serial_num} \n\n"
            output += f"**Schema:** {schema} \n\n"
            output += f"**Model:** {model} \n\n"
            output += f"**PO Number:** {found.get('po_num','')} \n\n"
            table_headers = ['process', 'status', 'date_time', 'operator_en']
            output += makeTable(table_headers, unit_history)
            return {'preformat': output, 'raw_records': unit_history, 'csv_file': [filename], 'response_type': 'KTS'}
        
        except Exception as e:
            return {'preformat': str(e), 'response_type': 'Error'}
        
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def getWIP(self, schema: str, model: str, PO_num: str, station_list: list, date_input: List[str]):
        if len(date_input) == 0:
            date_query = ''
            offset = date.today() + timedelta(days=1)
            date_input = [offset.isoformat()]
        elif len(date_input) > 1:
            offset = date.fromisoformat(date_input[1]) + timedelta(days=1)
            date_query = f"AND `date_time` < '{offset} 07:00:00' "
        else:
            offset = date.fromisoformat(date_input[0]) + timedelta(days=1)
            date_query = f"AND `date_time` < '{offset} 07:00:00' "
        
        try:
            conn = self.connect(schema)
        except Exception as e:
            conn.close()
            return {'preformat': str(e), 'response_type': 'Error'}
        
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
                try:
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
                except Error as e:
                    print(e)
                    continue

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
            return {'preformat': result, 'raw_records': batch_summary, 'csv_file': [filename], 'response_type': 'KTS'}

        finally:
            if cursor:
                cursor.close()
            if conn:
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
        try:
            conn = self.connect(schema)
        except Exception as e:
            conn.close()
            return {'preformat': str(e), 'response_type': 'Error'}
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
                if len(A_records + B_records) > 0:
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

                record_summary[station] = {'A_pass': 0, 'A_fail': 0,
                                           'B_pass': 0, 'B_fail': 0}
                for rec in A_records:
                    if '_' not in rec['serial_num']:
                        if int(rec['status']) == 1:
                            record_summary[station]['A_pass'] += 1
                        else:
                            record_summary[station]['A_fail'] += 1
                for rec in B_records:
                    if '_' not in rec['serial_num']:
                        if int(rec['status']) == 1:
                            record_summary[station]['B_pass'] += 1
                        else:
                            record_summary[station]['B_fail'] += 1
                
                if len(A_records + B_records) > 0:
                    filename = f'{model}_{station}_{'-'.join(date_input)}.csv'
                    exportCSV(filename, A_records + B_records)
                    filename_comp.append(filename)
                    record_summary[station].update({'csv': filename})

            result = str_formatter(record_summary, f"Station Details for {schema} {model}")
            record_summary.update({'schema': schema, 'model': model, 'po_num': po_num, 'date': ' to '.join(date_input)})
            instr = " A and B refer to employee shifts, so 'A_pass' means units that successfully passed the station during shift A."
            return {'preformat': result, 'raw_records': record_summary, 'csv_file': filename_comp, 'instructions': instr, 'response_type': 'KTS'}
        
        except Exception as e:
            print("Error:", e)
            conn.close()
            return {'preformat': 'No records found with the given parameters.', 'response_type': 'KTS'}

        finally:
            if cursor:
                cursor.close()
            if conn:
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
        return {'preformat': result, 'raw_records': all_summary, 'csv_file': [filename], 'response_type': 'KTS'}

    def listPO(self, customer: str, model: str):
        po_list = self._show_all_PO(customer, model)
        if len(po_list) == 0:
            return {'preformat': "No purchase orders found."}

        output = f"## List of PO for {customer} \n\n"
        output += f"**Model:** {model} \n\n"
        output += "<table> <tr> <th>Purchase Order</th> <th>Last Activity</th> </tr>"
        for po in po_list:
            output += f"<tr> <td>{po['po_num']}</td> <td>{po['last_activity']}</td> </tr>"
        output += "</table>"

        # return {'answer': output, 'response_type': 'KTS'}
        return {'preformat': output, 'raw_records': po_list, 'response_type': 'KTS'}

    def getRejects(self, schema: str, model: str, PO_num: str, station_list: list):
        process_flow = self._get_columns(schema, model)
        total_failure = {}
        fail_reasons = {}
        try:
            conn = self.connect(schema)
        except Exception as e:
            return {'preformat': str(e), 'response_type': 'Error'}
        try:
            cursor = conn.cursor(dictionary=True)
            for station in station_list:
                if station not in process_flow:
                    continue
                    # return {'preformat': f"Invalid station name {station}"}
                column_ref = self._get_columns(schema, f"{model}_{station}")
                if 'fail_reason' in column_ref:
                    comments = '`fail_reason`'
                else:
                    comments = '`remarks`'
                
                if 'test_rep' in column_ref:
                    comments += ', `test_rep`'
                
                query = " SELECT `serial_num`, `po_num`, `operator_en`, `date_time`, `status`, " + f"{comments} FROM {model}_{station} " + """
                WHERE `po_num` LIKE %s AND `status` = 0 AND `serial_num` NOT LIKE "%\\_%" """
                cursor.execute(query, (PO_num,))
                records = cursor.fetchall()
                total_failure[station] = records
                fail_reasons[station] = {}
                for rec in records:
                    fr = rec.get('remarks', '') or rec.get('fail_reason', '')
                    fr = ','.join(fr.split('Fail:')).strip('.').strip()
                    if fr not in fail_reasons[station]:
                        fail_reasons[station].update({fr:1})
                    else:
                        fail_reasons[station][fr] += 1

                # query = " SELECT DISTINCT `remarks` FROM " + f" {model}_{station} " + """ WHERE `po_num` LIKE %s AND `status` = 0 AND `serial_num` NOT LIKE "%\\_%" """
                # cursor.execute(query, (PO_num,))
                # fail_reasons[station] = cursor.fetchall()
            
            formatted = f"## Failed Units in {model.title()} \n\n"
            formatted += f"**Schema:** {schema} \n\n"
            formatted += f"**Model:** {model} \n\n"
            formatted += f"**PO number:** {PO_num} \n\n"

            filename = f"{model}_{'_'.join(station_list)}_fails.csv"
            output_file = open(CSV_PATH + filename, 'w', newline='')
            writer = csv.DictWriter(output_file, ['serial_num', 'po_num', 'station', 'operator_en', 'shift', 'date_time', 'test_rep', 'remarks'], extrasaction='ignore')
            writer.writeheader()
            
            table = "<tr> <th>PROCESS</th> <th>FAILED</th> <th>REASONS</th> </tr>"
            for stat, rec in total_failure.items():
                fail_text = [f'{fr} ({ct})' for fr, ct in fail_reasons[stat].items()]
                row = f"<tr> <td><b>{stat.title()}</b></td> <td>{len(rec)}</td> <td>{'\n\n'.join(fail_text)}</td> </tr>"
                table += row
                for entry in rec:
                    entry.update({'station': stat})
                    if 'fail_reason' in entry:
                        entry['remarks'] = entry.pop('fail_reason')
                    entry.pop('status')
                    writer.writerow(entry)

            formatted += "<table>" + table + "</table>"
            
            output_file.close()
            return {'preformat': formatted, 'raw_records': total_failure, 'csv_file': [filename], 'response_type': 'KTS'}
        
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def showTargetTime(self, customer: str, model: str):
        conn = self.connect('production_plan')

        try:
            cursor = conn.cursor(dictionary=True)
            query = f""" SELECT `station`, `process_time` FROM `target_time` WHERE `customer` LIKE "%{customer.lower()}%" AND `model` LIKE "%{model.lower()}%" """
            cursor.execute(query)
            target_time = cursor.fetchall()
            cursor.close()
            return {'preformat': '', 'raw_records': target_time, 'response_type': 'KTS'}
        finally:
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
            # for entry in data:
            writer.writerows(data)
    
    elif type(data) == dict:
        with open(CSV_PATH + filename, 'w', newline='') as output_file:
            writer = csv.DictWriter(output_file, list(data.keys()), extrasaction='ignore')
            writer.writeheader()
            # for entry in data.items():
            writer.writerows(data)

tmp = {'station_details': 'status and analysis update about the output summary of a model',
        'raw_data': 'csv file with raw data of station output summary of a model',
        'show_process_flow': 'list of stations under a certain model stored as table columns',
        'serial_query': 'look for the model of a unit with the given serial number',
        'get_wip': 'input and output summary of a work-in-progress model',
        'last_running_PO': 'most recent purchase order for a model',
        'rejects': 'quantity of failed units of a given model',
        'show_purchase_orders': 'list of purchase orders for a model',
        'show_active_projects': 'list of active projects',
        'running_models': 'list of running models',
        'none_applicable': 'query outside of scope'}