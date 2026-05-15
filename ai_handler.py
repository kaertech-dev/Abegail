# ai_handler.py - Enhanced with GPU Optimization
import subprocess
import os
import re
import csv
import spacy
from datetime import date, datetime, time
from typing import List, Optional, Dict, Any
from date_parser import extractDate
from mcp_activity_server import ActivityAPI
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

def _get_model_name():
    from config import MODEL_NAME
    return MODEL_NAME

def handler_deepseek(prompt: str, model_name: str = DEFAULT_MODEL):
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

        return clean_response(stdout.strip()) if stdout.strip() else "No response generated."

    except subprocess.TimeoutExpired:
        process.kill()
        return "⏱️ Request timeout."
    except FileNotFoundError:
        return "❌ Ollama not running."
    except Exception as e:
        return f"Error: {str(e)}"

def query_processor(message: str):
    query_type = None
    
    activity_keywords = [
        'activity', 'activities', 'monitoring',
        'what are they doing', 'who is doing', 'doing', 'working',
        'productivity', 'output', 'cycle time', 'target', 'start time', 'end time', 'operator'
    ]

    for kw in activity_keywords:
        if kw in message.lower():
            return 'activity'

    attendance_keywords = [
        'attendance', 'present', 'absent', 'time in', 'clock in', 'check in', 
        'who is here', 'who is in', 'in the house', 'in the haus',
        'department', 'headcount', 'employee', 'employees',
        'timeout', 'time out', 'clock out'
    ]

    for kw in attendance_keywords + departments:
        if kw in message.lower():
            return 'attendance'
    
    if query_type is None:
        return 'general'

def query_processor_LLM(question: str):
    att_act_intents = {'individual_attendance': 'employee attendance given the name or employee number which starts with KE followed by 4 numbers',
                       'department_headcount': 'list present employees under a given department',
                       'latest_entries': 'get the latest attendance records from the database',
                       'operator_activity': 'retrieve output, cycle time, and status of production operators',
                    #    'production_data': 'retrieve general production data such as customer, model, station, target, and operator list',
                       'none_applicable': 'query outside of scope'}
    
    main_prompt = f"""Current message: {question} 
    List of Intents with Description: {att_act_intents} 
    Instruction: Determine the intent of the user from the list of options, as well as the given employee name if applicable. Be concise and output only what are needed.
    Answer format: Tool= Employee= """
    
    ai_response = handler_deepseek(main_prompt)
    print(ai_response)
    return ai_response

def code_to_name(KE_number: str):
    KE_number = KE_number.replace('ll', 'ke')
    employee_list = attendance_DB().employees
    for emp in employee_list:
        if emp['employee_num'].lower() == KE_number.lower():
            return emp['employee_name']
    return KE_number

