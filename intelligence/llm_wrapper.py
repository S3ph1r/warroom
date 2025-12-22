"""
Unified LLM Wrapper supporting Ollama (Local), Google (Gemini), and OpenRouter.
"""
import os
import logging
import requests
import json
from abc import ABC, abstractmethod

# Dependencies
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)

class BaseLLMProvider(ABC):
    @abstractmethod
    def chat(self, messages, json_mode=False):
        pass

class OllamaProvider(BaseLLMProvider):
    def __init__(self, model="mistral-nemo:latest", host=None):
        self.model = model
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.api_url = f"{self.host}/api/chat"

    def chat(self, messages, json_mode=False):
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
                logger.error(f"Ollama Error: {resp.text}")
                return None
        except Exception as e:
            logger.error(f"Ollama Connection Error: {e}")
            return None

class GoogleProvider(BaseLLMProvider):
    """
    Uses the new `google-genai` SDK.
    """
    def __init__(self, api_key, model="gemini-1.5-flash"):
        if not genai:
            raise ImportError("Run `pip install google-genai`")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model
        
    def chat(self, messages, json_mode=False):
        system_instruction = None
        contents = []
        
        # Parse messages into new SDK format
        for m in messages:
            if m['role'] == 'system':
                system_instruction = m['content']
            elif m['role'] == 'user':
                contents.append(types.Content(role='user', parts=[types.Part.from_text(text=m['content'])]))
            elif m['role'] in ['model', 'assistant']:
                 contents.append(types.Content(role='model', parts=[types.Part.from_text(text=m['content'])]))
        
        # Config with Safety Settings (BLOCK_NONE)
        config = types.GenerateContentConfig(
            temperature=0.7,
            response_mime_type="application/json" if json_mode else "text/plain",
            system_instruction=system_instruction,
            safety_settings=[
                types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
                types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
                types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
                types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE'),
            ]
        )
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini SDK Error: {e}")
            return None

class OpenRouterProvider(BaseLLMProvider):
    def __init__(self, api_key, model, site_url="http://localhost", site_name="WarRoom"):
        if not OpenAI:
            raise ImportError("Run `pip install openai`")
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model = model
        self.extra_headers = {
            "HTTP-Referer": site_url,
            "X-Title": site_name,
        }

    def chat(self, messages, json_mode=False):
        try:
            resp = self.client.chat.completions.create(
                extra_headers=self.extra_headers,
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"} if json_mode else None
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenRouter Error: {e}")
            return None

class LLMWrapper:
    """
    Factory wrapper to maintain backward compatibility while supporting providers.
    """
    def __init__(self, provider="ollama", model=None, api_key=None):
        self.provider_name = provider
        self.provider = None
        
        if provider == "ollama":
            self.provider = OllamaProvider(model=model or "mistral-nemo:latest")
        elif provider == "google":
            self.provider = GoogleProvider(api_key=api_key, model=model or "gemini-1.5-flash")
        elif provider == "openrouter":
            self.provider = OpenRouterProvider(api_key=api_key, model=model)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def chat(self, messages, json_mode=False):
        return self.provider.chat(messages, json_mode)
