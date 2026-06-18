import os
import re
import csv
import json
import subprocess
from typing import List, Dict
from datetime import datetime, date

from mcp_activity_server import ActivityAPI, ActivityDB
from mcp_attendance_server import attendance_DB
from kts_data_handler import ProductionDB, getProdArgs
from dictionaries import departments, kts_tools, level_0_tools, level_1_tools, level_2_tools

# DEFAULT_MODEL = 'deepseek-r1:14b'
DEFAULT_MODEL = 'deepseek-r1:8b'

path_name = './csv_files/'
ktsData = ProductionDB()
response_type = 'general'

# ----- LLM Call ----- #
def llm_message(prompt: str, model_name: str = DEFAULT_MODEL, thinking=False):
    try:
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

        stdout, stderr = process.communicate(input=prompt)
        
        if process.returncode != 0:
            return "Sorry, there was an error."

        output_txt = remove_ansi(stdout.strip())
        if thinking:
            print(output_txt)
        return clean_response(output_txt) if output_txt else "No response generated."

    except subprocess.TimeoutExpired:
        process.kill()
        return "⏱️ Request timeout."
    except FileNotFoundError:
        return "❌ Ollama not running."
    except Exception as e:
        return f"Error: {str(e)}"

# ----- Agent Functions ----- #
def loop_agent(question: str, prev_convo: list, session_id: str):
    global response_type
    txt_result = None
    turn_history = prev_convo
    tool_response_list = []
    call_history = []

    tool_list = level_0_tools + level_1_tools + level_2_tools
    today = datetime.today()
    wd = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    for k in range(9):
        print(f"## -------- Turn {k} -------- ##")
        q_prompt = f""" 
Today is {wd[today.weekday()]}, {today}.
Records: {turn_history}
List of tools: {tool_list}

You are Abigail, an insightful AI assistant. Your task is to answer the user query based on available records.
If the records are insufficient, determine the best tools to gather more data.
Output the dates, if applicable, in YYYY-MM-DD format inside an array. For date range, include only the start and end dates.
If a parameter has no value based on the query, just leave it blank.
Put the tool calls inside an array and output in JSON format: {{"tool_calls" : [{{"tool_name":"", "args": {{"parameter":"", "parameter":"", "date":[]}} }} ] }}.

When you have all relevant data, do not output tool calls anymore.
Instead, answer the user query in 4-7 sentences with key insights. Output in JSON format: {{"final_answer": ""}}.

User Query: {question}
"""
        raw_response = llm_message(q_prompt)
        turn_history.append({'role': 'Abigail', 'content': raw_response})
        if 'final_answer' in raw_response:
            idx = raw_response.find('final_answer') - 2
            result = json_parser(raw_response[idx:])
            txt_result = result.get('final_answer')
            print('Initial answer --', txt_result)
            break
        else:
            tool_queue = json_parser(raw_response).get('tool_calls', [])
            for tool in tool_queue:
                if tool not in call_history:
                    call_history.append(tool)
                    # print('TOOL HISTORY --', call_history)
                    tool_result = execute_tool(tool, question, session_id)
                    # print('TOOL RESULT -- ', str(tool_result)[:250])
                    tool_response_list.append(tool_result)
                    turn_history.append({'role': 'tool_response', 'arguments': tool, 'content': tool_result})
                else:
                    print('repeated call')
                    turn_history.append({'role': 'duplicate_tool', 'content': 'You probably have the data. Answer the query now.'})
    if not txt_result:
        txt_result = raw_response
    return {'data_list': tool_response_list, 'initial_analysis': txt_result}

