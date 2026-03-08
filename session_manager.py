# session_manager.py - Chat Session Management
import os
import json
import spacy
from typing import Dict, List
from datetime import datetime
from collections import deque

nlp = spacy.load("en_core_web_md")

class SessionObject:
    def __init__(self, session_id: str, profile = 'guest'):
        self.session_id = session_id
        self.filename = profile + ".json"
        self.user_name = '' # store in json as well
        self.long_term = []
        self.json_buffer = {"full_history": []}

        # load original contents of json file
        with open(self.filename, mode='r', encoding='utf-8') as json_file:
            self.json_buffer = json.load(json_file)
            self.short_term = deque(self.json_buffer['full_history'][-5:], maxlen=10)
    
    def update_history(self, user_message: str, bot_message: str):
        entry = {'user': user_message, 'bot': bot_message, 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M")}
        self.short_term.append(entry)

        # update json file as well
        self.json_buffer['full_history'].append(entry)
        json_data = {}
        with open(self.filename, mode='w', encoding='utf-8') as json_file:
            json_data['full_history'] = self.json_buffer['full_history'][-200:]
            json.dump(json_data, json_file, indent=2, ensure_ascii=False)
    
    # def trim_long_term(self, current_query: str):
    #     reference = nlp(current_query)
    #     trimmed = self.json_buffer['full_history']
    #     for exchange in self.json_buffer['full_history']:
    #         processed = nlp(exchange["user"])
    #         if reference.similarity(processed) < 0.2:
    #             trimmed.pop(exchange)
    
    def summarize(self):
        with open(self.filename, mode='r', encoding='utf-8') as json_file:
            full_data = json.load(json_file)
            # call the llm here?
            # self.long_term = bot_response -> include timestamp inside
            # full_data.get('summaries').append(bot_response)
            # json.dump(full_data, json_file, indent=2, ensure_ascii=False)

    def get_relevant_context(self, query: str) -> List[Dict]:
        user_key = self.user_name if self.user_name else 'user'
        processed = nlp(query)
        relevant = []

        for message in reversed(self.short_term):
            if len(relevant) == 10:
                break

            # ref = nlp(message['user'])
            # if processed.similarity(ref) > 0.7:
            relevant.append({user_key: message['user'], 'response': message['bot']})
        relevant.reverse()
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