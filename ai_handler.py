# ai_handler.py - Enhanced with GPU Optimization
import subprocess
import os
from typing import List, Optional, Dict

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

def ask_general_question(question, context: Optional[str] = None, 
                        relevant_facts: Optional[List[str]] = None,
                        query_analysis: Optional[Dict] = None):
    """Enhanced general question handler with reasoning and GPU optimization"""
    MODEL_NAME = _get_model_name()
    
    reasoning_context = _build_reasoning_context(question, query_analysis)
    
    context_section = f"\nConversation Context:\n{context}\n" if context else ""
    facts_section = f"\nRelevant Facts:\n" + "\n".join(f"- {f}" for f in relevant_facts) + "\n" if relevant_facts else ""
    
    full_prompt = f"""You are Abegail, a helpful and intelligent AI assistant.

{reasoning_context}
{context_section}{facts_section}
User Question: {question}

INSTRUCTIONS:
1. Understand what the user is really asking
2. Provide a clear, direct answer
3. Be conversational and friendly
4. Use examples when helpful
5. If you're not sure, say so honestly

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
        
        return clean_response(stdout.strip()) if stdout.strip() else "No response generated."

    except subprocess.TimeoutExpired:
        process.kill()
        return "⏱️ Request timeout."
    except FileNotFoundError:
        return "❌ Ollama not running."
    except Exception as e:
        return f"Error: {str(e)}"

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