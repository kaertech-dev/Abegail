# ai_handler.py - Enhanced with GPU Optimization
import subprocess
import os
import re
import csv
import spacy
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from date_parser import extractDate, extractDate_new
from mcp_activity_server import ActivityAPI
# from mcp_attendance_client import get_attendance_service
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

def ask_deepseek(question, data_chunks, context: Optional[str] = None, 
                relevant_facts: Optional[List[str]] = None,
                query_analysis: Optional[Dict] = None):
    """Enhanced AI handler with query understanding and GPU optimization"""
    MODEL_NAME = _get_model_name()
    
    # GPU optimization: limit context for smaller VRAM
    # 1.5b model can handle more chunks than 7b on 4GB GPU
    max_chunks = 5 if "1.5b" in MODEL_NAME else 3
    
    # Build reasoning context
    reasoning_context = _build_reasoning_context(question, query_analysis)
    
    context_section = f"\nConversation Context:\n{context}\n" if context else ""
    facts_section = f"\nRelevant Facts:\n" + "\n".join(f"- {f}" for f in relevant_facts) + "\n" if relevant_facts else ""
    
    full_prompt = f"""You are Abigail, an intelligent AI assistant specializing in database queries and data analysis.

{reasoning_context}
{context_section}{facts_section}
Data Retrieved:
{chr(10).join(str(chunk)[:500] for chunk in data_chunks[:max_chunks])}

User Question: {question}

INSTRUCTIONS:
1. Analyze the user's intent carefully
2. If this is a yes/no question, answer clearly first (YES/NO)
3. Provide specific details from the data
4. Be conversational and natural
5. Use markdown formatting for clarity
6. If data is empty or missing, say so clearly

Answer:"""
    
    try:
        # GPU optimization: ensure GPU is used
        env = os.environ.copy()
        env['OLLAMA_NUM_GPU'] = '1'
        
        process = subprocess.Popen(
            ["ollama", "run", MODEL_NAME],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env
        )
        
        # Adjusted timeout based on model size
        timeout = 60 if "1.5b" in MODEL_NAME else 90
        stdout, stderr = process.communicate(input=full_prompt, timeout=timeout)
        
        if process.returncode != 0:
            return "Sorry, there was an error processing your request."
        
        return clean_response(stdout.strip()) if stdout.strip() else "No response generated."
        
    except subprocess.TimeoutExpired:
        process.kill()
        return "⏱️ Request timeout. Try a shorter question."
    except FileNotFoundError:
        return "❌ Ollama is not running. Start with 'ollama serve'"
    except Exception as e:
        return f"An error occurred: {str(e)}"

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
        timeout = 45 if "1.5b" in model_name else 60
        stdout, stderr = process.communicate(input=prompt, timeout=timeout)
        
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

def activity_handler(question: str, name_call='') -> dict[str, Any]:
    # Find schema and model for filtering
    new_filters = {}
    for schema, models in ktsData.models.items():
        if schema in question.lower():
            new_filters['schema'] = schema
            for mod in models:
                if mod in question.lower():
                    new_filters['model'] = mod

    # Set date and other filters for api endpoint
    curr_date = extractDate(question)[0]
    # print('API date:', curr_date+filters)
    api_date = f'?start_date={curr_date}&end_date={curr_date}'
    act_filters = api_date + f"&customer={new_filters.get('schema','')}&model={new_filters.get('model','')}"
    prod_filters = api_date + f"&db_name={new_filters.get('schema','')}"

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
        return {'answer': 'Activity/Productivity API timeout. Please try again.', 'response_type': 'activity'}
    
    records = api_response['data']['records']
    util_records = prod_response['data']['records']

    # Summarize util% for easier retrieval later
    util_summary = {}
    for ur in util_records:
        key = flatten(ur['operator_en'])
        mod_stt = f'{ur['Model'].lower()}_{ur['Station'].lower()}'
        if key not in util_summary:
            util_summary[key] = {mod_stt: ur['%UTIL']}
        else:
            util_summary[key].update({mod_stt: ur['%UTIL']})
    
    # Prepare csv file for writing
    if new_filters.get('schema'):
        filename = 'activity_' + new_filters.get('schema') + '_' + curr_date + '.csv'
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
        r['Operator Code'] = r.pop('operator_code')
        # Retrieval util%
        util_dict = util_summary.get(flatten(r['Operator'])) or util_summary.get(r['Operator Code'])
        if util_dict is not None:
            key = f'{r['Model'].lower()}_{r['Station'].lower()}'
            r['Util(%)'] = util_dict[key]
        # Write to csv
        writer.writerow(r)
        # Rename Target to Target Cycle Time
        r['Target Cycle Time(s)'] = r.pop('Target(s)')

        # Filter the records if name was given
        if name_call == '':
            filtered_records.append(r)
        elif same_name(name_call, r['Operator']):
            filtered_records.append(r)
        else:
            filtered_records.append(r)
    
    # print('Filtered --', filtered_records)
    
    return {'csv_file': filename, 'raw_records': filtered_records, 
            'instructions': "Include all details for all applicable entries. Lower cycle time than target is good."}

