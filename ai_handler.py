# ai_handler.py - Enhanced with GPU Optimization
import subprocess
import os
import re
import csv
import spacy
from datetime import date
from typing import List, Optional, Dict, Any
from date_parser import extractDate
from mcp_activity_server import ActivityAPI
from mcp_attendance_client import get_attendance_service
from mcp_attendance_server import AttendanceDB
from kts_data_handler import ProductionDB, getProdArgs

# DEFAULT_MODEL = 'deepseek-r1:14b'
DEFAULT_MODEL = 'deepseek-r1:8b'

path_name = './csv_files/'
filename = ''
nlp = spacy.load("en_core_web_md")

departments = ['Top Management',
            'Manufacturing', 'Quality Regulatory Affairs & EHS',
            'Business Development', 'HR & Admin',
            'Supply Chain Management', 'Facilities & Maintenance',
            'Information Technology', 'Research & Development',
            'Accounting', 'Finance & Administration']

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
    
    full_prompt = f"""You are Abegail, an intelligent AI assistant specializing in database queries and data analysis.

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
        'activity', 'activities', 'monitoring', 'where is',
        'what are they doing', 'who is doing', 'doing', 'working',
        'productivity', 'output', 'cycle time', 'target', 'start time', 'end time', 'operator'
    ]

    for kw in activity_keywords:
        if kw in message.lower():
            return 'activity'

    attendance_keywords = [
        'attendance', 'present', 'absent', 'time in', 'clock in', 'check in', 
        'who is here', 'who is in', 
        'department', 'headcount', 'employee', 'employees',
        'timeout', 'time out', 'clock out'
    ]

    for kw in attendance_keywords:
        if kw in message.lower():
            return 'attendance'
    
    if query_type is None:
        return 'general'

def query_processor_LLM(question: str):
    ai_input = f"""{question}

List of tools: {{individual_attendance, department_headcount, latest_entries}}.
I want to filter attendance records from database. What is the the best tool that would allow me to achieve that goal? And for which employee? If the query is not related to attendance, output 'not_attendance'.

Examples: (Question: "Check Ranbill attendance", Answer: "Tool=individual_attendance Employee=Ranbill"), (Question: "What are the latest attendance records?", Answer: "Tool=latest_entries Employee=None")

