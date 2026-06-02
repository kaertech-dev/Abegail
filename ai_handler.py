# ai_handler.py - Enhanced with GPU Optimization
import subprocess
import os
import re
import csv
import json
import spacy
from datetime import date, datetime, time
from typing import List, Optional, Dict, Any
from date_parser import extractDate
from mcp_activity_server import ActivityAPI, ActivityDB
from mcp_attendance_server import attendance_DB
from kts_data_handler import ProductionDB, getProdArgs

# DEFAULT_MODEL = 'deepseek-r1:14b'
DEFAULT_MODEL = 'deepseek-r1:8b'

path_name = './csv_files/'
nlp = spacy.load("en_core_web_md")
ktsData = ProductionDB()

departments = ['Top Management',
            'Manufacturing', 'Quality Regulatory Affairs & EHS',
            'Business Development', 'HR & Admin',
            'Supply Chain Management', 'Facilities & Maintenance',
            'Information Technology', 'Research & Development',
            'Accounting', 'Finance & Administration']

dept_alias = {'Quality Regulatory Affairs & EHS': ['QA', 'Quality Affairs'],
             'HR & Admin': ['HR', 'Human Resources'],
             'Supply Chain Management': ['Supply Chain', 'Logistics'],
             'Information Technology': ['IT'],
             'Research & Development': ['Research', 'R&D'],
             'Finance & Administration': ['Finance', 'Budgeting']}

