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

CSV_PATH = "c:/Users/ai/OneDrive/Documents/project_abegail/Abegail/mcp-server-demo/mcp-server-demo/csv_files/"

class ProductionArguments:
    # get wip = schema, model, po
    # station details = schema, model, station
    # process flow = schema, model
    # list all PO, last running PO = schema, model
    # serial query = serial
    # active projects, running models = none

    def __init__(self):
        self.command = ''
        self.schema = ''
        self.model = ''
        self.station = ''
        self.po_num = ''
        self.serial = ''
        self.date_time = []
        self.cont = None
    
    def __repr__(self):
        self.cont = [self.command, self.schema, self.model, self.station, self.po_num, self.serial]
        self.cont.extend(self.date_time)
        return self.cont
    
    def __str__(self):
        self.cont = [self.command, self.schema, self.model, self.station, self.po_num, self.serial]
        self.cont.extend(self.date_time)
        return str(self.cont)
    
    def check(self):
        if (self.command == 'get wip') and self.schema != '' and self.model != '' and self.po_num != '':
            return True
        elif (self.command == 'station details') and self.schema != '' and self.model != '' and self.station != '':
            return True
        elif (self.command == 'process flow') or (self.command == 'list all PO') or (self.command == 'last running PO'):
            if self.schema != '' and self.model != '':
                return True
        elif (self.command == 'serial query') and self.serial != '':
            return True
        elif (self.command == 'active projects') or (self.command == 'running models'):
            return True
        else:
            return False  
    
    def clear(self):
        self.command = ''
        # self.num_args = ''
        self.schema = ''
        self.model = ''
        self.station = ''
        self.po_num = ''
        self.serial = ''
        self.date_time = []

prodArgs = None
def getProdArgs():
    global prodArgs
    if prodArgs is None:
        prodArgs = ProductionArguments()
    return prodArgs

