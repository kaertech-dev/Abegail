# context_manager.py - Streamlined Context Manager
import json
import os
from datetime import datetime
from collections import deque
from typing import List, Dict

CONTEXT_FILE = "conversation_context.json"
MAX_SESSION_HISTORY = 200

class ContextManager:
    def __init__(self):
        self.active_sessions = {}
        self.entity_cache = {}
        
    def add_message(self, session_id: str, message: str, message_type: str, metadata: Dict = None):
        """Add message to session history"""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = deque(maxlen=MAX_SESSION_HISTORY)
        
        self.active_sessions[session_id].append({
            'message': message,
            'type': message_type,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        })
    
    def get_relevant_context(self, session_id: str, current_query: str, max_messages: int = 5) -> str:
        """Get relevant context based on query"""
        if session_id not in self.active_sessions:
            return ""
        
        history = list(self.active_sessions[session_id])[-max_messages * 2:]
        query_words = set(current_query.lower().split())
        
        scored = []
        for msg in history:
            if msg['type'] == 'user':
                msg_words = set(msg['message'].lower().split())
                overlap = len(query_words & msg_words) / max(len(query_words), 1)
                if overlap > 0.2:
                    scored.append((overlap, msg))
        
        scored.sort(reverse=True, key=lambda x: x[0])
        relevant = [msg for _, msg in scored[:max_messages]]
        
        return "\n".join(f"{'User' if m['type'] == 'user' else 'Assistant'}: {m['message']}" 
                        for m in relevant)
    
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