def attendance_handler(question: str, tool_call: str, emp_id: str) -> dict[str, Any]:
    result = ''
    filename = ''
    chartable = False
    date_input = extractDate(question)
    # Next step: no rigid intents, just prepare a template SQL query that will be filled out by Deepseek

    # employee_list = attendance_DB().employees

    if len(date_input) > 1:
        result = attendance_DB().get_records_by_range(date_input[0], date_input[1], emp_id)
        filename = f"{emp_id.replace(' ','')}_attendance_{date_input[0]}_{date_input[1]}.csv"
        chartable = True
    
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

def kts_handler(question: str):
    # For commands with no arguments needed
    if getProdArgs().check():
        return ktsData.execute(getProdArgs().command, getProdArgs())

    q_alt = question.replace(' ', '')
    # Search query for given schema and model
    for schema, models in ktsData.models.items():
        if schema in question or schema in q_alt or getProdArgs().schema == schema:
            getProdArgs().schema = schema
            if not getProdArgs().model:
                for mod in models:
                    if mod in question.split() or mod+' ' in question:
                        getProdArgs().model = mod
    
    # If no schema, try to look for model directly
    if not getProdArgs().schema:
        for schema, models in ktsData.models.items():
            found_models = [mod for mod in models if (mod in question) or (mod in q_alt)]
            if found_models and not getProdArgs().model:
                getProdArgs().model = found_models[0]
                getProdArgs().schema = schema
    
    # If schema was found but still no model, show user a list of models under that schema
    if getProdArgs().schema and not getProdArgs().model:
        models = ktsData.models[getProdArgs().schema]
        error = f"Select {getProdArgs().schema} model to view for {getProdArgs().command}: \n\n" + ', '.join(models)
        return {'answer': error, 'response_type': 'KTS'}

    # print("After schema/model check:", getProdArgs())
    if not getProdArgs().schema:
        getProdArgs().clear()
        return {'answer': f"Schema is either missing or not an active project.", 'response_type': 'KTS'}
    
    if getProdArgs().command == 'get wip' or getProdArgs().command == 'rejects' or getProdArgs().command == 'station details' or getProdArgs().command == 'raw data':
        if getProdArgs().model and not getProdArgs().po_num:
            # Search query for PO argument
            po_list = ktsData._show_all_PO(getProdArgs().schema, getProdArgs().model)
            getProdArgs().po_num = po_list[0]['po_num']
        
        if getProdArgs().model and not getProdArgs().stationList:
            # Search query for station argument
            question = ktsData.detectAlias(question)
            process_list = ktsData._get_columns(getProdArgs().schema, getProdArgs().model)
            if not process_list:
                getProdArgs().clear()
                return {'answer': 'No stations in the database.', 'response_type': 'KTS'}
            
            process_list.insert(0, 'depanel')

            # If multiple stations, split them into a list
            inputs = [q.strip(',') for q in question.split()]
            if len(inputs) == 1:
                inputs = [q.strip() for q in question.split(',')]
            
            found_proc = [val for val in process_list if (val == question) or (val in inputs)]
            if 'all station' in question.lower() or not found_proc:
                getProdArgs().stationList = process_list
                print(process_list)
            else:
                getProdArgs().stationList = found_proc

    if getProdArgs().check():
        # Final argument check
        return ktsData.execute(getProdArgs().command, getProdArgs())
        # return {'preformat': text, 'raw_records': result, 'csv_file': filename}
    else:
        # If query fails the final argument check, it's most likely not a KTS query
        getProdArgs().clear()
        return None

