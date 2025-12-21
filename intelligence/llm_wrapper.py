"""
Lightweight Ollama Chat Wrapper
"""
import requests
import json
import logging

logger = logging.getLogger(__name__)

class LLMWrapper:
    def __init__(self, model="mistral-nemo:latest"):
        self.model = model
        self.api_url = "http://localhost:11434/api/chat"

    def chat(self, messages, json_mode=False):
        """
        Send chat messages to Ollama.
        messages: list of dicts [{'role': 'user', 'content': '...'}, ...]
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }
        
        if json_mode:
            payload["format"] = "json"

        try:
            resp = requests.post(self.api_url, json=payload, timeout=120)
            if resp.status_code == 200:
                body = resp.json()
                return body.get('message', {}).get('content', '')
            else:
                print(f"❌ Ollama Chat Error: {resp.text}")
                return None
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            return None