def handler_deepseek(prompt: str, model_name: str = DEFAULT_MODEL, transparent=False):
    # MODEL_NAME = _get_model_name()
    try:
        # GPU optimization: ensure GPU is used
        env = os.environ.copy()
        env['OLLAMA_NUM_GPU'] = '1'
        
        process = subprocess.Popen(
            ["ollama", "run", model_name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env
        )

        # Shorter timeout for general questions
        # timeout = 45 if "1.5b" in model_name else 60
        stdout, stderr = process.communicate(input=prompt)
        
        if process.returncode != 0:
            return "Sorry, there was an error."

        output_txt = stdout.strip()
        if transparent:
            print('REASONING:', output_txt)
        return clean_response(output_txt) if output_txt else "No response generated."

    except subprocess.TimeoutExpired:
        process.kill()
        return "⏱️ Request timeout."
    except FileNotFoundError:
        return "❌ Ollama not running."
    except Exception as e:
        return f"Error: {str(e)}"

def code_to_name(KE_number: str):
    KE_number = KE_number.replace('ll', 'ke')
    employee_list = attendance_DB().employees
    for emp in employee_list:
        if emp['employee_num'].lower() == KE_number.lower():
            return emp['employee_name']
    return KE_number

def fetch_actprod(question: str, date_input: List[str]):
    global activity_records

    # Set date filters for api endpoint
    if not date_input:
        date_input = extractDate(question)
    curr_date = date_input[0]
    
    act_filters = f'?start_date={curr_date}&end_date={curr_date}'
    # act_filters = api_date + f"&customer={new_filters.get('schema','')}&model={new_filters.get('model','')}"
    prod_filters = f'?day={curr_date}'

    # Retrieve records from api
    activityService = ActivityAPI()
    actDatabase = ActivityDB()

    api_ok = False
    prod_ok = (curr_date != date.today().isoformat())
    for fail_ctr in range(5):
        if not api_ok:
            api_response = activityService.get_all_data(act_filters)
            if api_response['success']:
                api_ok = True
        
        if not prod_ok:
            prod_response = activityService.get_productivity(prod_filters)
            if prod_response['success']:
                prod_ok = True
        
        if api_ok and prod_ok:
            break

    # If Activity API fetch fails, return with timeout
    if not api_ok:
        activity_records = {}
        print("API failed after 3 times. Returning...")
        return False
    
    records = api_response['data']['records']
    util_summary = {}
    if prod_ok and (curr_date == date.today().isoformat()):
        util_records = prod_response['data']['records']

        # Summarize util% for easier retrieval later
        for ur in util_records:
            if KE_match := re.search(r'(KE|LL)\d{4}(?!\d)', ur['operator_en'], re.IGNORECASE):
                ur['operator_en'] = code_to_name(KE_match.group(0).lower())
            key = flatten(ur['operator_en'])
            mod_stt = f'{ur['Model'].lower()}_{ur['Station'].lower()}'
            if key not in util_summary:
                util_summary[key] = {mod_stt: ur['%UTIL']}
            else:
                util_summary[key].update({mod_stt: ur['%UTIL']})
        
        # print(util_summary)
    
    for r in records:
        # Remove serial numbers
        r.pop('serial_num')
        # Replace KE numbers in name column for consistency
        if KE_match := re.search(r'(KE|LL)\d{4}', r['Operator'], re.IGNORECASE):
            r['Operator'] = code_to_name(KE_match.group(0))
        # Replace Orange Target with Near Target
        if r['Status'].lower() == 'orange target':
            r['Status'] = 'NEAR TARGET'
        # Retrieve utilization rate
        op_flat = flatten(code_to_name(r['operator_code'].lower()))
        util_dict = util_summary.get(op_flat)
        if util_dict:
            key = f'{r['Model'].lower()}_{r['Station'].lower()}'
            r['Util(%)'] = util_dict.get(key)
        # Rename Target to Target Cycle Time
        r['Target Cycle Time(s)'] = r.pop('Target(s)')
    
    activity_records = {'date': curr_date, 'records': records}
    print('RECORDS:', len(records))
    return True
    
def activity_handler(tool_call: str, param_list: Dict[str, List]) -> dict[str, Any]:
    if tool_call == 'allowed_stations':
        actdb = ActivityDB()
        # get_op = re.search(r'persons=\s*\[(.+)\]\s*(?!date=)', handler_response)
        return actdb.qualified_stations(param_list.get('operator', []), param_list.get('station', []))

    curr_date = activity_records.get('date')
    records = activity_records.get('records')
    
    # Prepare csv file for writing
    if param_list.get('customer'):
        filename = 'activity_' + param_list['customer'][0] + '_' + curr_date + '.csv'
    else:
        filename = 'activity_' + curr_date + '.csv'
    csvfile = open(path_name + filename, 'w', newline='', encoding='utf-8')
    writer = csv.DictWriter(csvfile, fieldnames=
                            ['Customer', 'Model', 'Station', 'Operator', 'operator_code', 'Output', 'Cycle Time(s)', 'Target(s)', 'Start Time', 'End time', 'Status', 'Util(%)'],
                            extrasaction='ignore')
    writer.writeheader()
    writer.writerows(records)

    # Pre-process the records for easier parsing by Deepseek, and write to csv
    # empty_params = [len(value) for value in param_list.values() if len(value) != 0]
    # filtered_records = []
    # for r in records:
    #     writer.writerow(r)
    #     for par, value, in param_list.items():
    #         if r.get(par.title(), '') in value:
    #             filtered_records.append(r)
    #             break
    
    # if empty_params:
    #     records = filtered_records

    # print('Filtered --', filtered_records)
    instructions = """Include all details for all applicable entries. Lower cycle time than target is good. No cycle time or target is 'on target' by default.
    Utilization rate is how much time they spent working at a given station across their whole shift. Lower utilization early in the shift is expected."""

    if len(records) > 0:
        return {'preformat': '', 'csv_file': filename, 'raw_records': records, 'instructions': instructions}
    else:
        return {'preformat': "No records in the database for the given date and parameters.", 'raw_records': []}

def attendance_handler(question: str, tool_call: str, param_list: Dict[str, List], date_input: List[str]) -> dict[str, Any]:
    result = []
    filename = ''
    chartable = False
    if not date_input:
        date_input = extractDate(question)

    names = []
    for values in param_list.values():
        for val in values:
            names.append(val.lower().replace(' ', '-'))
    
    if r'employee_info' in tool_call:
        result = attendance_DB().find_person(param_list)
        text = 'No matches found in employee database.'
        if len(result) > 0:
            text = '# Employee Matches \n\n'
            for i, r in enumerate(result, 1):
                text += f"{i}. {r['employee_name']} ({r['employee_num']}) -- {r['department']} \n"
                text += f" - {r['job_title']} \n\n"
        return {'preformat': text, 'raw_records': result}
    
    elif r'attendance' in tool_call:
        print('paramlist', param_list)
        result = attendance_DB().get_attendance(date_input, param_list)
        # separate csv files for employees and for department?
        filename = f"ATT_{'_'.join(names)}_{'_'.join(date_input)}.csv"
        if len(date_input) > 1:
            chartable = True
    
    # print("Records: ", result)
    if len(result) == 0:
        return {'preformat': 'No records in the database for the given date and parameters.', 'raw_records': []}
    
    csvfile = open(path_name + filename, 'w', newline='', encoding='utf-8')
    writer = csv.DictWriter(csvfile, fieldnames=['employee_name', 'employee_num', 'department', 'timestamp', 'device_ip'], extrasaction='ignore')
    writer.writeheader()

    text = '# Attendance Records \n\n'
    for i, rec in enumerate(result, 1):
        if i <= 10:
            text += f'{i}. **{rec['employee_name']}** ({rec['employee_num']}) -- {rec['timestamp']} \n\n'
        writer.writerow(rec)
    
    if len(result) > 10:
        text += f"\n*Showing first 10 of {len(result)} records* \n\n"

    instructions = """Work hours can start between 07:00 and 10:00. Employees must log in BEFORE those times.
    Work hours can end between 16:00 and 19:00. Employees log out AFTER those times.
    Some employees from Manufacturing department work from 07:00 until 19:00."""
    return {'preformat': text, 'raw_records': result, 'instructions': instructions, 'csv_file': filename, 'with_chart': chartable}

def kts_handler(question: str, session_id: str):
    # For commands with no arguments needed
    if getProdArgs(session_id).check():
        return ktsData.execute(getProdArgs(session_id).command, getProdArgs(session_id))

    q_alt = question.replace(' ', '')
    # Search query for given schema and model
    for schema, models in ktsData.models.items():
        if ' '+schema in question or schema in q_alt or getProdArgs(session_id).schema == schema:
            getProdArgs(session_id).schema = schema
            if not getProdArgs(session_id).model:
                for mod in models:
                    if mod in question.split() or mod+' ' in question:
                        getProdArgs(session_id).model = mod
    
    # If no schema, try to look for model directly
    if not getProdArgs(session_id).schema:
        for schema, models in ktsData.models.items():
            found_models = [mod for mod in models if (mod in question) or (mod in q_alt)]
            if found_models and not getProdArgs(session_id).model:
                getProdArgs(session_id).model = found_models[0]
                getProdArgs(session_id).schema = schema
    
    # If schema was found but still no model, show user a list of models under that schema
    if getProdArgs(session_id).schema and not getProdArgs(session_id).model:
        models = ktsData.models[getProdArgs(session_id).schema]
        error = f"Select {getProdArgs(session_id).schema} model to view for {getProdArgs(session_id).command}: \n\n" + ', '.join(models)
        return {'answer': error, 'response_type': 'KTS'}

    # print("After schema/model check:", getProdArgs(session_id))
    if not getProdArgs(session_id).schema:
        getProdArgs(session_id).clear()
        return {'answer': f"Schema is either missing or not an active project.", 'response_type': 'KTS'}
    
    if getProdArgs(session_id).command == 'get_wip' or getProdArgs(session_id).command == 'rejects' or getProdArgs(session_id).command == 'station_details' or getProdArgs(session_id).command == 'raw_data':
        if getProdArgs(session_id).model and not getProdArgs(session_id).po_num:
            # Search query for PO argument
            po_list = ktsData._show_all_PO(getProdArgs(session_id).schema, getProdArgs(session_id).model)
            # print('Available PO:', po_list)
            found_po = [po_num['po_num'] for po_num in po_list if po_num['po_num'] in question]
            if found_po:
                getProdArgs(session_id).po_num = found_po[0]
            else:
                getProdArgs(session_id).po_num = po_list[0]['po_num']
        
        if getProdArgs(session_id).model and not getProdArgs(session_id).stationList:
            # Search query for station argument
            question = ktsData.detectAlias(question)
            process_list = ktsData._get_columns(getProdArgs(session_id).schema, getProdArgs(session_id).model)
            if not process_list:
                getProdArgs(session_id).clear()
                return {'answer': 'No stations in the database.', 'response_type': 'KTS'}
            
            if getProdArgs(session_id).command != 'rejects':
                process_list.insert(0, 'depanel')

            # If multiple stations, split them into a list
            inputs = [q.strip(',') for q in question.split()]
            if len(inputs) == 1:
                inputs = [q.strip() for q in question.split(',')]
            
            found_proc = [val for val in process_list if (' '+val in question) or (val in inputs)]
            # print(found_proc)
            if found_proc:
                getProdArgs(session_id).stationList = found_proc
            # elif 'all station' in question.lower() or not found_proc:
            else:
                getProdArgs(session_id).stationList = process_list
                # print(process_list)

    if getProdArgs(session_id).check():
        # Final argument check
        # print('Execute:', getProdArgs(session_id))
        output = ktsData.execute(getProdArgs(session_id).command, getProdArgs(session_id))
        output.update({'instructions': """Query is already answered by formatted data. Provide a brief summary of the records in 2-3 sentences.
                       No need to repeat the full data again. Comment on the number of units instead."""})
        getProdArgs(session_id).clear()
        return output
        # return {'preformat': text, 'raw_records': result, 'csv_file': filename}
    else:
        # If query fails the final argument check, it's most likely not a KTS query
        getProdArgs(session_id).clear()
        return {'preformat': ''}

def ask_general_question(question: str, context: List, session_id: Optional[str]):
    """Query handler with reasoning"""

    KTS_keywords = {'station details': 'status and analysis update about the output summary of a model',
                    'raw data': 'csv file with raw data of station output summary of a model',
                    'process flow': 'list of manufacturing stations under a certain model',
                    'get wip': 'input and output summary of a work-in-progress model',
                    'last running PO': 'most recent purchase order for a model',
                    'rejects': 'quantity of failed units of a given model',
                    'list all PO': 'list of purchase orders for a model',
                    'active projects': 'list of active projects',
                    'running models': 'list of running models',
                    'none applicable': 'query outside of scope'}
    
    addtl_keywords = {'individual_attendance': 'attendance of an employee',
                      'latest_entries': 'get the latest attendance records from the database',
                      'department_headcount': 'list present employees under a given department',
                      'employee_data': 'return the name, KE number, and department of an employee',
                      'production_data': 'retrieve data regarding customers and models currently in production',
                      'operator_activity': 'productivity details such as assigned station, output, cycle time versus target, and utilization of an operator'}
    
    # context_section = f" Recent conversation: {context}\n" if context else ""

    K_serial = re.search(r'K(\d{11})', question) or re.search(r'KLLM(\d{8})', question)
    if K_serial:
        getProdArgs(session_id).command = 'serial query'
        getProdArgs(session_id).serial = K_serial.group(0)
    
    handler_response = {}
    tool_call = ''
    name_call = ''
    query_type = 'general'

    question = detectAlias(question)

    past = "Past messages:"
    for cont in context[-2:]:
        past += str(cont)

    kts_prompt = past + f"""Current message: {question} 
    List of Intents with Description: {KTS_keywords | addtl_keywords} 
    Instruction: Determine the intent of the user from the list of options, as well as the given employee name if applicable. Be concise and output only what is needed.
    Answer format: Tool= Employee="""
    if getProdArgs(session_id).command:
        handler_response = kts_handler(question)
        return handler_response
    else:
    # Determine scope, intent, and employee name if applicable
        handler = handler_deepseek(kts_prompt).lower()
        print('Determined intent: ', handler)
    # Parse the tool call determined by Deepseek
    if get_tool := re.search(r'Tool=\s*(\w+)', handler, re.IGNORECASE):
        tool_call = get_tool.group(1)
    
    # Parse the employee name determined by Deepseek
    if get_name := re.search(r'Employee=\s*(\w+.+)', handler, re.IGNORECASE):
        name_call = get_name.group(1).lower()
    if get_KE := re.search(r'(?!<\w)(KE|LL)(\d{1,4})', question, re.IGNORECASE):
        digits = get_KE.group(2)
        while len(digits) < 4:
            digits = '0' + digits
        name_call = 'KE' + digits
    
    # Attendance Query
    if 'individual_attendance' in tool_call or 'department_headcount' in tool_call or 'latest_entries' in tool_call or 'employee_data' in tool_call:
        query_type = 'attendance'
        getProdArgs(session_id).clear()
        handler_response = attendance_handler(question, tool_call, name_call)
    # Activity Query
    elif 'production_data' in tool_call or 'operator_activity' in tool_call:
        query_type = 'activity'
        getProdArgs(session_id).clear()
        handler_response = activity_handler("Current query: " + question, name_call)
        if handler_response.get('answer'):
            return handler_response
    # KTS Query or general
    else:
        for key in KTS_keywords.keys():
            if key.lower() in handler:
                getProdArgs(session_id).command = key
                if not getProdArgs(session_id).date_time:
                    getProdArgs(session_id).date_time = extractDate(question, None)
                handler_response = kts_handler(question)
                query_type = 'KTS'
        # if kts_result is not None and kts_result != {}:
        #     return kts_result
    
    # getProdArgs(session_id).clear()
    reduced_context = ''
    for cont in context[-5:]:
        reduced_context += str(cont)
    full_prompt = f"""
Today is {date.today()}.
Your name is Abigail, an informative and helpful AI assistant of a manufacturing company. Be friendly, conversational, and concise.
Answer the current query based on the given contexts. Prioritize records over previous conversations as source of information. Respond honestly if unsure about the answer.

Previous conversations: {reduced_context}
Records: {handler_response.get('raw_records')}
{handler_response.get('instructions', '')}
Current query: {question}
"""
    result = handler_deepseek(full_prompt)
    print('HANDLER:', result)
    final_output = {'answer': handler_response.get('preformat', '') + '\n\n' + remove_ansi(result), 'response_type': query_type}
    if 'with_chart' in handler_response:
        final_output['with_chart'] = handler_response.get('with_chart')
    if 'csv_file' in handler_response:
        final_output['csv_file'] = handler_response.get('csv_file')
    
    # print('final output:', final_output)
    return final_output

KTS_keywords = {'station_details': 'status and analysis update about the output summary of a model',
                'raw_data': 'csv file with raw data of station output summary of a model',
                'show_process_flow': 'list of stations under a certain model stored as table columns',
                'serial_query': 'look for the model of a unit with the given serial number',
                'get_wip': 'input and output summary of a work-in-progress model',
                # 'last_running_PO': 'most recent purchase order for a model',
                'rejects': 'quantity of failed units of a given model',
                'show_purchase_orders': 'list of purchase orders for a model',
                'show_active_projects': 'list of active projects',
                # 'running_models': 'list of running models',
                'none_applicable': 'query outside of scope'}

addtl_keywords = {'employee_info': 'return the name, employee number, department, and division of an individual',
                  'attendance': 'retrieve daily attendance logs for a person or department',
                  'operator_activity': 'productivity details of operators such as station, output, cycle time, target time, and utilization rate',
                  'allowed_stations': 'list of stations that an employee is qualified to operate'}

def getIntent(question: str, context: list, session_id: str) -> str:
    K_serial = re.search(r'K(\d{11})', question) or re.search(r'KLLM(\d{8})', question)
    if K_serial:
        getProdArgs(session_id).command = 'serial query'
        getProdArgs(session_id).serial = K_serial.group(0)
    
    handler_response = ''
    print('## ----- SCOPE ----- ##')

    today = datetime.today()
    wd = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    intent_prompt = f"""Today is {wd[today.weekday()]}, {today}.
Previous conversation: {context}
Current query: {question}
List of Intents with Description: {KTS_keywords | addtl_keywords}
Instructions:
1. Determine the intent of the current query from the list of options.
2. Determine the date (or date range) of interest from the query. Output in YYYY-MM-DD format inside a Python list.
For date range, only include the start and end. If no year was given, assume current year. If the query does not contain any dates, use empty list. 
3. Determine the names of people in the query. Output them in a Python list. If no names, use empty list.
Be concise and output only what is needed.
Answer format: Intent= Date=[] Persons=[]"""
    
    # Determine intent, date, and names of interest
    handler_response = handler_deepseek(intent_prompt).lower()
    print('Response:', handler_response)

    intent = ''
    if get_tool := re.search(r'intent=\s*(\w+)', handler_response):
        intent = get_tool.group(1)
    
    param_list = []
    # Employee Info Query
    if 'employee_info' in intent:
        param_list = ['employee_name', 'employee_num', 'department', 'division', 'job_title']
        query_type = 'attendance'
    elif 'attendance' in intent:
        param_list = ['employee_name', 'employee_num', 'department', 'order']
        query_type = 'attendance'
    # Activity Query
    elif 'operator_activity' in intent or 'allowed_stations' in intent:
        param_list = ['customer', 'model', 'station', 'operator']
        query_type = 'activity'
    # General
    elif 'none_applicable' in intent or not intent:
        query_type = 'general'
    # KTS Query
    else:
        param_list = ['customer', 'model', 'station', 'PO_num', 'serial_num']
        query_type = 'KTS'

    return {'message': handler_response, 'tool_call': intent, 'param_list': param_list, 'response_type': query_type}

def get_params(question: str, handler: Dict[str, str], param_list: list):
    if handler['response_type'] == 'KTS' or handler['response_type'] == 'activity':
        addtl_context = f"Active customers and models: {ktsData.models}"
    else:
        addtl_context = ''
    
    param_prompt = f"""User query: {question}
Tool = {handler['tool_call']}
{addtl_context}
Parameters = {param_list}
Instructions: For every parameter in the list, determine its value or values from the user query and put them in a Python list.
Include all parameters even if it has no value, in which case put an empty list. Do NOT exclude parameters from the output.
Output in Python dictionary with the parameters as keys. Use double quotes for the strings.
Example: {{"customer": ["tagntrac"], "model": ["templogger"], "station": ["progtest", "assembly2"]}}"""
    param_result = remove_ansi(handler_deepseek(param_prompt))
    print('PARAM CHECK:', param_result)
    try:
        sb = param_result.find('{') 
        eb = param_result.find('}')
        if sb != -1 and eb != -1:
            result = json.loads(param_result[sb:eb+1])
            print('JSON --', result)
            return result
    except:
        final = {}
        newreg = re.findall(r'"(\w+)":\s*\[([a-zA-Z0-9,"\s]+)\]', param_result)
        for nr in newreg:
            key = nr[0]
            values = re.findall(r'"([a-zA-Z0-9\s_]+)"', nr[1])
            final[key] = [val.lower() for val in values]
        print('REGEX --', final)
        return final

def getData(question: str, handler: dict, session_id: str) -> dict[str, str]:
    handler_response = {}
    query_type = handler['response_type']
    tool_call = handler['tool_call']
    param_list = handler.get('param_list')
    date_list = []

    # Parse the date/range determined by Deepseek
    if date_p := re.search(r'date=\s*\[(.+)\]', handler['message'], re.IGNORECASE):
        date_list = re.findall(r'\d{4}-\d{2}-\d{2}', date_p.group(1))
    # print('DATE:', date_list)

    if tool_call == 'operator_activity':
        success = fetch_actprod(question, date_list)
        if not success:
            txt = 'Activity/Productivity API timeout. Please try again.'
            return {'preformat': txt, 'raw_records': txt, 'response_type': 'activity'}

    # Parse the parameters from the query
    params_call = {}
    if param_list:
        params_call = get_params(question, handler, param_list)

    # Parse the employee name determined by Deepseek
    if get_name := re.search(r'persons=\s*\[(.+)\]\s*(?!date=)', handler['message'], re.IGNORECASE):
        name_list = re.findall(r"[a-zA-Z0-9\s]+", get_name.group(1), re.IGNORECASE)
        for name in name_list:
            if get_KE := re.search(r'(?!<\w)(KE|LL)(\d{1,4})', name, re.IGNORECASE):
                digits = get_KE.group(2)
                ke_num = 'KE' + digits.rjust(4, "0")
                if 'employee_num' not in params_call.keys() or not params_call:
                    params_call['employee_num'] = [ke_num]
            elif name.replace(' ', ''):
                # name_call.append(name)
                if 'operator' in params_call.keys() or not params_call:
                    if not params_call.get('operator'):
                        params_call['operator'] = [name]
                elif not params_call.get('employee_name'):
                    params_call['employee_name'] = [name]

    print('## ----- DATA STEP ----- ##')
    # Attendance Query
    if query_type == 'attendance':
        handler_response = attendance_handler(question, tool_call, params_call, date_list)
    # Activity Query
    elif query_type == 'activity':
        handler_response = activity_handler(tool_call, params_call)
    # KTS Query
    elif query_type == 'KTS':
        # check if customer and/or model in the params
        # if params_call.get('model'):
        #     getProdArgs(session_id).model = params_call.get('model')[0]
        # elif params_call.get('customer'):
        #     pass
        # else:
        #     return {'preformat': 'No given customer or model.', 'response_type': 'KTS'}

        for key in KTS_keywords.keys():
            if key.lower() in tool_call:
                getProdArgs(session_id).command = key.lower()
                getProdArgs(session_id).date_time = [] if date_list == [date.today().isoformat()] else date_list
                getProdArgs(session_id).schema = '' if not params_call.get('customer') else params_call['customer'][0]
                getProdArgs(session_id).model = '' if not params_call.get('model') else params_call['model'][0]
                handler_response = kts_handler(question, session_id)
                break
    # General
    else:
        return {'preformat': '', 'response_type': 'general'}
    
    handler_response.update({'response_type': query_type})
    # print('Handler response:', handler_response.get('preformat'))
    return handler_response

def getAnalysis(question:str, handler_response: dict, context: list):
    reduced_context = ''
    for cont in context[-5:]:
        reduced_context += str(cont)
    
    print('## ----- INITIAL ANSWER ----- ##')
    
    today = datetime.today()
    wd = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    full_prompt = f"""Previous conversations: {reduced_context}
Today is {wd[today.weekday()]}, {today}.
Your name is Abigail, an informative and helpful AI assistant of a manufacturing company. Be friendly, conversational, and concise.
Analyze available contexts to address the user's query. If records are given, use them as primary source of information.
Otherwise, include in your response that no records were retrieved then check the previous conversations as alternative source.
Respond honestly if unsure about the answer.
Use markdown formatting for better readability.

Records: {handler_response.get('raw_records')}
{handler_response.get('instructions', '')}
Current query: {question}
"""
    result = handler_deepseek(full_prompt)

    print('## ----- VALIDATION ----- ##')
    checking_prompt = f"""Today is {wd[today.weekday()]}, {today}.
Previous conversations: [{reduced_context}]
Records: [{handler_response.get('raw_records')}]
The user query is: [{question}]
Generated response: [{remove_ansi(result)}]
Is the generated response accurate to the available data? If yes, return only <foobar> and nothing else. 
Otherwise, output a new response that better addresses the query, but do not mention the previous answer to avoid confusion."""
    new_result = handler_deepseek(checking_prompt, transparent=True)
    # print(new_result)

    if 'foobar' in new_result:
        final_output = {'answer': remove_ansi(result), 'response_type': handler_response.get('response_type')}
    else:
        final_output = {'answer': remove_ansi(new_result), 'response_type': handler_response.get('response_type')}
    
    # print('Final output:', final_output)
    return final_output

def remove_ansi(text: str):
    text = text.replace('\x1b[K\n', '')
    # print('NEW:', repr(text))
    while True:
        idx = text.find('\x1b[')
        if idx == -1:
            break
        num = ''
        ctr = 0
        for char in text[idx+2:]:
            if char == 'D':
                break
            num += char
            ctr += 1
        n_idx = idx - int(num)
        text = text[:n_idx+1] + text[idx+5:]
    # print('NEW:', repr(text))
    return text

def ask_with_file_parse(filename: str, question: str):
    if filename == '' and '.csv' in question:
        parse_filename = re.search(r'([A-Za-z0-9_\-]+.csv)', question, re.IGNORECASE)
        filename = parse_filename.group(1)
    elif filename and not question:
        question = """Summarize the contents of the file in 5-10 sentences. Determine the header names, then randomly select up to 10 datapoints to show as examples."""
    
    str_file = ''
    with open(f'./csv_files/{filename}', 'r') as file:
        for line in file:
            str_file += line + '\n'
    
    print('## ----- CSV READING ----- ##')
    full_prompt = f"""User Query: {question}
Instructions:
Today is {date.today()}.
Your name is Abigail, an informative and helpful AI assistant of a manufacturing company.
Analyze the contents of the file to determine patterns and trends. Provide examples if necessary.
Be informative, concise, and friendly.

File contents: <file start> {str_file} <file end>

Answer:"""

    result = remove_ansi(handler_deepseek(full_prompt))

    # name_parts = filename.replace('.csv', '').split('_')
    # try:
    #     converted_date = date.fromisoformat(name_parts[1])
    #     # Check if attendance csv with date range
    #     if len(name_parts) > 2 and converted_date:
    #         return {'answer': result, 'response_type': 'chart'}
    # except:
    #     print('not attendance')
    return {'answer': result, 'response_type': 'summary'}

def detectAlias(user_query: str):
    name_bank = {'kokoy': 'ranbill', 'rick': 'cesar', 'pj': 'paul john'}
    for nick, name in name_bank.items():
        if ' '+nick in user_query.lower():
            user_query = user_query.replace(nick, name)
    for key,val in dept_alias.items():
        for v in val:
            if v in user_query:
                user_query = user_query.replace(v, key)
    return user_query

def flatten(name: str):
    splitter = name.lower().replace('-','').replace(',', '').split()
    splitter.sort()
    return ' '.join(splitter)

def same_name(name_1: str, name_2: str):
    if name_1 == name_2:
        return True
    
    if len(name_1) >= len(name_2):
        ref_name = name_1.lower().replace('-','').replace(',', '').split()
        test_name = name_2.lower().replace('-','').replace(',', '').split()
    else:
        ref_name = name_2.lower().replace('-','').replace(',', '').split()
        test_name = name_1.lower().replace('-','').replace(',', '').split()
    
    exact = 0
    near = 0
    test_length = len(test_name)

    for t_part in test_name:
        # print('PART:', t_part)
        if t_part in ref_name:
            exact += 1
            ref_name.remove(t_part)

    for t_part in test_name:
        for r_part in ref_name:
            # print('TEST --', t_part, '  REF --', r_part)
            if t_part in r_part:
                near += len(t_part)/len(r_part)
                ref_name.remove(r_part)

    # print('Total grade:', exact + near)
    # print('Similarity = ', (exact + near)/test_length)
    similarity = (exact + near)/test_length
    if similarity >= 0.75:
        return True
    else:
        return False

def clean_response(output):
    """Remove thinking markers and extra whitespace"""
    clean = output
    # print('Reasoning:', output)
    
    # Remove thinking markers
    for start, end in [("Thinking...", "thinking."), ("<think>", "</think>")]:
        if start in clean and end in clean:
            start_idx = clean.find(start)
            end_idx = clean.find(end) + len(end)
            clean = clean[:start_idx] + clean[end_idx:]
    
    clean = clean.replace("Thinking...", "").replace("<think>", "").replace("</think>", "")
    
    # Clean whitespace
    while "\n\n\n" in clean:
        clean = clean.replace("\n\n\n", "\n\n")
    
    return clean.lstrip(". \n").strip()