# ai_handler.py - Enhanced with GPU Optimization
import subprocess
import os
import re
import csv
import spacy
from typing import List, Optional, Dict
from date_parser import extractDate
from mcp_activity_server import ActivityAPI
from mcp_attendance_server import AttendanceDB

path_name = './csv_files/'
filename = ''
nlp = spacy.load("en_core_web_md")

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

def activity_handler(question: str):
    # set date input for api endpoint
    curr_date = extractDate(question)[0]
    api_date = f'?start_date={curr_date}&end_date={curr_date}'

    # retrieve records from api
    activityService = ActivityAPI()
    success = False
    while not success:
        api_response = activityService.get_all_data(api_date)
        success = api_response['success']
    records = api_response['data']['records']
    
    # prepare csv file for writing
    global filename
    filename = 'activity_' + curr_date + '.csv'
    csvfile = open(path_name + filename, 'w', newline='', encoding='utf-8')
    writer = csv.DictWriter(csvfile, fieldnames=['Customer', 'Model', 'Station', 'Operator', 'Output', 'Cycle Time(s)', 'Target(s)', 'Start Time', 'End time', 'Status'], extrasaction='ignore')
    writer.writeheader()

    # remove serial numbers and rename target to make it easier for Deepseek to parse
    for r in records:
        writer.writerow(r)
        r['Target Cycle Time(s)'] = r.pop('Target(s)')
        r.pop('serial_num')
    
    return f"Activity Records: {records} Refer to people by name but also give their employee number."

def attendance_handler(question: str):
    attendanceService = AttendanceDB()
    processed = nlp(question)
    # ner_tagging = [(ent.text, ent.label_) for ent in processed.ents]
    emp_id = None
    for ent in processed.ents:
        if ent.label_ == 'PERSON':
            emp_id = ent.text
    
    date_input = extractDate(question)[0]
    records = attendanceService.get_records_by_date(date_input, emp_id)

    # prepare csv file for writing
    global filename
    filename = 'attendance_' + date_input + '.csv'
    csvfile = open(path_name + filename, 'w', newline='', encoding='utf-8')
    writer = csv.DictWriter(csvfile, fieldnames=['employee_name', 'employee_num', 'timestamp', 'location'], extrasaction='ignore')
    writer.writeheader()
    for r in records:
        writer.writerow(r)
    
    return f"Attendance Records: {records} If asking for earliest or latest, give 10 entries and sort them by timestamp. Use both names and employee numbers. Ignore ID."

def ask_general_question(question, context: Optional[str] = None, 
                        relevant_facts: Optional[List[str]] = None,
                        query_analysis: Optional[Dict] = None):
    """Enhanced general question handler with reasoning and GPU optimization"""
    MODEL_NAME = _get_model_name()
    
    # reasoning_context = _build_reasoning_context(question, query_analysis)
    
    context_section = f"\nRecent conversations:\n{context}\n" if context else ""
    # facts_section = f"\nRelevant Facts:\n" + "\n".join(f"- {f}" for f in relevant_facts) + "\n" if relevant_facts else ""

    if 'debug123' in question:
        question = question.replace('debug123', '')
        mcp_section = activity_handler(question)
    
    elif 'debug456' in question:
        question = question.replace('debug456', '')
        mcp_section = attendance_handler(question)
    
    else:
        mcp_section = ''
    
    full_prompt = f"""You are Abegail, a helpful and reliable AI assistant for retrieving and summarizing company data.

{context_section}
{mcp_section}
User Question: {question}

Instructions:
1. Be concise and brief, but friendly.
2. Provide specific details from the given data.
3. If data is missing or unknown, say so honestly.
4. Use markdown formatting for better readability. 
5. If there's no mention of activity or attendance, be verbose and enthusiastic.

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

        # Shorter timeout for general questions
        timeout = 45 if "1.5b" in MODEL_NAME else 60
        stdout, stderr = process.communicate(input=full_prompt, timeout=timeout)
        
        if process.returncode != 0:
            return "Sorry, there was an error."

        result = {
                'answer': clean_response(stdout.strip()) if stdout.strip() else "No response generated.",
                'csv_file': filename,
                'response_type': 'general'
            }
        
        return result

    except subprocess.TimeoutExpired:
        process.kill()
        return {'answer': "⏱️ Request timeout.", 'response_type': 'general'}
    except FileNotFoundError:
        return {'answer': "❌ Ollama not running.", 'response_type': 'general'}
    except Exception as e:
        return {'answer': f"Error: {str(e)}", 'response_type': 'general'}

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

def generate_smart_response(query_analysis: Dict, data: any) -> str:
    """Generate intelligent response based on query analysis"""
    intent = query_analysis.get('primary_intent')
    question_type = query_analysis.get('question_type')
    entities = query_analysis.get('entities', {})
    
    # Handle empty data
    if not data or (isinstance(data, (list, dict)) and len(data) == 0):
        if intent in ['attendance_check', 'attendance_report']:
            employee = entities.get('employee_name', [None])[0] or entities.get('employee_id', [None])[0]
            if employee:
                if question_type == 'yes_no':
                    return f"**NO**, {employee} is not present based on available records."
                else:
                    return f"No attendance records found for {employee}."
            else:
                return "No attendance records found for the specified criteria."
        else:
            return "No data found matching your query."
    
    # For yes/no attendance questions, provide clear answer
    if intent == 'attendance_check' and question_type == 'yes_no':
        employee = entities.get('employee_name', [None])[0] or entities.get('employee_id', [None])[0]
        if employee and data:
            return f"**YES**, {employee} is present! Found {len(data) if isinstance(data, list) else 1} attendance record(s)."
    
    return None  # Let AI handler process normally