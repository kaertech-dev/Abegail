# knowledge_base.py - Streamlined Knowledge Base
import json
import os
import re
from datetime import datetime
from typing import List, Dict

KNOWLEDGE_BASE_FILE = "knowledge_base.json"

class KnowledgeBase:
    def __init__(self):
        self.data = self._load_knowledge()
        self.facts = self.data.get('facts', [])
        self.examples = self.data.get('examples', [])
        
    def _load_knowledge(self):
        if os.path.exists(KNOWLEDGE_BASE_FILE):
            try:
                with open(KNOWLEDGE_BASE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {'facts': [], 'examples': [], 'last_updated': datetime.now().isoformat()}
    
    def _save_knowledge(self):
        try:
            self.data['facts'] = self.facts[-500:]  # Keep last 500
            self.data['examples'] = self.examples[-200:]  # Keep last 200
            self.data['last_updated'] = datetime.now().isoformat()
            
            with open(KNOWLEDGE_BASE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Could not save knowledge base: {e}")
    
    def add_fact(self, fact: str, category: str = "general", confidence: float = 0.8):
        """Add fact to knowledge base"""
        if not self._fact_exists(fact):
            self.facts.append({
                'fact': fact,
                'category': category,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat(),
                'usage_count': 0
            })
            self._save_knowledge()
    
    def _fact_exists(self, fact: str) -> bool:
        fact_words = set(fact.lower().split())
        for existing in self.facts:
            existing_words = set(existing['fact'].lower().split())
            similarity = len(fact_words & existing_words) / max(len(fact_words | existing_words), 1)
            if similarity > 0.8:
                return True
        return False
    
    def search_facts(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for relevant facts"""
        query_words = set(query.lower().split())
        scored_facts = []
        
        for fact_entry in self.facts:
            fact_words = set(fact_entry['fact'].lower().split())
            overlap = len(query_words & fact_words) / max(len(query_words), 1)
            score = overlap * fact_entry['confidence']
            
            if score > 0.2:
                scored_facts.append((score, fact_entry))
                fact_entry['usage_count'] += 1
        
        scored_facts.sort(reverse=True, key=lambda x: x[0])
        return [fact for _, fact in scored_facts[:limit]]
    
    def add_example(self, query: str, response: str, category: str = "general"):
        """Add example query-response pair"""
        self.examples.append({
            'query': query,
            'response': response,
            'category': category,
            'timestamp': datetime.now().isoformat()
        })
        self._save_knowledge()
    
    def extract_entities_from_text(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from text"""
        entities = {'operators': [], 'databases': [], 'dates': []}
        
        # Extract operator IDs (KE####)
        entities['operators'] = re.findall(r'\bKE\d{4}\b', text, re.IGNORECASE)
        
        # Extract database names
        db_names = ['operators', 'ledtech', 'dentsply', 'faceware', 'mainboard']
        for db in db_names:
            if db.lower() in text.lower():
                entities['databases'].append(db)
        
        return entities

_knowledge_base = None

def get_knowledge_base():
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base