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
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    genai = None
    HarmCategory = None
    HarmBlockThreshold = None

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
        # Check both OLLAMA_API_BASE (NHI format) and OLLAMA_HOST (legacy)
        if host:
            self.host = host
        else:
            # Try OLLAMA_API_BASE first (e.g., http://192.168.1.20:8000/v1)
            api_base = os.getenv("OLLAMA_API_BASE")
            if api_base:
                # Remove /v1 suffix if present for Ollama native endpoint
                self.host = api_base.rstrip('/v1').rstrip('/')
            else:
                self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
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
    def __init__(self, api_key, model="gemini-1.5-flash"):
        if not genai:
            raise ImportError("Run `pip install google-generativeai`")
        
        genai.configure(api_key=api_key)
        self.model_name = model

    def chat(self, messages, json_mode=False):
        try:
            # Extract system instruction
            system_instruction = None
            chat_history = []
            
            for m in messages:
                if m['role'] == 'system':
                    system_instruction = m['content']
                elif m['role'] == 'user':
                    chat_history.append({'role': 'user', 'parts': [m['content']]})
                elif m['role'] in ['assistant', 'model']:
                    chat_history.append({'role': 'model', 'parts': [m['content']]})

            # Instantiate model with system instruction
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )

            # Config - use direct dict for GenerationConfig
            generation_config = {
                "temperature": 0.7,
                "response_mime_type": "application/json" if json_mode else "text/plain"
            }

            # Safety Settings
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            response = model.generate_content(
                chat_history,
                generation_config=generation_config,
                safety_settings=safety_settings
            )

            if not response.parts:
                 # Check for safety blocks if no parts are returned
                if response.prompt_feedback:
                     logger.warning(f"Gemini Blocked: {response.prompt_feedback}")
                     return f"Error: Content blocked ({response.prompt_feedback})"
                return "Error: Empty response"

            return response.text

        except Exception as e:
            logger.error(f"Gemini SDK Error: {e}")
            return f"Error: {str(e)}"

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
            # Ensure messages is a list
            if isinstance(messages, str):
                messages = [{"role": "user", "content": messages}]

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
    Auto-detects NHI Orchestrator (OpenAI-compatible) vs native Ollama.
    """
    def __init__(self, provider="ollama", model=None, api_key=None):
        self.provider_name = provider
        self.provider = None
        
        if provider == "ollama":
            # Check if we're using NHI Orchestrator (OpenAI-compatible endpoint)
            api_base = os.getenv("OLLAMA_API_BASE")
            if api_base and "/v1" in api_base:
                # NHI Orchestrator uses OpenAI format
                logger.info(f"Using NHI Orchestrator at {api_base}")
                if not OpenAI:
                    raise ImportError("NHI integration requires: pip install openai")
                self.provider = OpenAI(base_url=api_base, api_key="dummy")  # No auth needed for local
                self.model = model or "neural-home-v3.2"  # NHI routing trigger model
                self.is_openai_client = True
            else:
                # Native Ollama
                self.provider = OllamaProvider(model=model or "mistral-nemo:latest")
                self.is_openai_client = False
        elif provider == "google":
            self.provider = GoogleProvider(api_key=api_key, model=model or "gemini-1.5-flash")
            self.is_openai_client = False
        elif provider == "openrouter":
            self.provider = OpenRouterProvider(api_key=api_key, model=model)
            self.is_openai_client = False
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def chat(self, messages, json_mode=False):
        if self.is_openai_client:
            # Use OpenAI SDK directly for NHI Orchestrator
            try:
                response = self.provider.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"} if json_mode else None
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"NHI Orchestrator Error: {e}")
                return None
        else:
            return self.provider.chat(messages, json_mode)