class ProductionDB:
    """Handle production database operations"""
    
    def __init__(self):
        self.config = DB_CONFIG
        self.projectList = self._get_all_projects()
        self.models = {}

        conn = self.connect('INFORMATION_SCHEMA')
        cursor = conn.cursor(dictionary=True)
        for proj_name in self.projectList:
            query = """ SELECT DISTINCT `TABLE_NAME` FROM `COLUMNS` 
            WHERE `TABLE_SCHEMA` = %s
            AND `TABLE_NAME` LIKE '%_main' """
            cursor.execute(query, (proj_name,))
            modelList = [row['TABLE_NAME'].split('_')[0] for row in cursor.fetchall()]
            self.models[proj_name] = modelList
        # print(self.models)
    
    def execute(self, command: str, args: ProductionArguments):
        output = {'answer': '', 'response_type': 'KTS'}

        if 'get wip' in command:
            result, filename = self.getWIP(args.schema, args.model, args.po_num, args.date_time)
            output.update({'csv_file': filename})

        elif 'station details' in command:
            result, filename = self.getStationDetails(args.schema, args.model, args.station, args.date_time)
            output.update({'csv_file': filename})
        
        elif 'list all po' in command:
            result = self.listPO(args.schema, args.model)
        
        elif 'last running po' in command:
            result = self.getLatestPO(args.schema, args.model)

        elif 'process flow' in command:
            result = self.getProcessFlow(args.schema, args.model)
        
        elif 'active projects' in command:
            result = self.getActiveProjects()
        
        elif 'serial query' in command:
            result = self.serialQuery(args.serial)
        
        elif 'running models' in command:
            result = self.getRunningModels(args.date_time)

        else:
            result = ''

        getProdArgs().clear()
        output.update({'answer': result})
        return output
    
    def connect(self, schema: str):
        """Create database connection"""
        try:
            self.config['database'] = schema
            return mysql.connector.connect(**self.config)
        except Error as e:
            raise Exception(f"Database connection error: {e}")
    
    # ======= Private Functions ======= #
    def _get_columns(self, schema: str, model: str):
        conn = self.connect('INFORMATION_SCHEMA')
        table = f"{model}_main"
        try:
            cursor = conn.cursor()
            query = """ SELECT `COLUMN_NAME` FROM `COLUMNS` WHERE `TABLE_SCHEMA` = %s AND `TABLE_NAME` = %s """
            cursor.execute(query, (schema, table))
            columns = [d[0] for d in cursor.fetchall()]
            return columns[2:]

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
        conn = self.connect(schema)
        try:
            cursor = conn.cursor(dictionary=True)
            query = " SELECT DISTINCT `po_num`, MAX(`date_time`) as `timestamp` FROM " + f"{model}_depanel" + " GROUP BY `po_num` ORDER BY `timestamp` DESC "
            cursor.execute(query)
            return cursor.fetchall()

        finally:
            cursor.close()
            conn.close()
    
    # ======= Public Functions ======= #
    def getProcessFlow(self, schema: str, model: str):
        columns = self._get_columns(schema, model)
        return str_formatter({'schema': schema, 'model': model, 'stations': columns}, 'Process Flow')
    
    def getActiveProjects(self):
        output = self._get_all_projects()
        return str_formatter(output, 'List of Active Projects')
    
    def serialQuery(self, serial_num: str):
        # Brute-force search all active projects
        projectList = self._get_all_projects()
        for project in projectList:
            found = self._find_schema(project, serial_num)
            if found:
                break

        if found is None:
            return f'Unit with serial {serial_num} is either invalid or not part of any active projects'

        schema = found['schema']
        model = found['model']
        columns = self._get_columns(schema, model)
        
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
                # else:
                #     break
            
            return str_formatter(unit_history, f'Serial Query: {serial_num}')
        
        except Exception:
            return ''
        
        finally:
            cursor.close()
            conn.close()

    def getWIP(self, schema: str, model: str, PO_num: str, date_input: List[date], shift='A'):
        conn = self.connect(schema.lower())

        if date_input[0] == date.today().isoformat():
            date_query = ''
        elif shift == 'A':
            date_query = f"AND `date_time` <= '{date_input[0]} 19:00:00'"
        elif shift == 'B':
            offset = date.fromisoformat(date_input[0]) + timedelta(days=1)
            date_query = f"AND `date_time` <= '{offset} 07:00:00'"
        
        try:
            cursor = conn.cursor(dictionary=True)
            columns = self._get_columns(schema, model)
            batch_summary = {'schema': schema, 'model': model, 'po_num': PO_num}

            # depanel
            query = """ SELECT * FROM """ + f'{model}_depanel' + """ 
            WHERE `po_num` LIKE %s
            """ + date_query
            cursor.execute(query, (PO_num,))
            out_entries = cursor.fetchall()
            batch_summary['depanel'] = {'in': len(out_entries),
                                        'wip': 0,
                                        'fail': 0,
                                        'out': len(out_entries)}
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

            csv_data = []
            for col, values in batch_summary.items():
                if col == 'schema' or col == 'model' or col == 'po_num':
                    continue
                data = {'process': col}
                data.update(values)
                csv_data.append(data)

            filename = f'WIP_{model}_{date_input[0]}.csv'
            exportCSV(filename, csv_data)
            return str_formatter(batch_summary, f'WIP as of {date_input[0]}'), filename

        finally:
            cursor.close()
            conn.close()
    
    def getStationDetails(self, schema: str, model: str, station: str, date_input: List[date]):
        if len(date_input) > 1:
            offset = date.fromisoformat(date_input[1]) + timedelta(days=1)
            date_arg = f"AND `date_time` BETWEEN '{date_input[0]} 07:00:00' AND '{offset} 06:59:59' "
            filename = f'{model}_{station}_{date_input[0]}_{date_input[1]}.csv'
            new_date = f'{date_input[0]} to {date_input[1]}'
        else:
            offset = date.fromisoformat(date_input[0]) + timedelta(days=1)
            date_arg = f"AND `date_time` BETWEEN '{date_input[0]} 07:00:00' AND '{offset} 06:59:59' "
            filename = f'{model}_{station}_{date_input[0]}.csv'
            new_date = f'{date_input[0]}'
        
        record_summary = {'schema': schema, 'model': model, 'station': station, 'date': new_date,
                          'A': {'passed': 0, 'failed': 0},
                          'B': {'passed': 0, 'failed': 0}}

        conn = self.connect(schema)
        try:
            cursor = conn.cursor(dictionary=True)
            query = """ SELECT `serial_num`, `po_num`, `operator_en`, `shift`, `date_time`, `test_rep`, `remarks`, `status` FROM """ + f"{model}_{station}" + """ 
            WHERE `shift` = 'A' """ + date_arg
            cursor.execute(query)
            A_records = cursor.fetchall()
            A_passed = 0
            for rec in A_records:
                A_passed += int(rec['status'])
            record_summary['A'] = {'passed': A_passed, 'failed': len(A_records) - A_passed}

            query = """ SELECT `serial_num`, `po_num`, `operator_en`, `shift`, `date_time`, `test_rep`, `remarks`, `status` FROM """ + f"{model}_{station}" + """ 
            WHERE `shift` = 'B' """ + date_arg
            cursor.execute(query)
            B_records = cursor.fetchall()
            B_passed = 0
            for rec in B_records:
                B_passed += int(rec['status'])
            record_summary['B'] = {'passed': B_passed, 'failed': len(B_records) - B_passed}

            if len(A_records) + len(B_records) == 0:
                return 'No records found with the given parameters.', None
            
            record_summary['Total'] = {'passed': A_passed + B_passed, 'failed': record_summary['A']['failed'] + record_summary['B']['failed']}
            
            exportCSV(filename, A_records + B_records)
            return str_formatter(record_summary, "Station Details"), filename

        finally:
            cursor.close()
            conn.close()
    
    def getRunningModels(self, date_input: List[date]):
        if len(date_input) > 1:
            date_query = f" WHERE DATE(`date_time`) BETWEEN '{date_input[0]}' AND '{date_input[1]}' "
            date_summary = f"{date_input[0]} to {date_input[1]}"
        else:
            date_query = f" WHERE DATE(`date_time`) = '{date_input[0]}' "
            date_summary = f"{date_input[0]}"

        projectList = self._get_all_projects()
        all_summary = {'date': date_summary}
        csv_data = []
        for schema in projectList:
            schema_summary = {}
            to_csv = {'schema': schema}
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
                            to_csv.update({table: len(output)})
                    except:
                        continue
                
                cursor.close()
                conn.close()

            except Exception as e:
                # print('Exit at', schema, e)
                continue

            if len(schema_summary) > 0:
                all_summary.update({schema: schema_summary})
                csv_data.append(to_csv)

        exportCSV(f"running_models_{'_'.join(date_input)}.csv", csv_data)
        return str_formatter(all_summary, 'Running Models')

    def listPO(self, customer: str, model: str):
        po_list = self._show_all_PO(customer, model)
        if len(po_list) == 0:
            return "No purchase orders found."

        output = f"## List of PO for {customer} \n\n"
        output += f"**Model:** {model} \n\n"
        output += "<table> <tr> <th>PO Number</th> <th>Last Depanel Date</th> </tr>"
        for po in po_list:
            output += f"<tr> <td>{po['po_num']}</td> <td>{po['timestamp']}</td> </tr>"
        output += "</table>"

        return output

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

            return f"Latest PO: {recent_activity[0]['po_num']} \n\nMost recent activity: {running}"
            
        finally:
            cursor.close()
            conn.close()