def activity_handler(question: str, name_call, date_input) -> dict[str, Any]:
    # Find schema and model for filtering
    new_filters = {}
    for schema, models in ktsData.models.items():
        if schema in question.lower():
            new_filters['schema'] = schema
            for mod in models:
                if mod in question.lower():
                    new_filters['model'] = mod

    # Set date and other filters for api endpoint
    if date_input:
        curr_date = date_input[0]
    else:
        curr_date = extractDate(question)[0]
    # print('API date:', curr_date+filters)
    api_date = f'?start_date={curr_date}&end_date={curr_date}'
    act_filters = api_date + f"&customer={new_filters.get('schema','')}&model={new_filters.get('model','')}"
    # prod_filters = api_date + f"&db_name={new_filters.get('schema','')}"
    prod_filters = f'?day={curr_date}'

    # Retrieve records from api
    activityService = ActivityAPI()

    api_ok = False
    prod_ok = False
    for fail_ctr in range(3):
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

    # If either fetch fails, return with timeout
    if not (api_ok and prod_ok):
        print("API failed after 3 times. Returning...")
        return {'preformat': 'Activity/Productivity API timeout. Please try again.', 'response_type': 'activity'}
    
    records = api_response['data']['records']
    util_records = prod_response['data']['records']

    # Summarize util% for easier retrieval later
    util_summary = {}
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
    
    # Prepare csv file for writing
    if new_filters.get('schema'):
        filename = 'activity_' + new_filters['schema'] + '_' + curr_date + '.csv'
    else:
        filename = 'activity_' + curr_date + '.csv'
    csvfile = open(path_name + filename, 'w', newline='', encoding='utf-8')
    writer = csv.DictWriter(csvfile, fieldnames=
                            ['Customer', 'Model', 'Station', 'Operator', 'Operator Code', 'Output', 'Cycle Time(s)', 'Target(s)', 'Start Time', 'End time', 'Status', 'Util(%)'],
                            extrasaction='ignore')
    writer.writeheader()

    # Pre-process the records for easier parsing by Deepseek, and write to csv
    filtered_records = []
    for r in records:
        # Remove serial numbers
        r.pop('serial_num')
        if KE_match := re.search(r'(KE|LL)\d{4}', r['Operator'], re.IGNORECASE):
            r['Operator'] = code_to_name(KE_match.group(0))
        r['Operator Code'] = r.pop('operator_code')
        if r['Status'].lower() == 'orange target':
            r['Status'] = 'NEAR TARGET'
        # Retrieve util%
        op_flat = flatten(code_to_name(r['Operator Code'].lower()))
        util_dict = util_summary.get(op_flat)
        if util_dict is not None:
            key = f'{r['Model'].lower()}_{r['Station'].lower()}'
            r['Util(%)'] = util_dict.get(key)
        # Write to csv
        writer.writerow(r)
        # Rename Target to Target Cycle Time
        r['Target Cycle Time(s)'] = r.pop('Target(s)')

        # Filter the records if name was given
        if name_call == '':
            filtered_records.append(r)
        elif same_name(name_call, r['Operator']):
            filtered_records.append(r)
        elif name_call == r['Operator Code']:
            filtered_records.append(r)
        else:
            filtered_records.append(r)
    
    # print('Filtered --', filtered_records)
    if len(filtered_records) > 0:
        return {'preformat': '', 'csv_file': filename, 'raw_records': filtered_records, 
                'instructions': """Include all details for all applicable entries. Lower cycle time than target is good. No target cycle time is automatically on target.
                Utilization rate is how much time they spent on working across their whole shift. Lower utilization early in the shift is expected."""}
    else:
        return {'preformat': "No records in the database for the given date and parameters.", 'raw_records': []}

def attendance_handler(question: str, tool_call: str, emp_id: str, date_input: str) -> dict[str, Any]:
    result = []
    filename = ''
    chartable = False
    if not date_input:
        date_input = extractDate(question)
    # Next step: no rigid intents, just prepare a template SQL query that will be filled out by Deepseek

    # employee_list = attendance_DB().employees

    if len(date_input) > 1:
        result = attendance_DB().get_records_by_range(date_input[0], date_input[1], emp_id)
        filename = f"{emp_id.replace(' ','')}_attendance_{date_input[0]}_{date_input[1]}.csv"
        chartable = True
    
    elif r'employee_data' in tool_call:
        possible_employees = []
        for emp in attendance_DB().employees:
            if emp['employee_num'] == emp_id:
                possible_employees.append(emp)
                break
            elif flatten(emp_id) == flatten(emp['employee_name']):
                possible_employees.append(emp)
            elif same_name(emp_id, emp['employee_name']):
                possible_employees.append(emp)
        result = possible_employees
        print(result)
        text = '# No employee match in the database.'
        if len(possible_employees) > 0:
            text = '# Employee Matches \n\n'
            for i, r in enumerate(result, 1):
                text += f"{i}. {r['employee_name']} ({r['employee_num']}) -- {r['department']} \n\n"
        return {'preformat': text, 'raw_records': result}
    
    elif r'individual_attendance' in tool_call:
        result = attendance_DB().get_records_by_date(date_input[0], emp_id)
        filename = f"{emp_id.replace(' ','')}_attendance_{date_input[0]}.csv"

    elif r'latest_entries' in tool_call:
        result = attendance_DB().get_latest_entries(None, None)
        filename = f"latest_attendance_{date_input[0]}.csv"
            
    elif r'department_headcount' in tool_call:
        dept_param = ''
        for true_name, alias in dept_alias.items():
            for nick in alias:
                if nick in question:
                    dept_param = true_name
        
        if not dept_param:
            found_depts = [dept for dept in departments if dept.lower() in question.lower()]
            dept_param = 'all' if not found_depts else found_depts[0]

        result = attendance_DB().get_present_employees(date_input[0], datetime.now().time(), dept_param)
        filename = f"{dept_param}_attendance_{date_input[0]}.csv"
        text = '# Department Headcount \n\n'
    
    # print("Records: ", result)
    if len(result) == 0:
        return {'preformat': 'No records in the database for the given date and parameters.', 'raw_records': []}
    
    csvfile = open(path_name + filename, 'w', newline='', encoding='utf-8')
    writer = csv.DictWriter(csvfile, fieldnames=['employee_name', 'employee_num', 'department', 'timestamp'], extrasaction='ignore')
    writer.writeheader()

    text = '# Attendance Records \n\n'
    for i, rec in enumerate(result, 1):
        if i <= 10:
            text += f'{i}. **{rec['employee_name']}** ({rec['employee_num']}) -- {rec['timestamp']} \n\n'
        writer.writerow(rec)
    
    if len(result) > 10:
        text += f"\n*Showing first 10 of {len(result)} records* \n\n"

    return {'preformat': text, 'raw_records': result, 'csv_file': filename, 'with_chart': chartable}

