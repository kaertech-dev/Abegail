# session_manager.py - Chat Session Management
from typing import Dict, List
from datetime import datetime

class SessionManager:
    """Manage chat sessions and messages"""
    
    def __init__(self):
        self.sessions: Dict[str, List[Dict]] = {}
    
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