def checker_agent(question:str, records: dict, initial_response: str, prev_convo: list):
    final = initial_response
    today = datetime.today()
    wd = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for j in range(5):
        print(f'## ----- VALIDATION {j} ----- ##')
        checking_prompt = f"""Today is {wd[today.weekday()]}, {today}.
Previous conversations: <{prev_convo}>
Records: <{records}>
The user query is: <{question}>
Initial response: <{final}>
Instruction: 
You are an adversarial reviewer of LLM responses. Score the initial response from 1-5 for each aspect outlined in this rubric.
1. Accuracy: 5 points if the response only mentioned data derived from the given sources. 1 point if the response has data without factual basis.
2. Completeness: 5 points if the response answered the user query completely. 1 point if the response did not cover one or more parts of the query.
3. Proactivity: 5 points if the response has insights on the given data. 1 point if the response merely echoed datapoints without insights.
Be concise and only output in this format: {{"accuracy":1-5, "completeness":1-5, "proactivity":1-5,}}"""
        
        feedback_result = llm_message(checking_prompt)
        print('Feedback --', feedback_result)
        feedback = json_parser(feedback_result)
        acc = feedback.get('accuracy', 0)
        rel = feedback.get('completeness', 0)
        com = feedback.get('proactivity', 0)

        if acc >= 3 and rel >= 2 and com >= 3:
            return final
        
        improve_prompt = f"""Today is {wd[today.weekday()]}, {today}.
Previous conversations: <{prev_convo}>
Records: <{records}>
User query: <{question}>
Inadequate response: <{final}>
Feedback: <{feedback}>
Instruction:
Your name is Abigail, an informative and helpful AI assistant of a manufacturing company. Be friendly, conversational, and concise.
Create a new response that better aligns with the criteria of accuracy to given records, relevance to user query, and completeness of datapoints.
Use the feedback on the given inadequate response to know which aspects to improve on.
Do not make explicit comparisons to the old response to avoid confusing the user. Pretend that your answer is the first time."""
        final = remove_ansi(llm_message(improve_prompt))
    
    return final

# ----- Query Handlers ----- #
def empdata_handler(question: str, tool: str, args: Dict):
    result = []
    filename = ''
    text = '# Attendance Records \n\n'
    chartable = False
    date_input = args.get('date') or [date.today().isoformat()]

    identifiers = args.get('employee_name') or args.get('employee_num') or args.get('identifier')

    if tool == 'basic_info':
        result = attendance_DB().find_person(args)
        text = 'No matches found in employee database.'
        if len(result) > 0:
            text = '# Employee Matches \n\n'
            for i, r in enumerate(result, 1):
                text += f"{i}. {r['employee_name']} ({r['employee_num']}) -- {r['department']} \n"
                text += f" - {r['job_title']} \n\n"
        return {'preformat': text, 'raw_records': result}

    elif tool == 'raw_attendance':
        result = attendance_DB().get_attendance(date_input, args)
        filename = f"ATT_{identifiers}_{'_'.join(date_input)}.csv"
        if len(date_input) > 1:
            chartable = True
    
    elif tool == 'dept_turnout':
        dept_list = args.get('department', [])
        result_dict = attendance_DB().dept_rate(date_input, dept_list)
        result = result_dict['raw_records']
        total = result_dict['total']
        present = result_dict['present']
        if dept_list and type(dept_list) == list:
            text += f"**Department:** {dept_list[0]} \n\n"
            filename = f"DEPT_{dept_list[0]}_{date_input[0]}.csv"
        elif dept_list and type(dept_list) == str:
            text += f"**Department:** {dept_list} \n\n"
            filename = f"DEPT_{dept_list}_{date_input[0]}.csv"
        else:
            filename = f"DEPT_{date_input[0]}.csv"
        text += f"**Present:** {present} out of {total} = {(100*(present / total)):.2f}% \n\n"
    
    # print("Records: ", result)
    if len(result) == 0:
        return {'preformat': 'No records in the database for the given date and parameters.', 'raw_records': []}
    
    csvfile = open(path_name + filename, 'w', newline='', encoding='utf-8')
    headers = list(result[0].keys())
    writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(result)

    # text = '# Attendance Records \n\n'
    for i, rec in enumerate(result, 1):
        if i <= 10:
            text += f'{i}. **{rec['employee_name']}** ({rec['employee_num']}) -- {rec.get('timestamp') or rec.get('first_log')} \n\n'
        # writer.writerow(rec)
        else:
            break
    
    if len(result) > 10:
        text += f"\n*Showing 10 of {len(result)} records* \n\n"

    instructions = """Work hours can start between 07:00 and 10:00 AM. Employees must log in before 10:00 AM."""
    return {'preformat': text, 'raw_records': result, 'instructions': instructions, 'csv_file': filename, 'with_chart': chartable}