def kts_handler(question: str, session_id: str):
    # For commands with no arguments needed
    if getProdArgs(session_id).check():
        return ktsData.execute(getProdArgs(session_id).command, getProdArgs(session_id))

    q_alt = question.replace(' ', '')
    # Search query for given schema and model
    for schema, models in ktsData.models.items():
        if schema in question or schema in q_alt or getProdArgs(session_id).schema == schema:
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
            
            process_list.insert(0, 'depanel')

            # If multiple stations, split them into a list
            inputs = [q.strip(',') for q in question.split()]
            if len(inputs) == 1:
                inputs = [q.strip() for q in question.split(',')]
            
            found_proc = [val for val in process_list if (val in question) or (val in inputs)]
            print(found_proc)
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
        getProdArgs(session_id).clear()
        return output
        # return {'preformat': text, 'raw_records': result, 'csv_file': filename}
    else:
        # If query fails the final argument check, it's most likely not a KTS query
        getProdArgs(session_id).clear()
        return {'preformat': ''}

def ask_general_question(question: str, context: List, session_id: Optional[str]):
    """Query handler with reasoning"""
    MODEL_NAME = _get_model_name()

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
                'process_flow': 'list of manufacturing stations under a certain model',
                'get_wip': 'input and output summary of a work-in-progress model',
                'last_running_PO': 'most recent purchase order for a model',
                'rejects': 'quantity of failed units of a given model',
                'list_all_PO': 'list of purchase orders for a model',
                'active_projects': 'list of active projects',
                'running_models': 'list of running models',
                'none_applicable': 'query outside of scope'}

addtl_keywords = {'individual_attendance': 'attendance of an employee',
                'latest_entries': 'get the latest attendance records from the database',
                'department_headcount': 'list present employees under a given department',
                'employee_data': 'return the name, KE number, and department of an employee',
                'production_data': 'retrieve data regarding customers and models currently in production',
                'operator_activity': 'productivity details such as assigned station, output, cycle time versus target, and utilization rate of an operator'}

# broader scopes = [attendance, operator productivity, manufacturing data, company-related, others]
# 

def getIntent(question: str, context: list, session_id: str) -> str:
    K_serial = re.search(r'K(\d{11})', question) or re.search(r'KLLM(\d{8})', question)
    if K_serial:
        getProdArgs(session_id).command = 'serial query'
        getProdArgs(session_id).serial = K_serial.group(0)
    
    handler_response = ''

    past = "Previous conversation:"
    for cont in context:
        past += str(cont)
    today = datetime.today()
    wd = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    kts_prompt = past + f"""Current message: {question} 
Today is {wd[today.weekday()]}, {today}.
List of Intents with Description: {KTS_keywords | addtl_keywords} 
Instructions:
1. Determine the intent of the current message from the list of options.
2. Determine the date or range of dates given by the user, and output them in a Python list in ISO format. Check for implied dates such as 'last 3 weeks'.
3. Determine if the message mentions a name of an employee. If none, leave blank.
In case of multiple dates, I only need the start and end. If no date, use empty list.
Be concise and output only what are needed.
Answer format: Intent= Date= Employee="""
    
    # if getProdArgs(session_id).command:
    #     handler_response = kts_handler(question)
    # else:
    # Determine scope, intent, and employee name if applicable
    handler_response = handler_deepseek(kts_prompt).lower()
    print('Response:', handler_response)

    return handler_response