Answer:
Tool=
Employee="""
    ai_response = handler_deepseek(ai_input, 'deepseek-r1:7b')
    print(ai_response)
    return ai_response

def activity_handler(question: str) -> dict[str, Any]:
    # set date input for api endpoint
    curr_date = extractDate(question)[0]
    api_date = f'?start_date={curr_date}&end_date={curr_date}'

    # retrieve records from api
    activityService = ActivityAPI()
    
    for fail_ctr in range(5):
        api_response = activityService.get_all_data(api_date)
        if api_response['success']:
            break

    if fail_ctr == 4:
        print("API failed after 5 times. Returning...")
        return {'answer': 'API timeout', 'response_type': 'activity'}
    
    records = api_response['data']['records']
    
    # prepare csv file for writing
    filename = 'activity_' + curr_date + '.csv'
    csvfile = open(path_name + filename, 'w', newline='', encoding='utf-8')
    writer = csv.DictWriter(csvfile, fieldnames=['Customer', 'Model', 'Station', 'Operator', 'Output', 'Cycle Time(s)', 'Target(s)', 'Start Time', 'End time', 'Status'], extrasaction='ignore')
    writer.writeheader()

    # remove serial numbers and rename target to make it easier for Deepseek to parse
    for r in records:
        writer.writerow(r)
        r['Target Cycle Time(s)'] = r.pop('Target(s)')
        r.pop('serial_num')
    
    return {'csv_file': filename, 'raw_records': records, 'instructions': "Refer to people by name but also give their employee number. Lower cycle time means above target."}

def attendance_handler(question: str, tool_call: str, default_name: str) -> dict[str, Any]:
    result = ''
    chartable = False
    attendanceService = get_attendance_service()
    date_input = extractDate(question)

    processed = nlp(question)
    entities = [ent.text for ent in processed.ents]

    name_match = re.search(r'Employee=(\w+)', tool_call)
    if name_match and 'Not' not in name_match.group(1) :
        emp_id = name_match.group(1)
    elif emp_num := re.search(r'\s+(KE\d+)\s*', question, re.IGNORECASE):
        emp_id = emp_num.group(1)
    elif emp_match := re.search(r'is (\w+) present', question, re.IGNORECASE):
        emp_id = emp_match.group(1)
    elif entities:
        emp_id = entities[-1]
    else:
        emp_id = default_name
    
    # print("Employee identifier: ", emp_id)
    tool_handle = re.search(r'Tool=(\w+)', tool_call, re.IGNORECASE)
    # print(tool_handle)

    if len(date_input) > 1:
        result = attendanceService.get_attendance_range(date_input[0], date_input[1], emp_id)
        chartable = True
    
    elif r'individual_attendance' in tool_call:
        result = attendanceService.check_presence(emp_id, date_input[0])

    elif r'latest_entries' in tool_call:
        result = attendanceService.get_latest_entries(None, None)
            
    elif r'department_headcount' in tool_call:
        dept_param = [dept.lower() for dept in departments if dept.lower() in question.lower()]
        result = attendanceService.department_headcount(dept_param[0], date_input[0])
    
    else:
        directToDB = AttendanceDB()
        # print('fallback. ', date_input)
        return {'error': directToDB.get_records_by_date(date_input[0], None), 'instructions': 'Include the KE number, timestamp, and location'}
        
    idx = result.find('.csv') + 4
    if idx > 3:
        filename = result[:idx]
        return {'answer': result[idx:], 'csv_file': filename, 'with_chart': chartable, 'response_type': 'attendance'}
    else:
        return {'answer': result, 'response_type': 'attendance'}

def kts_handler_old(question: str, handler: str = '', key: str = ''):
    prodData = ProductionDB()
    result = ''
    filename = ''

    if noun_match := re.search(r'Proper Nouns: \[(.*)\]', handler, re.IGNORECASE):
        raw_nouns = noun_match.group(1).split()
        nouns = []
        for nn in raw_nouns:
            nn = nn.strip(",'. ").strip('"').lower()
            if nn != 'po':
                nouns.append(nn)
        
        # print(nouns)

    if 'process flow' in question.lower() or key == 'process flow':
        gpf_match = re.search(r'get process flow for (?:schema)?\s*(\w+) (?:model)?\s*(\w+)', question, re.IGNORECASE)
        if gpf_match:
            result = prodData.getProcessFlow(gpf_match.group(1), gpf_match.group(2))
        elif len(nouns) > 1:
            result = prodData.getProcessFlow(nouns[0], nouns[1])
        else:
            result = "Parse error. Please use this input format:\n\nget process flow for schema {name} model {name}"
    
    elif 'active projects' in question.lower() or key == 'active projects':
        result = prodData.getActiveProjects()
    
    elif 'running models' in question.lower() or key == 'running models':
        date_input = extractDate(question)
        result = prodData.getRunningModels(date_input)
    
    elif 'list all po' in question.lower() or key == 'list all PO':
        if po_match := re.search(r'for (?:schema)?\s*(\w+) (?:model)?\s*(\w+)', question, re.IGNORECASE):
            result = prodData.listPO(po_match.group(1), po_match.group(2))
        elif len(nouns) > 1:
            result = prodData.listPO(nouns[0], nouns[1])
    
    elif 'last running' in question.lower() or key == 'last running PO':
        if po_match := re.search(r'for (?:schema)?\s*(\w+) (?:model)?\s*(\w+)', question, re.IGNORECASE):
            result = prodData.getLatestPO(po_match.group(1), po_match.group(2))
        elif len(nouns) > 1:
            result = prodData.getLatestPO(nouns[0], nouns[1])

    elif 'serial query' in question.lower() or key == 'serial query':
        if serial_match := re.search(r'K\d{11}', question, re.IGNORECASE):
            result = prodData.serialQuery(serial_match.group(0))
        else:
            result = "Invalid serial number format."

    elif 'get wip' in question.lower() or key == 'get wip':
        date_input = extractDate(question)[0]
        shift_match = re.search(r'shift (\w{1})', question, re.IGNORECASE)
        wip_match = re.search(r'get wip for (?:schema)?\s*(\w+) (?:model)?\s*(\w+) (?:PO)?\s*(\w+)', question, re.IGNORECASE)
        if wip_match:
            if shift_match:
                result = prodData.getWIP(wip_match.group(1), wip_match.group(2), wip_match.group(3), date_input, shift_match.group(1))
            else:
                result = prodData.getWIP(wip_match.group(1), wip_match.group(2), wip_match.group(3), date_input)
        elif len(nouns) > 2:
            result = prodData.getWIP(nouns[0], nouns[1], nouns[2], date_input)
        else:
            result = "Parse error. Please use this input format:\n\nget wip for schema {name} model {name} PO {number}"
    
    elif 'station details' in question.lower() or key == 'station details':
        # query database for entries between the given date range
        date_input = extractDate(question)
        if full_match := re.search(r'station details for (?:schema)?\s*(\w+) (?:model)?\s*(\w+) (?:station)?\s*(\w+)', question, re.IGNORECASE):
            result, filename = prodData.getStationDetails(full_match.group(1), full_match.group(2), full_match.group(3), date_input)
        elif len(nouns) > 2:
            result, filename = prodData.getStationDetails(nouns[0], nouns[1], nouns[2], date_input)
    
    return {'answer': result, 'csv_file': filename, 'response_type': 'KTS'}

ktsData = ProductionDB()
def kts_handler(question: str):
    if getProdArgs().command == 'serial query':
        if serial_match := re.search(r'K\d{11}', question, re.IGNORECASE):
            getProdArgs().serial = serial_match.group(0)
    
    if getProdArgs().check():
        # No need to go through the rest if arguments are already complete at this point
        return ktsData.execute(getProdArgs().command, getProdArgs())

    found_models = []
    # Search query for given schema and/or model
    if getProdArgs().schema == '' or getProdArgs().model == '':
        for schema, models in ktsData.models.items():
            found_models = [m for m in models if m in question]
            if found_models:
                if not getProdArgs().schema:
                    getProdArgs().schema = schema
                getProdArgs().model = found_models[0]
            elif schema in question:
                getProdArgs().schema = schema
                return {'answer': f"Available models for {schema}: " + ', '.join(models), 'response_type': 'KTS'}
    
    if getProdArgs().command == 'get wip' and getProdArgs().model and not getProdArgs().po_num:
        # Search query for PO argument
        po_list = ktsData._show_all_PO(getProdArgs().schema, getProdArgs().model)
        # print(po_list)
        found_po = [po['po_num'] for po in po_list if po['po_num'] in question]
        if not found_po:
            error = "Available PO: \n" + ', '.join([entry['po_num'] for entry in po_list])
        else:
            getProdArgs().po_num = found_po[0]
    elif getProdArgs().command == 'station details' and getProdArgs().model and not getProdArgs().station:
        # Search query for station argument
        process_list = ktsData._get_columns(getProdArgs().schema, getProdArgs().model)
        found_proc = [val for val in process_list if val in question]
        if not found_proc:
            error = "Process Flow: \n" + ', '.join([val for val in process_list])
        else:
            getProdArgs().station = found_proc[0]
    
    # print("Obj class:", getProdArgs())

    if getProdArgs().check():
        return ktsData.execute(getProdArgs().command, getProdArgs())
    else:
        try:
            return {'answer': error, 'response_type': 'KTS'}
        except:
            # Under the assumption that all kts-related query are properly supported, so an Exception must mean query is not kts-related
            getProdArgs().clear()
            return 'not kts related'

def ask_general_question(question: str, context: Optional[List], default_name: Optional[str]):
    """Question handler with reasoning"""
    MODEL_NAME = _get_model_name()

    KTS_keywords = ['process flow', 'active projects', 'running models', 'serial query', 'get wip', 'station details', 'list all PO', 'last running PO']
    
    # if 'debug' in question:
    #     question = question.replace('debug', '')
    #     if any(kw in question.lower() for kw in KTS_keywords.keys()):
    #         return kts_handler(question)
    
    context_section = f" Recent conversation: {context}\n" if context else ""
    
    handler_response = {}
    mcp_section = ''
    filename = ''
    kts_result = None

    # Check if input chaining, then skip intent determination
    # if stored_values:
    if getProdArgs().command != '':
        kts_result = kts_handler(question)
        # print("Chaining: ", kts_result)
    
    if kts_result is not None and kts_result != 'not kts related':
        return kts_result

    query_type = query_processor(question)
    if query_type == 'attendance':
        # Attendance Query
        tool_call = query_processor_LLM(str(context) + question)
        handler_response = attendance_handler(question, tool_call, default_name)

        if handler_response.get('answer'):
            return handler_response
        else:
            mcp_section = f"Attendance Records: {handler_response['error']}"
    elif query_type == 'activity':
        # Activity Query
        handler_response = activity_handler(question)
        if handler_response.get('answer'):
            return handler_response
        mcp_section = f"Activity Records: {handler_response['raw_records']}"
        filename = handler_response['csv_file']
    elif getProdArgs().command == '' and kts_result is None:
        # KTS query intent determination
        kts_prompt = f"User: {question} Intent: {KTS_keywords} Instruction: Determine the intent of the user from the list of available options. Be concise and output only what is needed."
        handler = handler_deepseek(kts_prompt)
        print(handler)
        for key in KTS_keywords:
            if key in handler.lower():
                getProdArgs().command = key
                getProdArgs().date_time = extractDate(question)
                kts_result = kts_handler(question)
        
        if kts_result != 'not kts related':
            return kts_result
    
    full_prompt = f"""You are Abegail, an AI assistant for monitoring attendance and manufacturing activity. You can also handle general queries and other requests.

{context_section}
{mcp_section}
{question}

Instructions:
1. Be informative, concise, and friendly.
2. Use markdown formatting for better readability.
3. Provide specific examples from the given data if possible.
{handler_response.get('instructions', '')}

Answer:"""

    result = handler_deepseek(full_prompt)

    return {'answer': result, 'csv_file': filename, 'response_type': query_type}

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