def get_activity_records(args: Dict):
    if args.get('date'):
        date_input = args['date'][0]
    else:
        date_input = date.today().isoformat()
    act_filters = f'?start_date={date_input}&end_date={date_input}'
    prod_filters = f'?day={date_input}'

    # Retrieve records from api
    activityService = ActivityAPI()

    api_ok = False
    prod_ok = (date_input != date.today().isoformat())
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
        print("API failed after 5 times. Returning...")
        return {'error': 'API failed after 5 times.'}
    
    records = api_response['data']['records']
    print('LEN:', len(records))
    util_summary = {}
    if prod_ok and (date_input == date.today().isoformat()):
        util_records = prod_response['data']['records']

        for ur in util_records:
            if KE_match := re.match(r'(KE|LL)\d{4}(?!\d)', ur['operator_en'], re.IGNORECASE):
                ur['operator_en'] = code_to_name(KE_match.group(0).lower())
            key = flatten(ur['operator_en'])
            mod_stt = f'{ur['Model'].lower()}_{ur['Station'].lower()}'
            if key not in util_summary:
                util_summary[key] = {mod_stt: ur['%UTIL']}
            else:
                util_summary[key].update({mod_stt: ur['%UTIL']})
        
        # print(util_summary)
    
    # Prepare csv file for writing
    employee_id = args.get('employee_name') or args.get('employee_num')
    customer = args.get('customer', '')
    model = args.get('model', '')
    station = args.get('station', '')
    # print('filters:', employee_id, customer, model, station)

    filename = 'ACT'
    if employee_id:
        filename += '_' + employee_id.lower()
    if customer:
        filename += '_' + customer.lower()
    if model:
        filename += '_' + model.lower()
    if station:
        filename += '_' + station.lower()
    filename += '_' + date_input + '.csv'

    csvfile = open(path_name + filename, 'w', newline='', encoding='utf-8')
    headers = [k for k in records[0].keys()]
    writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore')
    writer.writeheader()
    
    filtered = []
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
        writer.writerow(r)

        # DENTSPLY,VPRO2NORDIC,SOLDERING2,"Pineda, Kyra Nicole",665,,30.00,07:03:50,13:28:44,ON TARGET,,KE0244
        if employee_id and flatten(employee_id) in op_flat:
            filtered.append(r)
        elif (customer and r['Customer'] == customer.upper()) or (model and r['Model'] == model.upper()) or (station and r['Station'] == station.upper()):
            filtered.append(r)
        elif not employee_id and not customer and not model and not station:
            filtered.append(r)
    
    csvfile.close()
    return {'date': date_input, 'filename': filename, 'records': filtered}
    # print('RECORDS:', len(records))
    # return True

def opact_handler(tool: str, args: Dict):
    if tool == 'show_allowed_stations':
        employee_id = args.get('employee_name') or args.get('employee_num')
        if not employee_id:
            return {'error': 'no employee name or number to search for'}
        actdb = ActivityDB()
        return actdb.qualified_stations(employee_id, [])
    elif tool == 'operator_output':
        records = get_activity_records(args)
        instructions = """Include all details for all applicable entries. Lower cycle time than target is good. No cycle time or target is 'on target' by default.
    Utilization rate is how much time they spent working at a given station across their whole shift. Lower utilization early in the shift is expected."""

        if len(records.get('records')) > 0:
            return {'preformat': '', 'csv_file': records.get('filename'), 'raw_records': records.get('records'), 'instructions': instructions}
        else:
            return {'preformat': "No records for the given date and parameters.", 'raw_records': []}