def getData(question: str, handler: str, session_id: str) -> dict[str, str]:
    handler_response = {}
    tool_call = ''
    name_call = ''
    date_list = []
    query_type = 'general'
    # Parse the tool call determined by Deepseek
    if get_tool := re.search(r'intent=\s*(\w+)', handler.lower(), re.IGNORECASE):
        tool_call = get_tool.group(1)
    
    # Parse the employee name determined by Deepseek
    if get_name := re.search(r'employee=\s*(\w+.+)\s*(?!date=)', handler.lower(), re.IGNORECASE):
        name_call = get_name.group(1).lower()
    if get_KE := re.search(r'(?!<\w)(KE|LL)(\d{1,4})', question, re.IGNORECASE):
        digits = get_KE.group(2)
        while len(digits) < 4:
            digits = '0' + digits
        name_call = 'KE' + digits
    
    # Parse the date/range determined by Deepseek
    if date := re.search(r'date=\s*\[(.+)\]', handler.lower()):
        date_list = re.findall(r'\d{4}-\d{2}-\d{2}', date.group(1))
    # print('DATE:', date_list)
    
    # Attendance Query
    if 'individual_attendance' in tool_call or 'department_headcount' in tool_call or 'latest_entries' in tool_call or 'employee_data' in tool_call:
        query_type = 'attendance'
        handler_response = attendance_handler(question, tool_call, name_call, date_list)
    # Activity Query
    elif 'production_data' in tool_call or 'operator_activity' in tool_call:
        query_type = 'activity'
        handler_response = activity_handler(question, name_call, date_list)
    # General
    elif 'none_applicable' in tool_call or 'none' in tool_call or tool_call == '':
        return {'preformat': '', 'response_type': 'general'}
    # KTS Query
    else:
        for key in KTS_keywords.keys():
            if key.lower() in handler:
                getProdArgs(session_id).command = key
                if not getProdArgs(session_id).date_time:
                    # getProdArgs(session_id).date_time = extractDate(question, None)
                    getProdArgs(session_id).date_time = date_list
                handler_response = kts_handler(question, session_id)
                query_type = 'KTS'
    
    handler_response.update({'response_type': query_type})
    # print('Handler response:', handler_response.get('preformat'))
    return handler_response

def getAnalysis(question:str, handler_response: dict, context: list):
    reduced_context = ''
    for cont in context[-5:]:
        reduced_context += str(cont)
    
    today = datetime.today()
    wd = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    full_prompt = f"""Previous conversations: {reduced_context}
Today is {wd[today.weekday()]}, {today}.
Your name is Abigail, an informative and helpful AI assistant of a manufacturing company. Be friendly, conversational, and concise.
Analyze available contexts to answer the user's query. If records are given, use them as primary source of information.
Otherwise, include in your response that no records were retrieved then check the previous conversations as alternative source.
Respond honestly if unsure about the answer.

Records: {handler_response.get('raw_records')}
{handler_response.get('instructions', '')}
Current query: {question}
"""
    result = handler_deepseek(full_prompt)

#     checking_prompt = f"""
# Previous conversations: [{reduced_context}]
# Records: [{handler_response.get('raw_records')}]
# The user query is: [{question}]
# Generated response: [{result}]
# Does the generated response adequately and correctly answer the user query? Output only <yes> or <no>."""
#     new_result = handler_deepseek(checking_prompt)
#     print('Checking step:', new_result)

    final_output = {'answer': remove_ansi(result), 'response_type': handler_response.get('response_type')}
    
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
        question = 'Give a detailed but brief summary of the file.'
    
    list_entries = []
    with open(f'./csv_files/{filename}', 'r') as file:
        for line in csv.DictReader(file):
            list_entries.append(line)
        
    full_prompt = f"""
Instructions:
Today is {date.today()}.
Your name is Abigail, an informative and helpful AI assistant of a manufacturing company.
Answer the user query based on the given contents of a file.
Be informative, concise, and friendly. Provide examples from the file if necessary.

File contents: {list_entries}
User Query: {question}

Answer:"""

    result = handler_deepseek(full_prompt)

    name_parts = filename.replace('.csv', '').split('_')
    try:
        converted_date = date.fromisoformat(name_parts[1])
        # Check if attendance csv with date range
        if len(name_parts) > 2 and converted_date:
            return {'answer': result, 'response_type': 'chart'}
    except:
        return {'answer': result, 'response_type': 'general'}

def detectAlias(user_query: str):
    name_bank = {'kokoy': 'ranbill cadayona', 'rick': 'cesar modina', 'pj': 'paul john'}
    for nick, name in name_bank.items():
        if nick in user_query.lower():
            user_query = user_query.replace(nick, name)
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
    print('Reasoning:', output)
    
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