def ask_general_question(question: str, context: List, default_name: Optional[str]):
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
                    #   'production_data': 'retrieve general production activity of operators',
                      'operator_activity': 'productivity details such as assigned station, output, cycle time versus target, and utilization of an operator'}
    
    # context_section = f" Recent conversation: {context}\n" if context else ""

    K_serial = re.search(r'K(\d{11})', question) or re.search(r'KLLM(\d{8})', question)
    if K_serial:
        getProdArgs().command = 'serial query'
        getProdArgs().serial = K_serial.group(0)
    
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
    if getProdArgs().command:
        handler_response = kts_handler(question)
        return handler_response
    else:
    # Determine scope, intent, and employee name if applicable
        handler = handler_deepseek(kts_prompt).lower()
        print('Deepseek --', handler)
    # Parse the tool call determined by Deepseek
    if get_tool := re.search(r'Tool=\s*(\w+)', handler, re.IGNORECASE):
        tool_call = get_tool.group(1)
    
    # Parse the employee name determined by Deepseek
    if get_name := re.search(r'Employee=\s*(\w+.+)', handler, re.IGNORECASE):
        name_call = get_name.group(1).lower()
    elif get_KE := re.search(r'(?!<\w)(KE|LL)(\d{1,4})', question, re.IGNORECASE):
        digits = get_KE.group(2)
        while len(digits) < 4:
            digits = '0' + digits
        name_call = 'KE' + digits
    
    if 'individual_attendance' in tool_call or 'department_headcount' in tool_call or 'latest_entries' in tool_call:
        query_type = 'attendance'
        # Attendance Query
        getProdArgs().clear()
        handler_response = attendance_handler(question, tool_call, name_call)
    elif 'production_data' in tool_call or 'operator_activity' in tool_call:
        query_type = 'activity'
        # Activity Query
        getProdArgs().clear()
        handler_response = activity_handler("Current query: " + question, name_call)
        if handler_response.get('answer'):
            return handler_response
    else:
        for key in KTS_keywords.keys():
            if key.lower() in handler:
                # if not getProdArgs().command:
                getProdArgs().command = key
                if not getProdArgs().date_time:
                    getProdArgs().date_time = extractDate(question, None)
                handler_response = kts_handler(question)
                query_type = 'KTS'
                # print("Obj class:", getProdArgs())
        # if kts_result is not None and kts_result != {}:
        #     return kts_result
    
    # getProdArgs().clear()
    reduced_context = ''
    for cont in context[-5:]:
        reduced_context += str(cont)
    full_prompt = f"""
Today is {date.today()}.
Your name is Abigail, an informative and helpful AI assistant of a manufacturing company.
Be friendly, conversational, and concise.
Provide examples from the given data if applicable.
Do not create datapoints that do not exist.

Previous conversations: {reduced_context}
Records: {handler_response.get('raw_records')}
{handler_response.get('instructions', '')}
Current query: {question}
"""
    result = handler_deepseek(full_prompt)
    final_output = {'answer': handler_response.get('preformat', '') + result, 'response_type': query_type}
    if 'with_chart' in handler_response:
        final_output['with_chart'] = handler_response.get('with_chart')
    if 'csv_file' in handler_response:
        final_output['csv_file'] = handler_response.get('csv_file')
    return final_output

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
User Query: {question}
File contents: {list_entries}

Instructions:
Answer the user query based on the given contents of a file.
Be informative, concise, and friendly. Provide examples from the file if necessary.

Answer:"""

    result = handler_deepseek(full_prompt)

    name_parts = filename.replace('.csv', '').split('_')
    try:
        converted_date = date.fromisoformat(name_parts[1])
        # Check if attendance csv with date range
        if len(name_parts) > 2 and converted_date:
            return {'answer': result, 'response_type': 'chart'}
    except ValueError:
        return {'answer': result, 'response_type': 'general'}

def detectAlias(user_query: str):
    name_bank = {'kokoy': 'ranbill cadayona', 'rick': 'cesar modina', 'pj': 'paul john'}
    for nick, name in name_bank.items():
        if nick in user_query.lower():
            user_query = user_query.replace(nick, name)
    return user_query

def flatten(name: str):
    return name.lower().replace('-','').replace(',', '')

def same_name(name_1: str, name_2: str):
    name_1 = name_1.lower().replace('-','').replace(',', ' ').split()
    name_2 = name_2.lower().replace('-','').replace(',', ' ').split()

    ctr = 0
    for part_1 in name_1:
        for part_2 in name_2:
            if part_1 == part_2:
                ctr+=1
    
    if ctr > 0:
        return True
    else:
        return False

def _build_reasoning_context(question: str, query_analysis: Optional[Dict]) -> str:
    """Build context to help AI understand the query better"""
    if not query_analysis:
        return ""
    
    intent = query_analysis.get('primary_intent', 'unknown')
    question_type = query_analysis.get('question_type', 'unknown')
    entities = query_analysis.get('entities', {})
    temporal = query_analysis.get('temporal_context', {})
    
    context = "QUERY ANALYSIS:\n"
    context += f"- User Intent: {intent.replace('_', ' ').title()}\n"
    context += f"- Question Type: {question_type.replace('_', ' ').title()}\n"
    
    if entities:
        context += f"- Identified Entities:\n"
        for entity_type, values in entities.items():
            context += f"  • {entity_type}: {', '.join(values)}\n"
    
    if temporal.get('has_time_reference'):
        context += f"- Time Context: "
        if temporal.get('relative_time'):
            context += f"{temporal['relative_time'].replace('_', ' ')}\n"
        elif temporal.get('specific_date'):
            context += f"{temporal['specific_date']}\n"
        elif temporal.get('time_range'):
            context += f"from {temporal['time_range'][0]} to {temporal['time_range'][1]}\n"
    
    # Add reasoning hints based on question type
    if question_type == 'yes_no':
        context += "\nREASONING HINT: This is a YES/NO question. Answer clearly with YES or NO first, then explain.\n"
    elif question_type == 'quantitative':
        context += "\nREASONING HINT: User wants a number/count. Provide the specific quantity.\n"
    elif question_type == 'factual':
        context += "\nREASONING HINT: User wants specific facts. Be precise and direct.\n"
    elif question_type == 'explanatory':
        context += "\nREASONING HINT: User wants an explanation. Provide detailed reasoning.\n"
    
    return context + "\n"

def clean_response(output):
    """Remove thinking markers and extra whitespace"""
    clean = output
    
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