def kts_handler(args: dict, session_id: str, question: str):
    if getProdArgs(session_id).command == 'serial_query':
        if args.get('serial_number'):
            getProdArgs(session_id).serial = args['serial_number']
        elif K_serial := re.search(r'K(\d{11})', question) or re.search(r'KLLM(\d{8})', question):
            getProdArgs(session_id).serial = K_serial.group(0)

    if getProdArgs(session_id).check():
        return ktsData.execute(getProdArgs(session_id).command, getProdArgs(session_id))
    
    # Check if customer and model are valid
    dupe_models = []
    mod_arg = args.get('model', '').lower()
    for schema, model_list in ktsData.models.items():
        for model in model_list:
            if model in mod_arg:
                getProdArgs(session_id).model = model
                dupe_models.append(schema)
                break
    
    if len(dupe_models) > 1 and not getProdArgs(session_id).schema:
        return {'error': 'model name used by multiple customers, please clarify'}
    elif len(dupe_models) == 1:
        getProdArgs(session_id).schema = dupe_models[0]
    
    if not getProdArgs(session_id).model:
        return {'error': 'missing or invalid model argument'}
    
    if getProdArgs(session_id).command in ['station_yield', 'get_wip', 'failure_details']:
        # Search query for PO argument
        po_list = ktsData._show_all_PO(getProdArgs(session_id).schema, getProdArgs(session_id).model)
        # print('Available PO:', po_list)
        found_po = [po_num['po_num'] for po_num in po_list if (po_num['po_num'] in question or po_num['po_num'] == args.get('PO_number'))]
        if found_po:
            getProdArgs(session_id).po_num = found_po[0]
        elif po_list:
            getProdArgs(session_id).po_num = po_list[0]['po_num']
        
        # Search query for station argument
        question = ktsData.detectAlias(question)
        process_list = ktsData._get_columns(getProdArgs(session_id).schema, getProdArgs(session_id).model)
        # print('Stations:', process_list)
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
        if found_proc:
            getProdArgs(session_id).stationList = found_proc
        else:
            getProdArgs(session_id).stationList = process_list
            # print(process_list)
    
    print('Execute:', getProdArgs(session_id))
    if getProdArgs(session_id).check():
        output = ktsData.execute(getProdArgs(session_id).command, getProdArgs(session_id))
        output.update({'instructions': """No need to answer the query directly.
Instead, highlight interesting datapoints and provide a short insight in 4-7 sentences."""})
        getProdArgs(session_id).clear()
        return output
        # return {'preformat': text, 'raw_records': result, 'csv_file': filename}
    else:
        getProdArgs(session_id).clear()
        return {'preformat': ''}

# ----- Helper Functions ----- #
def execute_tool(tool: dict, question: str, session_id: str):
    tool_name = tool.get('tool_name', '')
    args = tool.get('args', {})

    if tool_name == 'show_employee_list':
        return attendance_DB().employees
    elif tool_name == 'show_department_list':
        return departments
    elif tool_name == 'show_running_models':
        return ktsData.models
    elif tool_name == 'raw_attendance' or tool_name == 'dept_turnout':
        return empdata_handler(question, tool_name, args)
    elif tool_name in ['operator_output', 'show_allowed_stations']:
        return opact_handler(tool_name, args)
    
    KTS_keywords = [kt['name'] for kt in kts_tools]
    if tool_name in KTS_keywords or tool_name == 'show_target_time':
        getProdArgs(session_id).command = tool_name
        getProdArgs(session_id).date_time = args.get('date', [])
        return kts_handler(args, session_id, question)
    
    else:
        print('yuh')
        return {'preformat': 'invalid tool', 'raw_records': []}

def extract_obj(input: str):
    cache = []
    fixed = ''
    initial = input.find('{')
    if initial == -1:
        return ''
    
    for char in input[initial:]:
        fixed += char
        if char == '{' or char == '[':
            cache.append(char)
            # print(cache)
        elif char == '}':
            if cache[-1] == '{':
                cache.pop()
                # print(cache)
            else:
                break
        elif char == ']':
            if cache[-1] == '[':
                cache.pop()
                # print(cache)
            else:
                break
        
        if len(cache) == 0:
            return fixed
    
    return ''

def json_parser(output: str):
    # print('RAW --', output)
    try:
        if output.find('```json') != -1:
            output = output.strip('```').replace('json', '').replace('\n', '')
        output = extract_obj(output)
        result = json.loads(output)
        print('JSON --', result)
        return result
    except:
        # output = extract_obj(output)
        # result = json.loads(output)
        # print('JSON --', result)
        return {}

def remove_ansi(text: str):
    text = text.replace('\x1b[K\n', '')
    # print('NO K:', repr(text))
    pattern = re.compile(r'\x1B\[(\d+)D')
    while True:
        esc = pattern.search(text)
        if not esc:
            break
        num = int(esc.group(1))
        text = text[:esc.start(0)-num] + text[esc.end(0):]
    # print('NO D:', repr(text))
    return text
    # ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    # return ansi_escape.sub('', text)

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

def code_to_name(KE_number: str):
    KE_number = KE_number.replace('ll', 'ke')
    employee_list = attendance_DB().employees
    for emp in employee_list:
        if emp['employee_num'].lower() == KE_number.lower():
            return emp['employee_name']
    return KE_number

def flatten(name: str):
    splitter = name.lower().replace('-','').replace(',', '').split()
    splitter.sort()
    return ' '.join(splitter)