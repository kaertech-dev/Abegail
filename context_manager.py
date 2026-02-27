# context_manager.py - Streamlined Context Manager
import json
import spacy
from datetime import datetime
from collections import deque
from typing import List, Dict
from ai_handler import handler_deepseek

CONTEXT_FILE = "user-profile.json"
MAX_SESSION_HISTORY = 200
MODEL_NAME = "deepseek-r1:1.5b"

nlp = spacy.load("en_core_web_md")

class SessionHistory:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session_wide_memory = {} # Note that everything is cleared after debug restart, so use knowledge base for certain facts
        self.long_term_summary = {} # <timestamp> : <text>
        self.long_term = deque(maxlen=100)
        self.short_term = deque(maxlen=20)
    
    def __del__(self):
        print("Session memory wiped clean.")
    
    def __str__(self):
        return f"Session Wide Memory: {self.session_wide_memory}\n\nShort Term: {self.short_term}\n\nLong Term: {self.long_term}\n"
    
    def add_history(self, dict_obj: Dict):
        # If short term is full, earliest entry is transferred to long term memory
        # Deque automatically trims long term
        if len(self.short_term) == 20:
            self.long_term.append(self.short_term.popleft())
        self.short_term.append(dict_obj)
    
    def get_context(self) -> deque:
        return self.short_term
    
    def retrieve_LTsummary(self, question) -> str:
        relevant_info = list(self.long_term)[-20:]
        sum_prompt = f"Please give a brief summary of these conversations between the user and AI assistant: {relevant_info}"
        new_summary = handler_deepseek(sum_prompt, MODEL_NAME)
        self.long_term_summary[datetime.today()] = new_summary

class ContextManager:
    def __init__(self):
        self.active_sessions = {}
        self.entity_cache = {}
    
    def update_history(self, session_id: str, user_message: str, bot_message: str):
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = SessionHistory(session_id)
        
        self.active_sessions[session_id].add_history({
            'timestamp': datetime.now().isoformat(), 
            'User': user_message, 
            'Assistant': bot_message
        })
    
    def add_fact(self, session_id: str, dict_entry: dict):
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = SessionHistory(session_id)
        
        self.active_sessions[session_id].session_wide_memory.update(dict_entry)
        print(self.active_sessions[session_id].session_wide_memory)
    
    def replace_name(self, session_id: str) -> str:
        if session_id not in self.active_sessions:
            return ""
        
        facts = self.active_sessions[session_id].session_wide_memory
        return facts["User name"]
    
    def get_relevant_context(self, session_id: str, current_query: str, max_messages: int = 5) -> dict:
        """Get relevant context based on query"""
        if session_id not in self.active_sessions:
            return {}
        
        immediate_context = self.active_sessions[session_id].get_context()
        processed = nlp(current_query)
        relevant = []

        for chat in immediate_context:
            if len(relevant) == max_messages:
                break

            ref = nlp(chat['User'])
            if processed.similarity(ref) > 0.7:
                relevant.append(chat)
        
        some_context = "\n".join(f"User: {msg['User']}\nAssistant: {msg['Assistant']}" for msg in relevant)
        facts = self.active_sessions[session_id].session_wide_memory
        return {'facts': facts, 'recent_convo': some_context}
    
    def clear_session(self, session_id: str):
        """Clear session history"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.entity_cache:
            del self.entity_cache[session_id]

_context_manager = None

def get_context_manager():
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager