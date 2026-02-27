# session_manager.py - Chat Session Management
import os
import json
import spacy
from typing import Dict, List
from datetime import datetime
from collections import deque

nlp = spacy.load("en_core_web_md")

class SessionObject:
    def __init__(self, session_id: str):
        self.filename = session_id + ".json"
        self.user_name = ''
        self.short_term = deque(maxlen=20)
        self.long_term = ''

        # initialize json file with this structure
        with open(self.filename, mode='w', encoding='utf-8') as json_file:
            first_entry = {'session_id': session_id, 'full_history' : [], 'summaries': []}
            json.dump(first_entry, json_file, indent=2, ensure_ascii=False)
    
    def add_message(self, user_message: str, bot_message: str):
        user = self.user_name if self.user_name else 'user'
        entry = {user: user_message, 'bot': bot_message, 'timestamp': datetime.now().strftime("%H:%M")} # need ba magdagdag ng other metadata?
        self.short_term.append(entry)

        # also add the query-response to json file automatically
        with open(self.filename, mode='rw', encoding='utf-8') as json_file:
            full_data = json.load(json_file)
            full_data['Session history'].append(entry)
            json.dump(full_data, json_file, indent=2, ensure_ascii=False)
    
    def summarize(self):
        with open(self.filename, mode='rw', encoding='utf-8') as json_file:
            full_data = json.load(json_file)
            # call the llm here?
            # self.long_term = bot_response -> include timestamp inside
            # full_data.get('summaries').append(bot_response)
            json.dump(full_data, json_file, indent=2, ensure_ascii=False)

    def get_relevant_context(self, query: str) -> List[Dict]:
        user_key = self.user_name if self.user_name else 'user'
        processed = nlp(query)
        relevant = []

        for message in self.short_term:
            if len(relevant) == 10:
                break

            ref = nlp(message[user_key])
            if processed.similarity(ref) > 0.7:
                relevant.append(message)
        
        return relevant

class SessionManager:
    """Manage chat sessions and messages"""
    
    def __init__(self):
        self.sessions: Dict[str, List[Dict]] = {}
        self.active_sessions = {}
    
    def get_session_object(self, session_id) -> SessionObject:
        if session_id not in self.active_sessions:
            self.active_sessions = {session_id : SessionObject(session_id)}
        
        return self.active_sessions[session_id]
    
    def create_message(self, msg_type: str, message: str, session_id: str, 
                      parent_id: str = None, **kwargs) -> Dict:
        """Create a message object"""
        return {
            'type': msg_type,
            'message': message,
            'timestamp': datetime.now().strftime("%H:%M"),
            'id': f"msg_{len(self.sessions.get(session_id, []))}",
            'parent_id': parent_id,
            **kwargs
        }
    
    def add_message(self, session_id: str, message: Dict):
        """Add message to session"""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(message)
    
    def get_session(self, session_id: str) -> List[Dict]:
        """Get session messages"""
        return self.sessions.get(session_id, [])
    
    def clear_session(self, session_id: str):
        """Clear session messages"""
        self.sessions[session_id] = []
    
    def ensure_session_exists(self, session_id: str):
        """Ensure session exists"""
        if session_id not in self.sessions:
            self.sessions[session_id] = []

# Singleton instance
_session_manager = None

def get_session_manager() -> SessionManager:
    """Get singleton session manager"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager