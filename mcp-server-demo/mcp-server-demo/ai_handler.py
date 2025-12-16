# ai_handler.py - Streamlined AI Handler
import subprocess
from typing import List, Optional

def _get_model_name():
    from config import MODEL_NAME
    return MODEL_NAME

def ask_deepseek(question, data_chunks, context: Optional[str] = None, 
                relevant_facts: Optional[List[str]] = None):
    """AI handler for database queries"""
    MODEL_NAME = _get_model_name()
    
    context_section = f"\nContext:\n{context}\n" if context else ""
    facts_section = f"\nFacts:\n" + "\n".join(f"- {f}" for f in relevant_facts) + "\n" if relevant_facts else ""
    
    full_prompt = f"""You are Abegail, an AI assistant for database queries.

{context_section}{facts_section}
Data:
{chr(10).join(data_chunks[:5])}

Question: {question}

Answer directly and concisely with specific details. Use markdown formatting."""
    
    try:
        process = subprocess.Popen(
            ["ollama", "run", MODEL_NAME],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        
        stdout, stderr = process.communicate(input=full_prompt, timeout=90)
        
        if process.returncode != 0:
            return "Sorry, there was an error processing your request."
        
        return clean_response(stdout.strip()) if stdout.strip() else "No response generated."
        
    except subprocess.TimeoutExpired:
        process.kill()
        return "⏱️ Request timeout. Try a shorter question."
    except FileNotFoundError:
        return "❌ Ollama not running. Start with 'ollama serve'"
    except Exception as e:
        return f"An error occurred: {str(e)}"

def ask_general_question(question, context: Optional[str] = None, relevant_facts: Optional[List[str]] = None):
    """AI handler for general questions"""
    MODEL_NAME = _get_model_name()
    
    context_section = f"\nContext:\n{context}\n" if context else ""
    facts_section = f"\nFacts:\n" + "\n".join(f"- {f}" for f in relevant_facts) + "\n" if relevant_facts else ""
    
    full_prompt = f"""You are Abegail, a helpful AI assistant.

{context_section}{facts_section}
Question: {question}

Answer clearly and concisely."""

    try:
        process = subprocess.Popen(
            ["ollama", "run", MODEL_NAME],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        stdout, stderr = process.communicate(input=full_prompt, timeout=60)
        
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

def clean_response(output):
    """Remove thinking markers and extra whitespace"""
    clean = output
    
    # Remove thinking markers
    for start, end in [("Thinking...", "...done"), ("<think>", "</think>")]:
        if start in clean and end in clean:
            start_idx = clean.find(start)
            end_idx = clean.find(end) + len(end)
            clean = clean[:start_idx] + clean[end_idx:]
    
    clean = clean.replace("Thinking...", "").replace("<think>", "").replace("</think>", "")
    
    # Clean whitespace
    while "\n\n\n" in clean:
        clean = clean.replace("\n\n\n", "\n\n")
    
    return clean.lstrip(". \n").strip()