# ======= Helper Functions ======= #

def str_formatter(raw_data: List|Dict|Any, data_name: str):
    output = f"## {data_name.title()} \n\n"
    if 'Process Flow' in data_name:
        output += f"**Schema:** {raw_data.pop('schema')} \n\n"
        output += f"**Model:** {raw_data.pop('model')} \n\n"

        for i, text in enumerate(raw_data['stations'], 1):
            output += f" {i}. {text} \n\n"
    
    elif 'Active Projects' in data_name:
        for i, text in enumerate(raw_data, 1):
            output += f" {i}. {text} \n\n"
    
    elif 'Running Models' in data_name:
        output += f"**Date Coverage:** {raw_data.pop('date')} \n\n"
        output += "<table><tr> <th>Customer</th> <th>Model &amp; Station</th> <th>Output</th> </tr>"
        for schema, models in raw_data.items():
            span = len(models)
            spanner = f"<td rowspan={span}>{schema}</td>"
            for key, value in models.items():
                output += "<tr>" + spanner + f"<td>{key}</td> <td>{value}</td> </tr>"
                spanner = ''
        
        output += "</table>"

    elif 'Serial Query' in data_name:
        output += f"**Schema:** {raw_data.pop('schema')} \n\n"
        output += f"**Model:** {raw_data.pop('model')} \n\n"
        table_headers = ['process', 'status', 'date_time', 'operator_en']
        output += makeTable(table_headers, raw_data)

    elif 'WIP' in data_name:
        output += f"**Schema:** {raw_data.pop('schema')} \n\n"
        output += f"**Model:** {raw_data.pop('model')} \n\n"
        output += f"**PO number:** {raw_data.pop('po_num')} \n\n"
        table_headers = ['process', 'in', 'wip', 'fail', 'out']
        output += makeTable(table_headers, raw_data)
    
    elif 'Station Details' in data_name:
        output += f"**Date Coverage:** {raw_data.pop('date')} \n\n"
        output += f"**Schema:** {raw_data.pop('schema')} \n\n"
        output += f"**Model:** {raw_data.pop('model')} \n\n"
        output += f"**Station:** {raw_data.pop('station')} \n\n"
        table_headers = ['shift', 'passed', 'failed']
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

"""
SELECT t1.`serial_num`, t2.`serial_num`, t1.`status` as `ft`, t2.`status` as `lasermarking` FROM `nanoirtag_ft` as t1 
RIGHT JOIN `nanoirtag_lasermarking` as t2 ON t1.`serial_num`=t2.`serial_num` WHERE t1.`serial_num` IS NULL
^^
dumaan na ng lasermarking but not ft


SELECT t1.`serial_num`, t2.`serial_num`, t1.`status` as `progtest`, t2.`status` as `assembly` FROM `nanoirtag_progtest` as t1
LEFT JOIN `nanoirtag_assembly` as t2 ON t1.`serial_num`=t2.`serial_num`
WHERE t2.`serial_num` IS NULL
AND t1.`serial_num` NOT LIKE "%\\_%"
AND t1.`status` = 1
^^ passed progtest but not yet in assembly
"""